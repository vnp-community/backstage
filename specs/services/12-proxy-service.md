# 12 — Proxy Service

## 1. Tổng quan

Proxy Service forward API requests đến external services — cho phép frontend truy cập third-party APIs thông qua Backstage backend (tránh CORS issues, thêm auth headers).

**Tương ứng TypeScript**:
- `plugin-proxy-backend` — Configurable reverse proxy with header management

## 2. Responsibilities

- **API Forwarding**: Proxy HTTP requests đến configured endpoints
- **Header Management**: Add/remove/modify headers (auth tokens, API keys)
- **Path Rewriting**: Rewrite request paths
- **Allow/Deny Lists**: Control allowed headers
- **Change Origin**: Change Host header cho target compatibility

## 3. Cấu trúc dự án

```
proxy-service/
├── cmd/server/main.go
├── internal/
│   ├── entity/
│   │   ├── endpoint.go              # Proxy endpoint config
│   │   └── errors.go
│   │
│   ├── usecase/
│   │   ├── interfaces.go
│   │   └── proxy_usecase.go         # Forward requests
│   │
│   ├── adapter/
│   │   └── handler/
│   │       └── http/
│   │           ├── router.go
│   │           └── proxy_handler.go  # Reverse proxy handler
│   │
│   └── infrastructure/
│       ├── config/config.go
│       └── server/http.go
│
├── config/config.yaml
├── Dockerfile
└── go.mod
```

## 4. Entity Models

```go
type ProxyEndpoint struct {
    Target          string            `json:"target"`           // Target URL
    PathRewrite     map[string]string `json:"pathRewrite,omitempty"`
    ChangeOrigin    bool              `json:"changeOrigin"`
    Headers         map[string]string `json:"headers,omitempty"` // Additional headers
    AllowedHeaders  []string          `json:"allowedHeaders,omitempty"`
    AllowedMethods  []string          `json:"allowedMethods,omitempty"`
    Credentials     string            `json:"credentials,omitempty"` // "require", "forward", "dangerously-allow-unauthenticated"
}
```

## 5. API Endpoints

| Method | Path | Description |
|---|---|---|
| `*` | `/:endpointName/**` | Forward to configured endpoint |
| `GET` | `/health` | Health check |

## 6. Configuration

```yaml
proxy:
  endpoints:
    "/circleci/api":
      target: "https://circleci.com/api/v1.1"
      headers:
        Circle-Token: "${CIRCLECI_TOKEN}"
      change_origin: true
    
    "/jenkins/api":
      target: "http://jenkins.internal:8080"
      credentials: "forward"
      allowed_headers: ["Authorization"]
    
    "/argocd/api":
      target: "https://argocd.internal"
      headers:
        Cookie: "argocd.token=${ARGOCD_TOKEN}"
      change_origin: true
      path_rewrite:
        "^/api/proxy/argocd/api": "/api/v1"
```

## 7. Security

- **Header Whitelist**: Chỉ forward headers trong allowedHeaders
- **No credentials by default**: Không forward auth headers trừ khi configured
- **Internal IPs blocked**: Không cho proxy đến internal network IPs (SSRF protection)
- **URL validation**: Validate target URLs, block `file://`, `data://`, etc.
