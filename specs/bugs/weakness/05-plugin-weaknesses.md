# Plugin-Level Weaknesses — Backstage Backend

## SEVERITY: HIGH–MEDIUM

---

### 1. Proxy Backend — SSRF via Configurable Target URL

**File:** [`router.ts`](file:///Users/binhnt/Lab/dev/backstage/plugins/proxy-backend/src/service/router.ts#L106-L120)

```typescript
// Validate that target is a valid URL.
const targetType = typeof fullConfig.target;
if (targetType !== 'string') {
  throw new Error(`Proxy target for route "${route}" must be a string...`);
}
try {
  new URL(fullConfig.target! as string);
} catch {
  throw new Error(`Proxy target is not a valid URL: ${fullConfig.target ?? ''}`);
}
```

**Problem:** The proxy backend validates that the target is a syntactically valid URL, but performs **no SSRF (Server-Side Request Forgery) protection**:
- Internal network addresses (`http://10.0.0.0/8`, `http://169.254.169.254` — AWS metadata) are not blocked
- `file://`, `gopher://`, and other dangerous schemes are not filtered (only `new URL()` syntax validation)
- No blocklist/allowlist for target domains or IP ranges
- The `dangerously-allow-unauthenticated` credential policy makes this accessible without authentication

**Impact:** An attacker with config access (or in deployments where proxy config comes from catalog entities) can use the proxy backend as an SSRF pivot to access internal services, cloud metadata endpoints, or internal APIs.

---

### 2. Proxy Backend — No Response Size Limiting

**File:** [`router.ts`](file:///Users/binhnt/Lab/dev/backstage/plugins/proxy-backend/src/service/router.ts#L217-L238)

```typescript
fullConfig.onProxyRes = (proxyRes, _, res) => {
  // only forward the allowed headers in backend->client
  const headerNames = Object.keys(proxyRes.headers);
  headerNames.forEach(h => {
    if (!responseHeaderAllowList.has(h.toLocaleLowerCase())) {
      delete proxyRes.headers[h];
    }
  });
  // handle SSE connections
  proxyRes.on('close', () => { ... });
};
```

**Problem:** Proxy responses are forwarded without any size limiting:
- No `Content-Length` validation on responses
- No streaming body size cap
- A malicious or compromised upstream service can send unlimited data through the proxy
- Combined with SSE support (`proxyRes.on('close')`), this enables infinite response streams

**Impact:** Memory exhaustion and DoS via oversized proxy responses.

---

### 3. Proxy Backend — Config Hot-Reload Creates Race Condition

**File:** [`router.ts`](file:///Users/binhnt/Lab/dev/backstage/plugins/proxy-backend/src/service/router.ts#L311-L330)

```typescript
options.config.subscribe(() => {
  const newProxyConfig = readProxyConfig(options.config, options.logger);
  const newKey = JSON.stringify(newProxyConfig);
  if (currentKey !== newKey) {
    currentKey = newKey;
    currentRouter = Router();  // <-- New router created
    configureMiddlewares(proxyOptions, currentRouter, ...);
  }
});
```

**Problem:** When config changes, a new router is atomically swapped in. However:
- **In-flight requests** on the old router may lose access to their proxy middleware
- The old proxy middleware instances (and their HTTP connections) are not explicitly cleaned up
- The `configureMiddlewares` function may throw for individual routes (caught by `skipInvalidProxies`), leaving the new router partially configured
- The `addAuthPolicy` call in `buildMiddleware` adds policies to the HTTP router that are **never removed** when routes are reconfigured

**Impact:** Auth policy leak — removed proxy routes retain their unauthenticated access policies.

---

### 4. Scaffolder — Credentials Serialized as JSON String in Task Secrets

**File:** [`StorageTaskBroker.ts`](file:///Users/binhnt/Lab/dev/backstage/plugins/scaffolder-backend/src/scaffolder/tasks/StorageTaskBroker.ts#L218-L223)

```typescript
async getInitiatorCredentials(): Promise<BackstageCredentials> {
  const secrets = this.task.secrets as InternalTaskSecrets;
  if (secrets && secrets.__initiatorCredentials) {
    return JSON.parse(secrets.__initiatorCredentials);
  }
  // ...
}
```

**Problem:** The initiator's credentials are serialized as a JSON string and stored in the task's `secrets` field in the database:
- **Credentials are persisted in the database** — the credentials object (which may contain tokens) is stored alongside the task
- **`JSON.parse` reconstructs credentials** without any validation or signature verification — anyone with database access can forge credentials
- The credential object's `$$type` and `version` fields are trusted blindly after deserialization
- **No expiration check** — credentials stored in the database may outlive the original token's expiration

```typescript
// In router.ts — credentials are serialized:
__initiatorCredentials: JSON.stringify({
  $$type: '@backstage/BackstageCredentials',
  ...credentials
})
```

**Impact:** Credential forgery via direct database manipulation. Long-lived scaffolder tasks may continue operating with expired credentials.

---

### 5. Scaffolder — Workspace Path Traversal Risk

**File:** [`NunjucksWorkflowRunner.ts`](file:///Users/binhnt/Lab/dev/backstage/plugins/scaffolder-backend/src/scaffolder/tasks/NunjucksWorkflowRunner.ts#L640)

```typescript
const workspacePath = path.join(this.options.workingDirectory, taskId);
```

**Problem:** The workspace path is constructed by joining the working directory with the `taskId`. While the `taskId` is typically a UUID:
- There is no explicit validation that `taskId` does not contain path traversal sequences (`../`)
- If the `taskId` generation is ever changed or a custom TaskStore allows user-controlled IDs, this becomes a path traversal vulnerability
- Temporary directories are created with `${workspacePath}_step-${step.id}-` — the `step.id` comes from template definition and is user-controlled

```typescript
createTemporaryDirectory: async () => {
  const tmpDir = await fs.mkdtemp(`${workspacePath}_step-${step.id}-`);
  tmpDirs.push(tmpDir);
  return tmpDir;
},
```

**Impact:** If `step.id` contains path traversal characters, temporary directories could be created outside the intended workspace.

---

### 6. Scaffolder — Template Rendering Error Leaks Secret Paths

**File:** [`NunjucksWorkflowRunner.ts`](file:///Users/binhnt/Lab/dev/backstage/plugins/scaffolder-backend/src/scaffolder/tasks/NunjucksWorkflowRunner.ts#L283-L287)

```typescript
} catch (ex) {
  this.options.logger.error(
    `Failed to parse template string: ${value} with error ${ex.message}`,
  );
}
```

**Problem:** When template rendering fails, the raw template string (which may contain secret references like `${{ secrets.MY_API_KEY }}`) is logged:
- The template string includes the Nunjucks expressions that reference secrets
- While the actual secret values should be redacted, the **names and structure** of secrets are exposed in logs
- Error messages from Nunjucks may include partial evaluations of the template

**Impact:** Information disclosure — secret names and template structure visible in logs.

---

### 7. Scaffolder — Secret Redaction Bypass via Rendering Failure

**File:** [`NunjucksWorkflowRunner.ts`](file:///Users/binhnt/Lab/dev/backstage/plugins/scaffolder-backend/src/scaffolder/tasks/NunjucksWorkflowRunner.ts#L504-L531)

```typescript
if (hasSecrets) {
  try {
    const contextNoSecrets = { ...preIterationContext, ...iteration.each,
      secrets: {}, environment: { ...preIterationContext.environment, secrets: {} },
    };
    const inputWithoutSecrets = this.render(step.input, contextNoSecrets, renderTemplate);
    taskLogger.addRedactions(collectSecretRedactions(iteration.input, inputWithoutSecrets));
  } catch {
    taskLogger.addRedactions(extractStringValues(iteration.input));
  }
}
```

**Problem:** The secret redaction mechanism works by comparing two renders (with and without secrets) to identify which output values were influenced by secrets. However:
- If the render **without secrets fails** (throws), the fallback `extractStringValues` redacts **all string values** in the input — this is overly aggressive and may redact non-sensitive data, making logs useless
- If the comparison render succeeds but produces a **different structure** (e.g., conditional logic based on secret presence), the diff-based redaction may miss some secret-derived values
- **Short secret values** (e.g., "yes", "true", "1") would cause frequent false-positive redactions of legitimate log content

**Impact:** Either incomplete secret redaction (secret leaks in logs) or over-aggressive redaction (logs become unreadable).

---

### 8. Catalog Processing — Polling Loop Has No Adaptive Backoff

**File:** [`DefaultCatalogProcessingEngine.ts`](file:///Users/binhnt/Lab/dev/backstage/plugins/catalog-backend/src/processing/DefaultCatalogProcessingEngine.ts#L108-L156)

```typescript
this.pollingIntervalMs = options.pollingIntervalMs ?? 1_000;
// ...
loadTasks: async count => {
  try {
    const { items } = await this.processingDatabase.transaction(async tx => {
      return this.processingDatabase.getProcessableEntities(tx, { processBatchSize: count });
    });
    return items;
  } catch (error) {
    this.logger.warn('Failed to load processing items', error);
    return [];  // <-- Returns empty, no backoff
  }
},
```

**Problem:** The catalog processing engine polls the database at a fixed interval (default 1 second):
- **No adaptive backoff** — if the database is failing, the engine continues polling every second
- **No circuit breaker** — persistent database failures generate one warning per second forever
- When `loadTasks` returns empty due to an error, the pipeline immediately polls again
- No distinction between "no work available" and "database is down"

**Impact:** Under database stress, the processing engine amplifies the problem with continuous 1-second polling.

---

### 9. Catalog Processing — `onProcessingError` Callback Has No Error Boundary

**File:** [`DefaultCatalogProcessingEngine.ts`](file:///Users/binhnt/Lab/dev/backstage/plugins/catalog-backend/src/processing/DefaultCatalogProcessingEngine.ts#L263-L276)

```typescript
Promise.resolve(undefined)
  .then(() =>
    this.onProcessingError?.({
      unprocessedEntity,
      errors: result.errors,
    }),
  )
  .catch(error => {
    this.logger.debug(
      `Processing error listener threw an exception, ${stringifyError(error)}`,
    );
  });
```

**Problem:** The `onProcessingError` callback is invoked as a fire-and-forget Promise:
- Errors from the callback are logged at `debug` level — effectively invisible in production
- The callback runs **after** the database transaction scope — if it needs transactional consistency, it doesn't get it
- Using `Promise.resolve(undefined).then(...)` is an unusual pattern that creates an unnecessary microtask
- The callback receives the full `unprocessedEntity` — which may contain sensitive annotations

**Impact:** Error handling callbacks can silently fail, and operators won't know their error processing logic is broken.

---

### 10. Scaffolder Task Broker — Event Polling Loop with Fixed 1-Second Delay

**File:** [`StorageTaskBroker.ts`](file:///Users/binhnt/Lab/dev/backstage/plugins/scaffolder-backend/src/scaffolder/tasks/StorageTaskBroker.ts#L417-L452)

```typescript
event$(options: { taskId: string; after?: number; }): Observable<{ events: SerializedTaskEvent[] }> {
  return new ObservableImpl(observer => {
    let cancelled = false;
    (async () => {
      while (!cancelled) {
        const result = await this.storage.listEvents({ taskId, after });
        const { events } = result;
        if (events.length) {
          after = events[events.length - 1].id;
          observer.next(result);
        }
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    })();
    return () => { cancelled = true; };
  });
}
```

**Problem:** The event streaming mechanism uses a polling loop with a hardcoded 1-second delay:
- **Not event-driven** — polls the database every second regardless of activity
- **N+1 query problem** — each connected client (e.g., browser tab watching a task) creates its own polling loop
- With 100 concurrent task observers, the database receives 100 queries/second just for event polling
- **No cleanup on error** — if `this.storage.listEvents()` throws, the error propagates to the observer but the loop continues
- The `cancelled` flag is checked after the `setTimeout`, not before — there's a 1-second delay between unsubscribe and actual stop

**Impact:** Significant database load under concurrent usage. Not scalable for production environments with many simultaneous scaffolder users.

---

### 11. Scaffolder Task Heartbeat — Recursive setTimeout with No Guard

**File:** [`StorageTaskBroker.ts`](file:///Users/binhnt/Lab/dev/backstage/plugins/scaffolder-backend/src/scaffolder/tasks/StorageTaskBroker.ts#L202-L216)

```typescript
private startTimeout() {
  this.heartbeatTimeoutId = setTimeout(async () => {
    try {
      await this.storage.heartbeatTask(this.task.taskId);
      this.startTimeout();  // <-- recursive call
    } catch (error) {
      this.isDone = true;
      this.logger.error(`Heartbeat for task ${this.task.taskId} failed`, error);
    }
  }, 1000);
}
```

**Problem:**
- **Recursive `setTimeout`** with no maximum retry count — a network blip followed by recovery would silently resume heartbeats forever
- **Single heartbeat failure kills the task** — `this.isDone = true` is set on the first failure, with no retry
- No exponential backoff for transient failures
- The `heartbeatTimeoutId` is a `setTimeout` return value that may not be properly cleaned up if the task completes between the timeout scheduling and firing

**Impact:** A single transient database hiccup causes a running scaffolder task to be abandoned and marked as stale.

---

### 12. Permission Backend — Default Allow-All Policy in Example Backend

**File:** [`index.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend/src/index.ts#L58-L60)

```typescript
backend.add(
  import('@backstage/plugin-permission-backend-module-allow-all-policy'),
);
```

**Problem:** The example backend uses an "allow all" permission policy, and this pattern is likely copied by many production deployments:
- The `allow-all-policy` module permits every action for every user
- Documentation and examples normalize this insecure default
- No warning is logged at startup when using this policy in production

**Impact:** Many production Backstage deployments likely run with no effective permission enforcement due to copy-paste from the example.
