# Performance & Reliability Weaknesses — Backstage Backend

## SEVERITY: MEDIUM–HIGH

---

### 1. Database Keepalive Uses `SELECT 1` with Fixed 60s Interval

**File:** [`DatabaseManager.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/database/DatabaseManager.ts#L199-L228)

```typescript
this.keepaliveIntervals.set(
  pluginId,
  setInterval(() => {
    client?.raw('select 1').then(
      () => { lastKeepaliveFailed = false; },
      (error: unknown) => {
        if (!lastKeepaliveFailed) {
          lastKeepaliveFailed = true;
          logger.warn(`Database keepalive failed for plugin ${pluginId}, ...`);
        }
      },
    );
  }, 60 * 1000),
);
```

**Problems:**
- **Fixed 60-second interval** is not configurable — too frequent for healthy databases, potentially too slow for detecting dropped connections
- **No exponential backoff** on failures — a disconnected database gets hammered every 60 seconds
- **Logging is suppressed after first failure** (`lastKeepaliveFailed` flag) — subsequent failure details are silently swallowed
- **No reconnection logic** — if the keepalive detects a failure, it doesn't attempt to re-establish the connection
- **Promise not awaited** — the `.then()` pattern loses unhandled rejection tracking

**Impact:** Database connection issues may go undetected or trigger excessive logging without recovery.

---

### 2. Database Connection Cache Has Race Condition

**File:** [`DatabaseManager.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/database/DatabaseManager.ts#L175-L197)

```typescript
private async getDatabase(...): Promise<Knex> {
  if (this.databaseCache.has(pluginId)) {
    return this.databaseCache.get(pluginId)!;
  }
  const clientPromise = connector.getClient(pluginId, deps);
  this.databaseCache.set(pluginId, clientPromise);
  // ...
  return clientPromise;
}
```

**Problem:** While storing the Promise prevents duplicate creation, the approach has a subtle issue:
- If `connector.getClient()` rejects, the failed Promise remains cached forever
- Subsequent calls to `getDatabase()` will always return the rejected promise
- There is no retry mechanism or cache eviction on failure

**Impact:** A transient database connection failure at startup will permanently prevent a plugin from accessing its database until the entire backend is restarted.

---

### 3. SQLite3 Connections Skip Destroy During Shutdown

**File:** [`DatabaseManager.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/database/DatabaseManager.ts#L126-L128)

```typescript
if (connection.client.config.includes('sqlite3')) {
  return; // sqlite3 does not support destroy, it hangs
}
```

**Problem:** SQLite3 connections are intentionally leaked during shutdown because `destroy()` hangs. This is a workaround rather than a fix:
- File handles and WAL locks may not be properly released
- Tests using SQLite3 may leave behind lock files
- Data may not be fully flushed to disk

**Impact:** Potential data corruption or lock conflicts in environments using SQLite3 (common in development and testing).

---

### 4. JWKS Client Has Unbounded Cache Growth

**File:** [`PluginTokenHandler.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/auth/plugin/PluginTokenHandler.ts#L63-L67)

```typescript
private jwksMap = new Map<string, JwksClient>();
private supportedTargetPlugins = new Set<string>();
private targetPluginInflightChecks = new Map<string, Promise<boolean>>();
```

**Problem:** Three in-memory collections grow unboundedly:
- `jwksMap` — never evicts entries for removed/decommissioned plugins
- `supportedTargetPlugins` — never invalidates; a plugin that goes offline stays "supported" forever
- `targetPluginInflightChecks` — cleaned up on completion but has no timeout (a hanging check remains indefinitely)

**Impact:** Memory leak proportional to the total number of plugins ever communicated with.

---

### 5. Credentials Cached on Request Object Without Invalidation

**File:** [`httpAuthServiceFactory.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/httpAuth/httpAuthServiceFactory.ts#L145-L153)

```typescript
async #getCredentials(req: RequestWithCredentials) {
  return (req[credentialsSymbol] ??= this.#extractCredentialsFromRequest(req));
}
async #getLimitedCredentials(req: RequestWithCredentials) {
  return (req[limitedCredentialsSymbol] ??= this.#extractLimitedCredentialsFromRequest(req));
}
```

**Problem:** Credentials are memoized on the request object using Symbol properties. Once computed, they are never re-validated:
- In long-running streaming requests, the credentials may expire mid-stream
- No mechanism to invalidate cached credentials if the underlying token is revoked

**Impact:** Long-lived connections (SSE, WebSocket upgrades, large file uploads) continue to operate under expired credentials.

---

### 6. `parseErrorResponseBody` Silently Swallows All Errors

**File:** [`response.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/errors/src/serialization/response.ts#L85-L87)

```typescript
} catch {
  // ignore
}
```

**Problem:** The function has two bare `catch` blocks that silently swallow errors:
- If `response.text()` throws (e.g., body stream already consumed), the error is hidden
- If JSON parsing fails, the error details are lost
- The returned synthetic error body gives no indication of what went wrong

**Impact:** Debugging production issues becomes difficult when error context is silently discarded.

---

### 7. Error Status Code Matching by `error.name` String

**File:** [`MiddlewareFactory.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/rootHttpRouter/http/MiddlewareFactory.ts#L332-L371)

```typescript
function getStatusCode(error: Error): number {
  // ...
  switch (error.name) {
    case NotModifiedError.name: return 304;
    case InputError.name: return 400;
    case AuthenticationError.name: return 401;
    // ...
  }
}
```

**Problem:** Error-to-HTTP-status-code mapping relies on string matching against `error.name`:
- Any error with `name === 'InputError'` will be treated as 400, regardless of its actual class
- This can be exploited by third-party code or plugins that accidentally (or intentionally) name errors to match Backstage error names
- If errors are serialized/deserialized across process boundaries, `instanceof` checks would fail, but name-based checks would succeed on unintended errors
- `NotModifiedError` maps to 304, which is a redirect status, not an error — this is semantically incorrect in an error handler

**Impact:** Incorrect HTTP status codes could be returned, leading to confusing client behavior and potential security implications (e.g., returning 401 instead of 500 for an unrelated error named "AuthenticationError").

---

### 8. `applyInternalErrorFilter` Only Catches `DatabaseError` by Constructor Name

**File:** [`applyInternalErrorFilter.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/rootHttpRouter/http/applyInternalErrorFilter.ts#L44-L48)

```typescript
const constructorName = error.constructor.name;
if (constructorName === 'DatabaseError') {
  return handleBadError(error, logger);
}
```

**Problem:**
- Only `DatabaseError` (from `pg-protocol`) is filtered — other database drivers (MySQL, SQLite) may expose internal errors with different class names
- String-based constructor name matching is fragile — minification or bundling can rename constructors
- Other sensitive error types (e.g., filesystem errors, network errors with internal IPs) are not filtered

**Impact:** Internal database details from non-PostgreSQL drivers may be leaked in error responses.

---

### 9. No Request Body Size Limits

**File:** [`rootHttpRouterServiceFactory.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/rootHttpRouter/rootHttpRouterServiceFactory.ts#L113-L198)

**Problem:** The default middleware stack applies `helmet`, `cors`, `compression`, `logging`, `rateLimit`, and `notFound`/`error`, but does **not** apply request body size limits:
- No `express.json({ limit: ... })` or `express.urlencoded({ limit: ... })` middleware
- Individual plugins must set their own body parsers with limits
- Large payloads can exhaust memory and crash the process

```typescript
applyDefaults() {
  // ...
  app.use(middleware.helmet());
  app.use(middleware.cors());
  app.use(middleware.compression());
  app.use(middleware.logging());
  app.use(middleware.rateLimit());
  // Note: no body parser with size limits
  app.use(healthRouter);
  app.use(routes);
  app.use(middleware.notFound());
  app.use(middleware.error());
}
```

**Impact:** Denial of Service via oversized request bodies.

---

### 10. `config.subscribe` Error Handling Is Incomplete

**File:** [`HostDiscovery.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/discovery/HostDiscovery.ts#L179-L184)

```typescript
config.subscribe?.(() => {
  try {
    discovery.#updateResolvers(config, options?.defaultEndpoints);
  } catch (e) {
    options?.logger.error(`Failed to update discovery service: ${e}`);
  }
});
```

**Problem:**
- If `#updateResolvers` throws, the old resolvers remain — which is actually safe — but the error message provides no actionable detail
- The `options?.logger` uses optional chaining, meaning if no logger was provided, the error is silently swallowed
- No mechanism to recover or retry the config update
- No notification to operators that discovery is running with stale configuration

**Impact:** Stale service discovery configuration with no clear indication to operators.
