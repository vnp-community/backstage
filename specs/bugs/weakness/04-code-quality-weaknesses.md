# Code Quality & Maintainability Weaknesses — Backstage Backend

## SEVERITY: MEDIUM

---

### 1. Excessive Use of `as any` Type Assertions

**File:** [`httpAuthServiceFactory.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/httpAuth/httpAuthServiceFactory.ts#L155-L201)

```typescript
async credentials<TAllowed extends keyof BackstagePrincipalTypes = 'unknown'>(
  req: Request<any, any, any, any, any>,
  // ...
): Promise<BackstageCredentials<BackstagePrincipalTypes[TAllowed]>> {
  // ...
  if (!allowed) {
    return credentials as any;  // <-- unsafe cast
  }
  if (this.#auth.isPrincipal(credentials, 'none')) {
    if (allowed.includes('none' as TAllowed)) {
      return credentials as any;  // <-- unsafe cast
    }
  // ... more `as any` casts
```

**Problem:** The `credentials()` method uses `as any` at every return point instead of proper generic type narrowing. This:
- Bypasses TypeScript's type safety at the most security-critical boundary
- Makes it impossible for TypeScript to catch type errors in credential handling
- Breaks IDE autocompletion and refactoring tools for downstream consumers

**Impact:** Type safety holes in authentication code — the compiler cannot verify that the returned credentials match the expected principal type.

---

### 2. Token Stored as Non-Enumerable Property — Fragile Pattern

**File:** [`helpers.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/auth/helpers.ts#L38-L51)

```typescript
Object.defineProperties(result, {
  token: {
    enumerable: false,
    configurable: true,
    writable: true,
    value: token,
  },
  // ...
});
```

**Problem:** Tokens are stored as non-enumerable, configurable, writable properties on credential objects. This pattern:
- Can be accidentally overwritten (writable: true)
- Can be removed or reconfigured (configurable: true)
- Is invisible to `JSON.stringify`, `Object.keys`, spread operators — but accessible via `Object.getOwnPropertyDescriptor`
- Relies on the `InternalBackstageCredentials` type having a `token` field that doesn't exist in the public type, creating a hidden contract

**Impact:** Fragile security by obscurity rather than proper encapsulation. Any code with access to the credential object can read or modify the token.

---

### 3. Credential Version Check is a String Comparison

**File:** [`helpers.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/auth/helpers.ts#L119-L123)

```typescript
if (internalCredentials.version !== 'v1') {
  throw new Error(`Invalid credential version ${internalCredentials.version}`);
}
```

**Problem:** Credential version validation:
- Uses a simple string check with no forward-compatibility logic
- The error message exposes the internal version field
- No mechanism for version negotiation or graceful degradation
- Adding a `v2` credential format would require all consumers to be updated simultaneously

**Impact:** Tight version coupling makes credential format evolution difficult.

---

### 4. Duplicated Token Verification Options Pattern

**File:** [`UserTokenHandler.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/auth/user/UserTokenHandler.ts#L82-L111)

```typescript
#getTokenVerificationOptions(token: string): JWTVerifyOptions | undefined {
  try {
    const { typ } = decodeProtectedHeader(token);
    if (typ === tokenTypes.user.typParam) {
      return { requiredClaims: ['iat', 'exp', 'sub'], typ: tokenTypes.user.typParam };
    }
    if (typ === tokenTypes.limitedUser.typParam) {
      return { requiredClaims: ['iat', 'exp', 'sub'], typ: tokenTypes.limitedUser.typParam };
    }
    const { aud } = decodeJwt(token);
    if (aud === tokenTypes.user.audClaim) {
      return { audience: tokenTypes.user.audClaim };
    }
  } catch { /* ignore */ }
  return undefined;
}
```

**Problem:**
- The method decodes the token header **twice** (once for `typ`, once for `aud` on fallback) — wasteful and inconsistent
- The legacy `aud`-based path has a less strict verification (no `requiredClaims`) — different security levels for the same operation
- The bare `catch` block silently swallows malformed token errors — hides issues during development
- No logging of why a token was not recognized

**Impact:** Code is hard to maintain and has subtle security inconsistencies between token verification paths.

---

### 5. Error Handler Relies on `(error as any)[field]` Access Pattern

**File:** [`MiddlewareFactory.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/rootHttpRouter/http/MiddlewareFactory.ts#L332-L344)

```typescript
function getStatusCode(error: Error): number {
  const knownStatusCodeFields = ['statusCode', 'status'];
  for (const field of knownStatusCodeFields) {
    const statusCode = (error as any)[field];
    if (typeof statusCode === 'number' && (statusCode | 0) === statusCode && ...) {
      return statusCode;
    }
  }
```

**Problem:** Status code extraction iterates over string field names and accesses them via `as any`:
- Any error object with a numeric `status` or `statusCode` field will have it used, regardless of intent
- This can conflict with error types from third-party libraries that use these fields for different purposes
- No validation that the status code field actually relates to HTTP status

**Impact:** Third-party error objects may unexpectedly produce incorrect HTTP status codes.

---

### 6. `connection.client.config.includes('sqlite3')` — String Matching on Config Object

**File:** [`DatabaseManager.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/database/DatabaseManager.ts#L126)

```typescript
if (connection.client.config.includes('sqlite3')) {
  return; // sqlite3 does not support destroy, it hangs
}
```

**Problem:** The code performs `String.includes('sqlite3')` on a Knex client config object:
- `connection.client.config` is an object, so `.includes()` would throw a TypeError in most cases
- This code likely relies on implicit `toString()` conversion, which is fragile and non-obvious
- Different Knex versions may change the internal `client.config` structure

**Impact:** Potential runtime error if the Knex internal API changes. The SQLite detection logic is unreliable.

---

### 7. Inconsistent Error Messages — Mix of Technical and User-Facing

**Files:** Multiple across the codebase

**Examples:**
```typescript
// Technical (good for debugging, bad for users)
throw new AuthenticationError('Invalid plugin token: forbidden subject format');

// Vague (bad for everyone)
throw new AuthenticationError('Illegal token');

// Internal detail leaking
throw new Error(`Unsupported database client type '${client}' specified for plugin '${pluginId}'`);

// Overly generic
throw new NotAllowedError('Unknown principal type, this should never happen');
```

**Problem:** Error messages inconsistently mix:
- Internal implementation details (`plugin token`, `subject format`)
- Vague descriptions (`Illegal token`)
- "Should never happen" assertions that provide no actionable context
- No error codes for programmatic handling

**Impact:** Difficult to debug in production and confusing error messages for API consumers.

---

### 8. Boolean Config Pattern `backend.rateLimit = true` vs Config Object

**File:** [`MiddlewareFactory.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/rootHttpRouter/http/MiddlewareFactory.ts#L250-L253)

```typescript
const useDefaults = this.#config.getOptional('backend.rateLimit') === true;
const rateLimitOptions = useDefaults
  ? undefined
  : this.#config.getOptionalConfig('backend.rateLimit');
```

**Problem:** The `backend.rateLimit` config key can be either:
- A boolean `true` (enable with defaults)
- A config object (enable with custom settings)
- A config object with `global: false` (disable global rate limiting)
- Not present (disable entirely)

This creates a confusing 4-way state that's difficult to document and validate:
- `backend.rateLimit: true` → use defaults
- `backend.rateLimit: { windowMs: 60000 }` → use custom settings
- `backend.rateLimit: { global: false }` → explicitly disable
- (not set) → implicitly disabled

**Impact:** Config API inconsistency makes it error-prone for operators to configure rate limiting correctly.

---

### 9. Multiple Configuration Key Paths for Same Concept

**File:** [`DatabaseManager.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/database/DatabaseManager.ts#L105-L109)

```typescript
const skip =
  this.options?.migrations?.skip ??
  this.config.getOptionalBoolean(`plugin.${pluginId}.skipMigrations`) ??
  this.config.getOptionalBoolean('skipMigrations') ??
  false;
```

**Problem:** Migration skip behavior is controlled by 3 different sources with a precedence cascade:
1. Programmatic option (`this.options?.migrations?.skip`)
2. Per-plugin config (`plugin.<id>.skipMigrations`)
3. Global config (`skipMigrations`)

This makes it unclear which config takes effect and creates opportunity for misunderstanding.

**Impact:** Operators may set the wrong config key and have migrations unexpectedly run or be skipped.

---

### 10. `console.error` Used in Config Reload Instead of Logger

**File:** [`loader.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/config-loader/src/loader.ts#L144)

```typescript
} catch (error) {
  if (loaded) {
    console.error(`Failed to reload configuration, ${error}`);
  }
```

**Problem:** Configuration reload failures use `console.error` instead of the structured logger:
- Bypasses any configured log formatting, filtering, or transport
- Will not appear in structured log aggregation systems (Elasticsearch, Datadog, etc.)
- No log level, no metadata, no correlation ID
- The error is interpolated into a string, losing stack trace

**Impact:** Critical configuration reload failures are invisible to production monitoring systems.
