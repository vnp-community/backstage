# Backstage Security Audit Report

**Ngày phân tích:** 2026-05-28  
**Phiên bản:** Latest (main branch)  
**Phạm vi:** Core packages, backend plugins, auth system, proxy, scaffolder, catalog, techdocs

---

## Tóm tắt

Phân tích mã nguồn Backstage phát hiện **12 nhóm vấn đề bảo mật** ở các mức độ nghiêm trọng khác nhau. Một số đã có biện pháp giảm thiểu (mitigations) trong code, nhưng vẫn tiềm ẩn rủi ro nếu cấu hình sai hoặc mở rộng không đúng cách.

| Mức độ | Số lượng |
|--------|----------|
| 🔴 CRITICAL | 3 |
| 🟠 HIGH | 6 |
| 🟡 MEDIUM | 6 |
| 🔵 LOW | 5 |

---

## 🔴 CRITICAL — Mức độ Nghiêm trọng

### SEC-001: CSP `unsafe-eval` trong Content Security Policy mặc định

**File:** `packages/backend-defaults/src/entrypoints/rootHttpRouter/http/readHelmetOptions.ts:97`

```typescript
// TODO(Rugvip): We currently use non-precompiled AJV for validation in the frontend, which uses eval.
//               It should be replaced by any other solution that doesn't require unsafe-eval.
result['script-src'] = ["'self'", "'unsafe-eval'"];
```

**Vấn đề:** CSP mặc định cho phép `unsafe-eval` trong `script-src`. Điều này cho phép thực thi JavaScript tùy ý thông qua `eval()`, `Function()`, `setTimeout(string)`, v.v. Đây là điều kiện tiên quyết cho rất nhiều cuộc tấn công XSS.

**Tác động:** Nếu kẻ tấn công có thể inject bất kỳ đoạn script nào (qua XSS lỗ hổng khác), `unsafe-eval` cho phép họ thực thi mã tùy ý trong trình duyệt của nạn nhân.

**Khuyến nghị:**
- Thay thế AJV bằng phiên bản pre-compiled hoặc thư viện validation khác không cần `eval()`
- Loại bỏ `unsafe-eval` khỏi CSP mặc định
- Nếu không thể loại bỏ ngay, sử dụng `nonce-based` CSP thay thế

---

### SEC-002: SQL Injection tiềm tàng qua string interpolation trong raw queries

**Files:**
- `plugins/catalog-backend/src/database/DefaultProcessingDatabase.ts:223-225`
- `plugins/catalog-backend/src/database/operations/stitcher/getDeferredStitchableEntities.ts:104-107`

```typescript
// MySQL - refreshInterval là số nhưng được interpolated trực tiếp
return tx.raw(`now() + interval ${refreshInterval} second`);

// PostgreSQL
return tx.raw(`now() + interval '${refreshInterval} seconds'`);
```

**Vấn đề:** Biến `refreshInterval` và `seconds` được nhúng trực tiếp vào raw SQL queries thay vì sử dụng parameterized queries. Mặc dù giá trị này đến từ config (không phải user input trực tiếp), đây là một **anti-pattern nguy hiểm**:

1. Nếu config bị compromise hoặc đọc từ nguồn không tin cậy, SQL injection có thể xảy ra
2. SQLite version sử dụng parameterized (`?`) nhưng MySQL/PostgreSQL không — cho thấy sự không nhất quán
3. Nếu tương lai code được refactor và `refreshInterval` nhận giá trị từ user input, sẽ tạo lỗ hổng nghiêm trọng

**Khuyến nghị:**
- Sử dụng parameterized queries cho tất cả các DB engine, tương tự như SQLite version
- Validate rằng `refreshInterval`/`seconds` luôn là số nguyên trước khi sử dụng

---

### SEC-003: Scaffolder Shell Command Execution — Thiếu kiểm soát command/args

**File:** `plugins/scaffolder-node/src/actions/executeShellCommand.ts:47-85`

```typescript
export async function executeShellCommand(
  options: ExecuteShellCommandOptions,
): Promise<void> {
  const { command, args, options: spawnOptions, ... } = options;
  await new Promise<void>((resolve, reject) => {
    const process = spawn(command, args, spawnOptions);
    // ...
  });
}
```

**Vấn đề:** Hàm `executeShellCommand` thực thi lệnh shell tùy ý. Mặc dù sử dụng `spawn` (an toàn hơn `exec`), không có:
- Whitelist các command được phép
- Validation/sanitization cho `command` và `args`
- Sandboxing cho child process (không có resource limits, network isolation)

Custom scaffolder actions của bên thứ ba có thể truyền user-controlled input vào `command` hoặc `args`, dẫn đến **Remote Code Execution (RCE)**.

**Tương tự ở:** `plugins/techdocs-node/src/stages/generate/helpers.ts:54-82` — `runCommand` function

**Khuyến nghị:**
- Implement command whitelist cho scaffolder actions
- Thêm sandboxing (namespace, cgroup) cho child processes
- Log tất cả command executions cho audit trail
- Validate và sanitize arguments trước khi spawn

---

## 🟠 HIGH — Mức độ Cao

### SEC-004: Proxy Backend — `dangerously-allow-unauthenticated` cho phép SSRF

**File:** `plugins/proxy-backend/src/service/router.ts:99-104`

```typescript
if (credentialsPolicy === 'dangerously-allow-unauthenticated') {
  httpRouterService.addAuthPolicy({
    path: route,
    allow: 'unauthenticated',
  });
}
```

**Vấn đề:** Proxy backend hỗ trợ chế độ `dangerously-allow-unauthenticated`, cho phép bất kỳ ai gửi request qua proxy mà không cần xác thực. Kết hợp với `credentials: 'forward'` (line 182: `requestHeaderAllowList.add('authorization')`), điều này tạo ra vector tấn công SSRF:

1. Kẻ tấn công không cần xác thực gửi request qua proxy
2. Proxy forward request đến internal services với credentials
3. Có thể truy cập internal APIs, metadata services (cloud), hoặc private networks

**Tác động:** Server-Side Request Forgery cho phép scan internal network, truy cập cloud metadata (AWS IMDSv1: `169.254.169.254`), hoặc tương tác với internal services.

**Khuyến nghị:**
- Mặc định không cho phép `dangerously-allow-unauthenticated`
- Thêm target URL validation — block private IP ranges, localhost, metadata endpoints
- Log cảnh báo rõ ràng khi tùy chọn này được sử dụng
- Thêm network-level egress filtering

---

### SEC-005: Session Cookie thiếu `httpOnly` flag

**File:** `plugins/auth-backend/src/service/router.ts:124-135`

```typescript
router.use(
  session({
    secret,
    saveUninitialized: false,
    resave: false,
    cookie: { secure: enforceCookieSSL ? 'auto' : false },
    // ⚠️ Thiếu: httpOnly: true
    // ⚠️ Thiếu: sameSite: 'lax' hoặc 'strict'
    store: new KnexSessionStore({ ... }),
  }),
);
```

**Vấn đề:** Session cookie configuration thiếu:
1. **`httpOnly: true`** — mặc dù express-session mặc định là `true`, không explicit setting tạo rủi ro nếu mặc định thay đổi
2. **`sameSite`** — không được đặt, mặc định phụ thuộc vào browser. Thiếu `sameSite` có thể cho phép CSRF attacks
3. **`secure: false`** khi không dùng HTTPS — cookie có thể bị đánh cắp qua HTTP

**Tác động:** Session hijacking qua XSS (nếu `httpOnly` bị tắt) hoặc CSRF attacks (nếu `sameSite` không đúng).

**Khuyến nghị:**
```typescript
cookie: { 
  secure: enforceCookieSSL ? 'auto' : false,
  httpOnly: true,       // Explicit set
  sameSite: 'lax',      // Chống CSRF
  maxAge: 24 * 60 * 60 * 1000,  // Session timeout
}
```

---

### SEC-006: Nunjucks Template Rendering với `autoescape: false`

**Files:**
- `plugins/scaffolder-backend/src/lib/templating/SecureTemplater.ts:37,46`
- `plugins/scaffolder-backend/src/scaffolder/tasks/NunjucksWorkflowRunner.ts:242`

```typescript
const env = module.exports.configure({
  autoescape: false,  // ⚠️ XSS risk
  // ...
});
```

**Vấn đề:** Nunjucks template engine được cấu hình với `autoescape: false`. Điều này có nghĩa output từ template rendering không được HTML-escaped tự động.

**Mitigations hiện có:**
- Template rendering chạy trong `isolated-vm` sandbox (V8 isolate) — giảm RCE risk
- Template output chủ yếu dùng để tạo file, không render trực tiếp thành HTML

**Rủi ro còn lại:**
- Nếu template output được hiển thị trong UI (ví dụ: scaffolder task logs), có thể tạo Stored XSS
- Custom template filters/globals có thể mở rộng attack surface

**Khuyến nghị:**
- Bật `autoescape: true` cho output sẽ được hiển thị trong HTML context
- Sanitize template output trước khi hiển thị trong UI
- Review tất cả custom template filters cho injection risks

---

### SEC-007: Không có Rate Limiting mặc định

**File:** `packages/backend-defaults/src/entrypoints/rootHttpRouter/http/MiddlewareFactory.ts:242-269`

```typescript
rateLimit(): RequestHandler {
  const enabled = this.#config.has('backend.rateLimit');
  // ...
  // Global rate limiting disabled
  if (rateLimitOptions && rateLimitOptions.getOptionalBoolean('global') === false) {
    return noopMiddleware;
  }
  // ...
}
```

**Vấn đề:** Rate limiting chỉ hoạt động khi được cấu hình qua `backend.rateLimit`. **Mặc định không bật**, nghĩa là:
- Auth endpoints có thể bị brute-force
- API endpoints có thể bị DoS
- Scaffolder/catalog endpoints có thể bị abuse

**Khuyến nghị:**
- Bật rate limiting mặc định với giá trị hợp lý (ví dụ: 100 req/phút/IP)
- Rate limit riêng cho auth endpoints (stricter: 10 req/phút/IP)
- Rate limit cho scaffolder task creation

---

### SEC-013: Events Backend — HTTP Ingress không xác thực

**File:** `plugins/events-backend/src/service/EventsPlugin.ts:149-152`

```typescript
httpRouter.addAuthPolicy({
  allow: 'unauthenticated',
  path: '/http',
});
```

**Vấn đề:** Events HTTP ingress endpoint (`/http/*`) cho phép gửi events mà không cần xác thực. Endpoint này được thiết kế để nhận webhooks từ external services (GitHub, GitLab, etc.), nhưng **bất kỳ ai trên mạng** đều có thể gửi events giả vào hệ thống.

**Tác động:**
- **Event Injection:** Kẻ tấn công có thể gửi events giả mạo (fake GitHub webhooks) để trigger các hành động không mong muốn
- **Event Flooding/DoS:** Không có rate limiting riêng cho ingress
- **Supply Chain Attack:** Fake catalog refresh events có thể khiến hệ thống reload entities từ nguồn không tin cậy

**Khuyến nghị:**
- Implement webhook secret validation (GitHub `X-Hub-Signature-256`, GitLab token, etc.)
- Thêm IP whitelist cho webhook sources
- Rate limit trên `/http/*` endpoint
- Log và monitor tất cả incoming events để phát hiện anomalies

---

### SEC-014: OIDC PKCE — Cho phép `plain` code challenge method

**File:** `plugins/auth-backend/src/service/OidcService.ts:280-284, 660-661`

```typescript
if (!codeChallengeMethod || !['S256', 'plain'].includes(codeChallengeMethod)) {
  throw new InputError('Invalid code_challenge_method');
}

// In verifyPkce:
if (!opts.method || opts.method === 'plain') {
  return opts.codeChallenge === opts.codeVerifier;  // ⚠️ Plain text comparison
}
```

**Vấn đề:** OIDC implementation hỗ trợ `plain` PKCE challenge method, đặt `code_challenge == code_verifier` mà không hash. Điều này **vô hiệu hóa mục đích bảo mật của PKCE**:

1. Nếu kẻ tấn công intercept authorization request (chứa `code_challenge`), họ có thể sử dụng trực tiếp giá trị đó làm `code_verifier`
2. RFC 7636 khuyến nghị **CHỈ sử dụng S256** trong production

Thêm vào đó, DCR clients (`resolveDcrClient`) không bắt buộc PKCE (`requiresPkce: false`), trong khi chỉ CIMD clients bắt buộc.

**Khuyến nghị:**
- Loại bỏ support cho `plain` method — chỉ cho phép `S256`
- Bắt buộc PKCE cho tất cả public clients (bao gồm DCR clients)
- Cấu hình mặc định `code_challenge_methods_supported: ['S256']`

---

## 🟡 MEDIUM — Mức độ Trung bình

### SEC-008: `res.send()` thay vì `res.json()` — Tiềm năng Content-Type Sniffing

**Files:**
- `plugins/app-backend/src/service/router.ts:321` — `res.send(injectResult.indexHtmlContent)` *(có Content-Type header)*
- `plugins/app-backend/src/lib/assets/createStaticAssetMiddleware.ts:60` — `res.send(asset.content)` *(có res.type())*
- `plugins/techdocs-node/src/stages/publish/openStackSwift.ts:266` — `res.send(await streamToBuffer(stream))`

**Vấn đề:** Theo chính SECURITY.md của dự án, nên dùng `.json()` thay vì `.send()`. Mặc dù các trường hợp trên phần lớn đã set Content-Type, vẫn có rủi ro nếu:
- Content-Type bị override hoặc bỏ qua
- Browser thực hiện content sniffing (mặc dù có helmet X-Content-Type-Options)

**Khuyến nghị:**
- Review tất cả `res.send()` calls để đảm bảo Content-Type luôn được set rõ ràng
- Ưu tiên sử dụng `res.json()` cho JSON responses

---

### SEC-009: Cross-Origin Policy bị tắt mặc định

**File:** `packages/backend-defaults/src/entrypoints/rootHttpRouter/http/readHelmetOptions.ts:44-48`

```typescript
// These are all disabled in order to maintain backwards compatibility
crossOriginEmbedderPolicy: false,
crossOriginOpenerPolicy: false,
crossOriginResourcePolicy: false,
originAgentCluster: false,
```

**Vấn đề:** Tất cả cross-origin security headers đều bị tắt vì "backwards compatibility". Điều này để lại các attack vectors:
- **COEP disabled:** Cho phép cross-origin resource loading không kiểm soát
- **COOP disabled:** Cho phép cross-origin window interaction (Spectre attacks)
- **CORP disabled:** Cho phép cross-origin resource access

**Khuyến nghị:**
- Bật `crossOriginResourcePolicy: 'same-origin'` làm mặc định
- Cung cấp migration guide cho adopters để bật COEP/COOP
- Thêm cảnh báo deprecation cho việc tắt các headers này

---

### SEC-010: Guest Provider có thể bật ngoài Development

**File:** `plugins/auth-backend-module-guest-provider/src/authenticator.ts:24-28`

```typescript
initialize({ config }) {
  const allowOutsideDev = config.getOptionalBoolean(
    'dangerouslyAllowOutsideDevelopment',
  );
  return process.env.NODE_ENV !== 'development' && allowOutsideDev !== true;
},
```

**Vấn đề:** Guest provider cho phép đăng nhập không cần credentials. Mặc dù yêu cầu `dangerouslyAllowOutsideDevelopment: true`, config này có thể bị vô tình bật trong production. Guest user có token với identity `user:development/guest`, có thể có quyền truy cập vào tài nguyên nội bộ.

**Tác động:** Truy cập không xác thực vào toàn bộ Backstage instance nếu config sai.

**Khuyến nghị:**
- Thêm startup warning rõ ràng hơn khi guest provider bật ngoài dev
- Giới hạn quyền của guest user mặc định
- Thêm environment variable check bổ sung (không chỉ `NODE_ENV`)

---

### SEC-015: WebSocket Auth Token truyền qua `Sec-WebSocket-Protocol` header

**File:** `plugins/signals-backend/src/service/router.ts:78-87`

```typescript
// Authentication token is passed in Sec-WebSocket-Protocol header as there
// is no other way to pass the token with plain websockets
try {
  const token = request.headers['sec-websocket-protocol'];
  if (token) {
    const credentials = await auth.authenticate(token);
    // ...
  }
} catch (e) {
  // ...
}
```

**Vấn đề:** Bearer token được truyền qua `Sec-WebSocket-Protocol` header. Đây là workaround phổ biến nhưng có rủi ro:

1. **Token exposure trong logs:** Nhiều reverse proxy/load balancer log `Sec-WebSocket-Protocol` header
2. **Không có revocation:** Nếu token bị leak, không có cơ chế invalidation cho WebSocket connections
3. **Unauthenticated fallback:** Nếu token không có, connection vẫn được thiết lập nhưng không có identity (`userIdentity = undefined`). Connection vẫn nhận signals.

**Tác động:** Unauthenticated WebSocket clients có thể eavesdrop trên broadcast signals.

**Khuyến nghị:**
- Bắt buộc authentication cho WebSocket connections — reject nếu không có token
- Implement ticket-based auth: Client lấy one-time ticket qua REST, rồi dùng ticket để upgrade WebSocket
- Kiểm tra connection identity trước khi gửi signals

---

### SEC-016: Lodash Template Injection trong App Config HTML

**File:** `plugins/app-backend/src/lib/config/injectConfigIntoHtml.ts:44-67`

```typescript
const templateSource = compileTemplate(templateContent, {
  interpolate: /<%=([\s\S]+?)%>/g,
});

const indexHtmlContent = templateSource({
  config,
  publicPath,
});

const indexHtmlContentWithConfig = indexHtmlContent.replace(
  '</head>',
  `<script type="backstage.io/config">
  ${JSON.stringify(appConfigs, null, 2)
    .replaceAll('</script', '')
    .replaceAll('<!--', '')}
  </script></head>`,
);
```

**Vấn đề:** 
1. **Lodash Template Engine:** `lodash/template` được sử dụng để render `index.html.tmpl`. Mặc dù chỉ dùng interpolation (`<%= %>`), lodash template cũng hỗ trợ evaluation (`<% %>`). Nếu template file bị compromise, code execution xảy ra.
2. **Config Injection:** App config được inject trực tiếp vào HTML. Sanitization chỉ loại bỏ `</script` và `<!--` nhưng có thể bị bypass qua encoding hoặc event handlers.

**Mitigations hiện có:** Comment trong code ghi nhận rằng "control of the app config effectively means full control of the app" — đây là accepted risk.

**Khuyến nghị:**
- Validate template file content trước khi compile (reject nếu chứa `<% %>` evaluation blocks)
- Sử dụng JSON serialization an toàn hơn cho config injection (ví dụ: base64 encoding)

---

### SEC-017: OIDC Client Secret sử dụng `randomUUID` thay vì high-entropy secret

**File:** `plugins/auth-backend/src/service/OidcService.ts:219-220`

```typescript
const generatedClientId = crypto.randomUUID();
const generatedClientSecret = crypto.randomUUID();
```

**Vấn đề:** Client secret được tạo bằng `crypto.randomUUID()` (UUID v4), cung cấp ~122 bits of entropy. Mặc dù đây là đủ cho hầu hết use cases, OAuth 2.0 best practices (RFC 6819) khuyến nghị **client secrets ít nhất 128 bits of entropy** và nên sử dụng `crypto.randomBytes(32).toString('base64url')` cho higher entropy.

Tích cực: Backstage sử dụng `crypto.timingSafeEqual()` cho client secret verification, tránh timing attacks.

**Khuyến nghị:**
- Sử dụng `crypto.randomBytes(32).toString('base64url')` cho client secrets
- UUID format vẫn phù hợp cho client IDs

---

## 🔵 LOW — Mức độ Thấp

### SEC-011: `form-action` CSP directive bị xóa

**File:** `packages/backend-defaults/src/entrypoints/rootHttpRouter/http/readHelmetOptions.ts:102`

```typescript
// TODO(Rugvip): This is removed so that we maintained backwards compatibility
delete result['form-action'];
```

**Vấn đề:** `form-action` CSP directive bị xóa khỏi defaults, cho phép forms submit đến bất kỳ origin nào. Điều này có thể bị lợi dụng trong phishing attacks hoặc data exfiltration qua form submission.

**Khuyến nghị:**
- Set `form-action` thành `['self']` mặc định
- Document rõ cách override nếu cần

---

### SEC-012: Permission Module Allow-All

**File:** `plugins/permission-backend-module-policy-allow-all/src/module.ts`

```typescript
export const permissionModuleAllowAllPolicy = createBackendModule({
  pluginId: 'permission',
  moduleId: 'allow-all-policy',
  register(reg) {
    reg.registerInit({
      deps: { policy: policyExtensionPoint },
      async init({ policy }) {
        policy.setPolicy(new AllowAllPermissionPolicy());
      },
    });
  },
});
```

**Vấn đề:** Module `policy-allow-all` cho phép tất cả permission requests mà không kiểm tra. Mặc dù được thiết kế cho development, nó được đóng gói như một package riêng và có thể dễ dàng được sử dụng trong production.

**Tác động:** Tất cả authorization checks bị bypass, mọi user có quyền truy cập tất cả resources.

**Khuyến nghị:**
- Thêm production guard tương tự guest provider
- Log warning khi module này được sử dụng ngoài development
- Document rõ rằng module này chỉ dành cho development

---

### SEC-018: OIDC Open Redirect qua Error Flow

**File:** `plugins/auth-backend/src/service/OidcRouter.ts:303-316`

```typescript
} catch (error) {
  if (OidcError.isOidcError(error)) {
    const errorParams = new URLSearchParams();
    errorParams.append('error', error.body.error);
    errorParams.append('error_description', error.body.error_description);
    if (state) {
      errorParams.append('state', state);
    }
    const redirectUrl = new URL(redirectUri);  // ⚠️ redirectUri from user input
    redirectUrl.search = errorParams.toString();
    return res.redirect(redirectUrl.toString());
  }
}
```

**Vấn đề:** Khi xảy ra OIDC error, `redirectUri` từ request query được sử dụng trực tiếp để redirect. Mặc dù `redirect_uri` được validate qua Zod schema (`z.string().url()`), validation này chỉ kiểm tra đó là URL hợp lệ, **không kiểm tra có phải registered redirect URI hay không**.

Error flow xảy ra **trước khi** `createAuthorizationSession` validate `redirectUri` against registered URIs, nghĩa là nếu `createAuthorizationSession` throw trước validation, redirect sẽ xảy ra với URL tùy ý.

**Tác động:** Open redirect có thể dùng cho phishing attacks — kẻ tấn công redirect user đến trang giả mạo sau lỗi.

**Khuyến nghị:**
- Validate `redirectUri` against registered client URIs **trước khi** sử dụng cho error redirect
- Nếu không thể validate, redirect về một error page mặc định thay vì client URL

---

### SEC-019: Signals Backend — Health Endpoint không cần authentication nhưng không giới hạn

**File:** `plugins/signals-backend/src/plugin.ts:64-67`

```typescript
httpRouter.addAuthPolicy({
  path: '/health',
  allow: 'unauthenticated',
});
```

**Vấn đề:** Nhiều plugins expose health endpoints mà không cần authentication: `signals-backend`, `devtools-backend`, `events-backend`, `notifications-backend`. Mặc dù health endpoints thường không nhạy cảm, chúng có thể tiết lộ:
- Service đang chạy hay không
- Backend stack trace khi lỗi
- Internal service names và versions

**Khuyến nghị:**
- Cân nhắc giới hạn health endpoints chỉ cho internal monitoring systems
- Không trả về chi tiết lỗi trong health responses

---

### SEC-020: Token Claims Logging — Sensitive Information Disclosure

**File:** `plugins/auth-backend/src/identity/issueUserToken.ts:65,101-106`

```typescript
logger.info(`Issuing token for ${sub}, with entities ${ent}`);

// On oversized token:
throw new Error(
  `Failed to issue a new user token. The resulting token is excessively large, 
   with either too many ownership claims or too large custom claims. 
   The following claims were requested: '${JSON.stringify(tokenClaims)}'`,
);
```

**Vấn đề:**
1. **Line 65:** Mỗi lần issue token, entity ref và ownership entities được log ở level `info`. Trong production, điều này tạo log volume lớn và tiết lộ user identity patterns.
2. **Line 103:** Khi token quá lớn, **tất cả token claims** (bao gồm custom claims có thể chứa sensitive data) được dump vào error message.

**Tác động:** Log aggregation systems có thể lưu trữ sensitive user data vô thời hạn.

**Khuyến nghị:**
- Giảm token issue log xuống `debug` level
- Không log full token claims trong error messages — chỉ log số lượng claims và kích thước

---

## Tổng kết các khuyến nghị ưu tiên

| Ưu tiên | Hành động | Issue |
|----------|-----------|-------|
| P0 | Loại bỏ `unsafe-eval` khỏi CSP mặc định | SEC-001 |
| P0 | Parameterize tất cả SQL queries | SEC-002 |
| P1 | Block private IP ranges trong proxy target | SEC-004 |
| P1 | Thêm `httpOnly`, `sameSite` cho session cookies | SEC-005 |
| P1 | Bật rate limiting mặc định | SEC-007 |
| P1 | Thêm webhook secret validation cho Events ingress | SEC-013 |
| P1 | Loại bỏ PKCE `plain` method, bắt buộc S256 | SEC-014 |
| P2 | Command whitelist cho scaffolder | SEC-003 |
| P2 | Bật autoescape cho Nunjucks | SEC-006 |
| P2 | Bật cross-origin security headers | SEC-009 |
| P2 | Bắt buộc WebSocket authentication | SEC-015 |
| P2 | Validate redirectUri trước error redirect | SEC-018 |
| P3 | Production guard cho guest provider | SEC-010 |
| P3 | Production guard cho allow-all policy | SEC-012 |
| P3 | Set `form-action` CSP directive | SEC-011 |
| P3 | Review tất cả `res.send()` calls | SEC-008 |
| P3 | Validate lodash template files | SEC-016 |
| P3 | Dùng high-entropy secret cho OIDC clients | SEC-017 |
| P3 | Giới hạn health endpoints | SEC-019 |
| P3 | Giảm log level cho token claims | SEC-020 |

---

## Ghi chú về Mitigations hiện có

Backstage đã có nhiều biện pháp bảo mật tốt:

1. **`resolveSafeChildPath`** — Sử dụng rộng rãi để chống path traversal trong scaffolder, techdocs, app-backend
2. **`isChildPath`** — Validation cho mkdocs.yml docs_dir để chống directory traversal
3. **Isolated VM** — Nunjucks template rendering chạy trong V8 isolate sandbox (128MB memory limit)
4. **Header filtering** — Proxy backend có whitelist headers, không forward mặc định
5. **Helmet** — Security headers được cài đặt mặc định (CSP, X-Content-Type-Options, X-Frame-Options)
6. **Knex Query Builder** — Phần lớn database queries dùng Knex builder (parameterized tự động)
7. **SSRF Protection** — CimdClient có validation chống SSRF cho OIDC:
   - DNS lookup validation (`isNonPublicIp`) — block private IPs, link-local, loopback
   - `redirect: 'error'` — block redirects to prevent SSRF bypass
   - Response size cap (64KB) — prevent resource exhaustion
   - Request timeout (10s)
8. **Symlink validation** — TechDocs validate symlinks không trỏ ra ngoài input directory
9. **MkDocs YAML allowlist** — Chỉ cho phép các configuration keys được phê duyệt, sử dụng custom YAML schema (`MKDOCS_SCHEMA`)
10. **Timing-safe comparison** — Client secret verification sử dụng `crypto.timingSafeEqual()`
11. **Zod validation** — OIDC request parameters được validate qua Zod schemas
12. **Token size limit** — User tokens bị giới hạn ở 32KB để tránh abuse
13. **Key rotation** — Signing keys được tự động rotate theo `keyDurationSeconds`, expired keys được prune sau 3x duration
14. **PKCE for CIMD** — CIMD clients (public clients) bắt buộc PKCE
15. **Authorization code protections** — One-time use, 10-minute expiry, redirect URI matching
