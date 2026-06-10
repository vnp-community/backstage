# Security Weaknesses — Backstage Backend

## SEVERITY: HIGH

---

### 1. `unsafe-eval` in Content Security Policy (CSP)

**File:** [`readHelmetOptions.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/rootHttpRouter/http/readHelmetOptions.ts#L97)

```typescript
result['script-src'] = ["'self'", "'unsafe-eval'"];
```

**Problem:** The CSP explicitly allows `unsafe-eval` as a script source, which is one of the most dangerous CSP directives. This enables:
- Cross-Site Scripting (XSS) attacks via `eval()`, `Function()`, `setTimeout(string)`, and `setInterval(string)`
- Code injection through template literal manipulation
- Potential supply-chain attacks where compromised dependencies inject eval-based code

**Root Cause:** The codebase acknowledges this is due to non-precompiled AJV usage in the frontend (see TODO comment on line 96).

**Impact:** Any XSS vector in the frontend can be escalated to arbitrary code execution in the browser context, bypassing the primary CSP defense.

---

### 2. `disableDefaultAuthPolicy` Produces Empty Token

**File:** [`DefaultAuthService.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/auth/DefaultAuthService.ts#L163-L165)

```typescript
if (type === 'none' && this.disableDefaultAuthPolicy) {
  return { token: '' };
}
```

**Problem:** When the default auth policy is disabled, unauthenticated credentials are "forwarded" by returning an empty token string. This empty token:
- Bypasses all downstream authentication checks that rely on token presence
- Can be used to impersonate service-level access in plugin-to-plugin communication
- Creates an implicit "open door" for all service calls when the policy is disabled

**Impact:** Any deployment that disables the default auth policy (e.g., for development) and accidentally promotes that config to production gets fully open backend access.

---

### 3. Limited User Token Re-signature Bypass via `uip` Claim

**File:** [`UserTokenHandler.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/auth/user/UserTokenHandler.ts#L113-L157)

```typescript
createLimitedUserToken(backstageToken: string) {
  const [headerRaw, payloadRaw] = backstageToken.split('.');
  // ...
  const limitedUserToken = [
    base64url.encode(JSON.stringify({ typ: tokenTypes.limitedUser.typParam, alg: header.alg, kid: header.kid })),
    base64url.encode(JSON.stringify({ sub: payload.sub, iat: payload.iat, exp: payload.exp })),
    payload.uip,  // <-- Reuses the original "uip" as the signature
  ].join('.');
```

**Problem:** The limited user token is constructed by **manually reassembling** JWT parts rather than using proper cryptographic signing. The `uip` claim from the original full token is reused verbatim as the "signature" part. This means:
- The limited token is **not independently signed** — it's a truncated version of the original
- If the `uip` derivation logic is ever weakened or the original token is compromised, all limited tokens derived from it are also compromised
- The approach assumes the `uip` claim is unforgeable, which is a non-standard JWT guarantee

**Impact:** The limited user token mechanism relies on an implicit assumption about `uip` immutability rather than standard JWT signatures. A vulnerability in the `uip` generation could allow token forgery.

---

### 4. No Token Revocation Mechanism

**Files:**
- [`DefaultAuthService.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/auth/DefaultAuthService.ts)
- [`PluginTokenHandler.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/auth/plugin/PluginTokenHandler.ts)

**Problem:** There is no token revocation list (CRL/blacklist) for any token type:
- User tokens remain valid until expiration
- Plugin-to-plugin tokens cannot be revoked
- External access tokens have no revocation mechanism
- Limited user tokens (cookies) cannot be force-expired server-side

**Impact:** If a token is compromised, there is no way to invalidate it before its natural expiration. This is particularly dangerous for long-lived external access tokens.

---

### 5. Cookie `secure` Flag Based on Hostname, Not Protocol

**File:** [`httpAuthServiceFactory.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/httpAuth/httpAuthServiceFactory.ts#L264-L266)

```typescript
const secure =
  externalBaseUrl.protocol === 'https:' ||
  externalBaseUrl.hostname === 'localhost';
```

**Problem:** The `secure` flag is set to `true` whenever the hostname is `localhost`, regardless of protocol. This means:
- On `http://localhost`, cookies are marked as `secure` but are still transmitted over HTTP
- The `sameSite: 'none'` attribute (set when `secure` is `true`) further weakens cookie protection
- A proxy sitting between client and a localhost backend can intercept cookies

**Impact:** Cookie-based authentication tokens may be transmitted insecurely in certain deployment configurations (e.g., behind an HTTP reverse proxy).

---

### 6. Missing `form-action` CSP Directive

**File:** [`readHelmetOptions.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/rootHttpRouter/http/readHelmetOptions.ts#L99-L102)

```typescript
// TODO(Rugvip): This is removed so that we maintained backwards compatibility
delete result['form-action'];
```

**Problem:** The `form-action` CSP directive is explicitly deleted for backward compatibility. Without it:
- Forms on the page can be submitted to arbitrary external URLs
- Phishing attacks via form redirection are possible
- Data exfiltration via form submissions to attacker-controlled servers

**Impact:** Medium — depends on the application having user-submitted content or XSS vulnerabilities.

---

### 7. Helmet Security Headers Disabled for Backward Compatibility

**File:** [`readHelmetOptions.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/rootHttpRouter/http/readHelmetOptions.ts#L44-L48)

```typescript
crossOriginEmbedderPolicy: false,
crossOriginOpenerPolicy: false,
crossOriginResourcePolicy: false,
originAgentCluster: false,
```

**Problem:** Four critical security headers are explicitly disabled:
- **Cross-Origin-Embedder-Policy**: Prevents Spectre-like side-channel attacks
- **Cross-Origin-Opener-Policy**: Prevents window reference attacks
- **Cross-Origin-Resource-Policy**: Prevents cross-origin resource leaks
- **Origin-Agent-Cluster**: Prevents cross-origin process sharing

**Impact:** The backend is vulnerable to Spectre-class side-channel attacks and cross-origin data leaks in browser contexts.

---

### 8. Rate Limiting Disabled by Default

**File:** [`MiddlewareFactory.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/rootHttpRouter/http/MiddlewareFactory.ts#L242-L248)

```typescript
rateLimit(): RequestHandler {
  const enabled = this.#config.has('backend.rateLimit');
  if (!enabled) {
    return (_req: Request, _res: Response, next: NextFunction) => {
      next();
    };
  }
```

**Problem:** Rate limiting is completely disabled unless explicitly configured. Most Backstage deployments likely don't configure this, leaving the API open to:
- Brute force authentication attempts
- Denial of Service (DoS) attacks
- Resource exhaustion attacks on expensive endpoints (e.g., catalog refresh, scaffolder)

**Impact:** Any publicly accessible Backstage deployment without explicit rate limiting configuration is vulnerable to abuse.

---

### 9. Error Response Leaks Internal Details in Development Mode

**File:** [`MiddlewareFactory.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/rootHttpRouter/http/MiddlewareFactory.ts#L294-L295)

```typescript
const showStackTraces =
  options.showStackTraces ?? process.env.NODE_ENV === 'development';
```

**Problem:** Stack traces are automatically included in error responses during development. If `NODE_ENV` is not explicitly set to `production` in a deployed environment:
- Full file paths are leaked
- Internal module structures are exposed
- Database query patterns may be revealed in stack traces

**Impact:** Information disclosure that aids attackers in crafting targeted exploits.

---

### 10. JWKS Endpoint Has No Authentication

**File:** [`PluginTokenHandler.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/auth/plugin/PluginTokenHandler.ts#L192-L196)

```typescript
const res = await fetch(
  `${await this.discovery.getBaseUrl(targetPluginId)}/.backstage/auth/v1/jwks.json`,
);
```

**Problem:** The JWKS endpoints (`.backstage/auth/v1/jwks.json` and `.well-known/jwks.json`) are fetched without any authentication. An attacker on the internal network can:
- Enumerate which plugins are deployed
- Understand the key rotation schedule
- Potentially perform a JWKS confusion attack if they can intercept the JWKS response

**Impact:** Information disclosure and potential for key confusion attacks in deployments with weak network isolation.
