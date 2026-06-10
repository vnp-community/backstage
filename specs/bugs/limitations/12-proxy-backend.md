# Limitation: Proxy Backend

## Package
`@backstage/plugin-proxy-backend`

## Source Files
- `plugins/proxy-backend/src/service/router.ts`

---

## L-PRX-001: Header Allowlist Only — No Header Validation

**Severity**: Medium  
**Type**: Security Gap

The proxy filters headers by allowlist but does not validate header values:

```typescript
const requestHeaderAllowList = new Set<string>([
  ...safeForwardHeaders,
  ...((fullConfig.headers && Object.keys(fullConfig.headers)) || []),
  ...(fullConfig.allowedHeaders || []),
].map(h => h.toLocaleLowerCase()));

headerNames.forEach(h => {
  if (!requestHeaderAllowList.has(h.toLocaleLowerCase())) {
    delete req.headers[h];
  }
});
```

**Impact**:
- A malicious client could send allowed headers (e.g., `content-type`) with crafted values
- No validation of header values for injection attacks (CRLF injection in allowed headers)

---

## L-PRX-002: Proxy Config Reload Uses JSON Stringify Comparison

**Severity**: Low  
**Type**: Correctness Risk

Config change detection for hot-reload uses string comparison:

```typescript
const newKey = JSON.stringify(newProxyConfig);
if (currentKey !== newKey) {
  currentKey = newKey;
  currentRouter = Router();
  configureMiddlewares(...);
}
```

**Impact**:
- JSON key ordering is not guaranteed to be stable across Node.js versions/runtimes
- Two semantically identical configs with different key orders may trigger unnecessary router rebuilds
- Config rebuilding drops all in-flight proxy requests

---

## L-PRX-003: No Request Body Size Limit

**Severity**: Medium  
**Type**: Security / Resource

The proxy does not enforce a maximum body size on proxied requests:

```typescript
return createProxyMiddleware(filter, fullConfig);
```

**Impact**:
- Clients can send arbitrarily large request bodies through the proxy
- Memory spike risk when a large upload is buffered through Node.js
- No protection against slow-loris style attacks on body consumption

---

## L-PRX-004: `dangerously-allow-unauthenticated` is a String Policy

**Severity**: Medium  
**Type**: Security Naming Risk

The most permissive policy is controlled purely by string matching:

```typescript
const credentialsPolicyCandidates = [
  'require',
  'forward',
  'dangerously-allow-unauthenticated',
];
```

**Impact**:
- A typo in the config string silently falls back to validation error — no autocomplete in YAML
- The word "dangerously" signals the risk but does not prevent accidental misconfiguration
- No audit log when unauthenticated proxy routes are accessed

---

## L-PRX-005: Response Header Allowlist Shares Same `allowedHeaders` Config

**Severity**: Low  
**Type**: Design Ambiguity

Request and response header filtering both use `fullConfig.allowedHeaders`:

```typescript
const responseHeaderAllowList = new Set<string>([
  ...safeForwardHeaders,
  ...(fullConfig.allowedHeaders || []),
]);
```

**Impact**:
- Cannot independently configure which request headers to forward vs. which response headers to return
- A header needed in the response but not in the request (or vice versa) forces inclusion in both directions

---

## L-PRX-006: `host` Header is Always in Safe Forward List

**Severity**: Low  
**Type**: Security Nuance

The `host` header is in `safeForwardHeaders` with an important caveat in the comment:

```typescript
// host is overridden by default. if changeOrigin is configured to false,
// we assume this is a intentional and should also be forwarded.
'host',
```

**Impact**:
- When `changeOrigin: false` is set, the original `Host` header is forwarded to the proxy target
- This can be used for host header injection attacks if the proxy target is misconfigured
- No warning when operators set `changeOrigin: false`

---

## L-PRX-007: `reviveConsumedRequestBodies` Requires Explicit Opt-In

**Severity**: Low  
**Type**: Usability

Body revival for consumed request bodies defaults to off:

```typescript
const reviveConsumedRequestBodies =
  options.config.getOptionalBoolean('proxy.reviveConsumedRequestBodies') ?? false;
```

**Impact**:
- When a body-parsing middleware (e.g., `express.json()`) runs before the proxy, the body is consumed
- Without `reviveConsumedRequestBodies: true`, POST/PUT requests silently fail with empty bodies
- This is a non-obvious footgun that is hard to debug

---

## L-PRX-008: No Timeout Configuration per Proxy Route

**Severity**: Medium  
**Type**: Resilience

The proxy middleware does not expose request timeout configuration per route:

```typescript
fullConfig = rest;  // timeout not in ProxyConfig options
```

**Impact**:
- A slow upstream target can hold a connection open indefinitely
- No circuit breaking — all workers can be exhausted by one slow upstream
- Default Node.js HTTP timeout (typically 0 = infinite) applies to all proxy routes
