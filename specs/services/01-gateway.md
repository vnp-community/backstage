# 01 — API Gateway Service

## 1. Tổng quan

API Gateway là entry point duy nhất cho toàn bộ backend. Nó nhận mọi request từ frontend, thực hiện authentication, routing, rate limiting, rồi forward đến các microservice tương ứng qua gRPC.

**Tương ứng TypeScript**: `plugin-app-backend` (serve SPA) + routing logic trong `@backstage/backend-defaults`

## 2. Responsibilities

- **Reverse Proxy / Routing**: Route requests đến đúng service dựa trên URL prefix
- **Authentication Middleware**: Validate JWT token, extract user identity
- **Rate Limiting**: Per-user / per-IP rate limiting
- **Circuit Breaker**: Bảo vệ downstream services khi bị overload
- **CORS**: Cross-Origin Resource Sharing policies
- **Security Headers**: Helmet-like security headers (CSP, HSTS, etc.)
- **Request/Response Transformation**: Chuyển đổi REST ↔ gRPC
- **Serve Frontend SPA**: Serve React static files
- **Health Aggregation**: Aggregate health checks từ tất cả services
- **API Versioning**: Support multiple API versions

## 3. Cấu trúc dự án

```
gateway/
├── cmd/
│   └── server/
│       └── main.go
├── internal/
│   ├── entity/
│   │   ├── route.go                 # Route configuration model
│   │   ├── upstream.go              # Upstream service model
│   │   └── user_identity.go         # User identity from JWT
│   ├── usecase/
│   │   ├── interfaces.go            # ServiceRegistry interface
│   │   ├── route_resolver.go        # Resolve route to upstream
│   │   ├── health_aggregator.go     # Aggregate health from services
│   │   └── auth_validator.go        # JWT validation logic
│   ├── adapter/
│   │   ├── handler/
│   │   │   └── http/
│   │   │       ├── router.go        # Main router setup
│   │   │       ├── proxy_handler.go # gRPC proxy handler
│   │   │       ├── spa_handler.go   # SPA file serving
│   │   │       ├── health_handler.go
│   │   │       └── middleware/
│   │   │           ├── auth.go          # JWT validation MW
│   │   │           ├── rate_limit.go    # Rate limiting MW
│   │   │           ├── circuit_breaker.go
│   │   │           ├── cors.go
│   │   │           ├── helmet.go        # Security headers
│   │   │           ├── request_id.go
│   │   │           ├── audit_log.go
│   │   │           └── recovery.go
│   │   └── grpc_client/
│   │       ├── pool.go              # gRPC connection pool
│   │       ├── auth_client.go
│   │       ├── catalog_client.go
│   │       ├── scaffolder_client.go
│   │       ├── search_client.go
│   │       ├── techdocs_client.go
│   │       ├── kubernetes_client.go
│   │       ├── permission_client.go
│   │       ├── notification_client.go
│   │       ├── signal_client.go
│   │       └── event_client.go
│   └── infrastructure/
│       ├── config/
│       │   └── config.go
│       ├── server/
│       │   └── http.go
│       └── telemetry/
│           └── otel.go
├── static/                          # Frontend SPA build output
│   └── index.html
├── config/
│   └── config.yaml
├── Dockerfile
└── go.mod
```

## 4. Routing Table

```yaml
# config/config.yaml
gateway:
  listen: ":7007"
  
  routes:
    # Auth
    - prefix: "/api/auth"
      service: "auth-service"
      grpc_target: "auth-service:9090"
      strip_prefix: false
      auth_required: false   # Auth endpoints don't require JWT

    # Catalog
    - prefix: "/api/catalog"
      service: "catalog-service"
      grpc_target: "catalog-service:9090"
      strip_prefix: true
      auth_required: true

    # Scaffolder
    - prefix: "/api/scaffolder"
      service: "scaffolder-service"
      grpc_target: "scaffolder-service:9090"
      strip_prefix: true
      auth_required: true

    # Search
    - prefix: "/api/search"
      service: "search-service"
      grpc_target: "search-service:9090"
      strip_prefix: true
      auth_required: true

    # TechDocs
    - prefix: "/api/techdocs"
      service: "techdocs-service"
      grpc_target: "techdocs-service:9090"
      strip_prefix: true
      auth_required: true

    # TechDocs static (cookie auth)
    - prefix: "/api/techdocs/static"
      service: "techdocs-service"
      grpc_target: "techdocs-service:9090"
      strip_prefix: true
      auth_required: false
      cookie_auth: true

    # Kubernetes
    - prefix: "/api/kubernetes"
      service: "kubernetes-service"
      grpc_target: "kubernetes-service:9090"
      strip_prefix: true
      auth_required: true

    # Permission
    - prefix: "/api/permission"
      service: "permission-service"
      grpc_target: "permission-service:9090"
      strip_prefix: true
      auth_required: true

    # Notifications
    - prefix: "/api/notifications"
      service: "notification-service"
      grpc_target: "notification-service:9090"
      strip_prefix: true
      auth_required: true

    # Signals (WebSocket — direct HTTP proxy, not gRPC)
    - prefix: "/api/signals"
      service: "signal-service"
      http_target: "signal-service:8080"
      strip_prefix: true
      auth_required: false
      websocket: true

    # Events
    - prefix: "/api/events"
      service: "event-service"
      grpc_target: "event-service:9090"
      strip_prefix: true
      auth_required: true

    # Proxy
    - prefix: "/api/proxy"
      service: "proxy-service"
      http_target: "proxy-service:8080"
      strip_prefix: true
      auth_required: true

    # DevTools
    - prefix: "/api/devtools"
      service: "devtools-service"
      http_target: "devtools-service:8080"
      strip_prefix: true
      auth_required: true

    # MCP
    - prefix: "/api/mcp"
      service: "mcp-service"
      grpc_target: "mcp-service:9090"
      strip_prefix: true
      auth_required: true

  rate_limit:
    requests_per_second: 100
    burst: 200

  circuit_breaker:
    max_failures: 5
    timeout: 30s
    half_open_max: 3

  cors:
    allowed_origins: ["http://localhost:3000"]
    allowed_methods: ["GET", "POST", "PUT", "DELETE", "PATCH"]
    allowed_headers: ["Authorization", "Content-Type"]
    max_age: 86400
```

## 5. Key Implementation Details

### 5.1 JWT Validation Middleware

```go
// internal/adapter/handler/http/middleware/auth.go

func AuthMiddleware(jwtConfig JWTConfig) gin.HandlerFunc {
    return func(c *gin.Context) {
        // 1. Extract token from Authorization header or cookie
        token := extractToken(c)
        if token == "" {
            c.AbortWithStatusJSON(401, ErrorResponse{
                Error: "missing_token",
                Message: "Authorization token is required",
            })
            return
        }

        // 2. Validate JWT signature and expiration
        claims, err := validateJWT(token, jwtConfig.PublicKey)
        if err != nil {
            c.AbortWithStatusJSON(401, ErrorResponse{
                Error: "invalid_token",
                Message: "Token validation failed",
            })
            return
        }

        // 3. Set user identity in context for downstream handlers
        c.Set("user_id", claims.Subject)
        c.Set("user_entity_ref", claims.EntityRef)
        c.Set("user_ownership_refs", claims.OwnershipRefs)
        c.Set("token_exp", claims.ExpiresAt)

        c.Next()
    }
}
```

### 5.2 gRPC Proxy Handler

```go
// internal/adapter/handler/http/proxy_handler.go

func (h *ProxyHandler) Handle(c *gin.Context) {
    route := c.MustGet("route").(*entity.Route)
    
    // Get gRPC connection from pool
    conn, err := h.pool.Get(route.GRPCTarget)
    if err != nil {
        c.JSON(503, ErrorResponse{Error: "service_unavailable"})
        return
    }

    // Create gRPC metadata from HTTP headers + user identity
    md := metadata.New(map[string]string{
        "x-request-id":        c.GetString("request_id"),
        "x-user-id":           c.GetString("user_id"),
        "x-user-entity-ref":   c.GetString("user_entity_ref"),
    })
    
    ctx := metadata.NewOutgoingContext(c.Request.Context(), md)

    // Forward to appropriate gRPC method based on HTTP method + path
    response, err := h.forwardRequest(ctx, conn, c.Request)
    if err != nil {
        handleGRPCError(c, err)
        return
    }

    c.JSON(response.StatusCode, response.Body)
}
```

### 5.3 Circuit Breaker

```go
// Sử dụng sony/gobreaker
breaker := gobreaker.NewCircuitBreaker(gobreaker.Settings{
    Name:        "catalog-service",
    MaxRequests: 3,              // half-open state max requests
    Interval:    60 * time.Second,
    Timeout:     30 * time.Second,
    ReadyToTrip: func(counts gobreaker.Counts) bool {
        return counts.ConsecutiveFailures > 5
    },
    OnStateChange: func(name string, from, to gobreaker.State) {
        logger.Warn().
            Str("service", name).
            Str("from", from.String()).
            Str("to", to.String()).
            Msg("Circuit breaker state changed")
    },
})
```

### 5.4 SPA Handler

```go
// internal/adapter/handler/http/spa_handler.go

func SPAHandler(staticDir string) gin.HandlerFunc {
    fs := http.FileServer(http.Dir(staticDir))
    return func(c *gin.Context) {
        // Nếu file tồn tại → serve static file
        path := filepath.Join(staticDir, c.Request.URL.Path)
        if _, err := os.Stat(path); err == nil {
            fs.ServeHTTP(c.Writer, c.Request)
            return
        }
        // Fallback → serve index.html (SPA routing)
        c.File(filepath.Join(staticDir, "index.html"))
    }
}
```

## 6. API Endpoints (Gateway Level)

| Method | Path | Target Service | Description |
|---|---|---|---|
| `*` | `/api/auth/**` | auth-service | All auth operations |
| `*` | `/api/catalog/**` | catalog-service | Catalog operations |
| `*` | `/api/scaffolder/**` | scaffolder-service | Scaffolder operations |
| `*` | `/api/search/**` | search-service | Search operations |
| `*` | `/api/techdocs/**` | techdocs-service | TechDocs operations |
| `*` | `/api/kubernetes/**` | kubernetes-service | Kubernetes operations |
| `*` | `/api/permission/**` | permission-service | Permission checks |
| `*` | `/api/notifications/**` | notification-service | Notification operations |
| `WS` | `/api/signals/**` | signal-service | WebSocket signals |
| `*` | `/api/events/**` | event-service | Event bus operations |
| `*` | `/api/proxy/**` | proxy-service | API proxy |
| `*` | `/api/devtools/**` | devtools-service | DevTools |
| `*` | `/api/mcp/**` | mcp-service | MCP actions |
| `GET` | `/healthz` | gateway | Liveness probe |
| `GET` | `/readyz` | gateway | Readiness probe |
| `GET` | `/**` | gateway (SPA) | Frontend static files |

## 7. Configuration

```yaml
# config/config.yaml
app:
  name: "backstage-gateway"
  env: "development"
  base_url: "http://localhost:7007"

server:
  port: 7007
  read_timeout: 30s
  write_timeout: 30s
  shutdown_timeout: 10s

auth:
  jwt:
    public_key_url: "http://auth-service:8080/.well-known/jwks.json"
    issuer: "http://localhost:7007/api/auth"
    audience: "backstage"

frontend:
  static_dir: "./static"
  
telemetry:
  enabled: true
  service_name: "backstage-gateway"
  otlp_endpoint: "otel-collector:4317"

logging:
  level: "info"
  format: "json"
```

## 8. Health Check Aggregation

Gateway aggregate health từ tất cả downstream services:

```go
// GET /readyz
{
  "status": "ok",
  "services": {
    "auth-service":         { "status": "ok", "latency_ms": 2 },
    "catalog-service":      { "status": "ok", "latency_ms": 5 },
    "scaffolder-service":   { "status": "ok", "latency_ms": 3 },
    "search-service":       { "status": "ok", "latency_ms": 8 },
    "techdocs-service":     { "status": "ok", "latency_ms": 4 },
    "kubernetes-service":   { "status": "degraded", "latency_ms": 150 },
    "permission-service":   { "status": "ok", "latency_ms": 2 },
    "notification-service": { "status": "ok", "latency_ms": 3 },
    "signal-service":       { "status": "ok", "latency_ms": 1 },
    "event-service":        { "status": "ok", "latency_ms": 2 }
  }
}
```
