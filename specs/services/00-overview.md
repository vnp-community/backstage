# Backstage Backend — Golang Microservices Architecture

## 1. Tổng quan

Chuyển đổi Backstage backend từ monolith TypeScript/Node.js sang kiến trúc **API Gateway + Microservices** bằng **Golang**, tuân theo mô hình **Clean Architecture** (Robert C. Martin).

### 1.1 Nguyên tắc thiết kế

- **Single Responsibility**: Mỗi service đảm nhận một bounded context duy nhất
- **Clean Architecture**: 4 layer rõ ràng — Entity → Use Case → Interface Adapter → Infrastructure
- **Dependency Rule**: Dependencies chỉ hướng vào trong (Infrastructure → Interface → Use Case → Entity)
- **Database-per-Service**: Mỗi service sở hữu database riêng, không truy cập trực tiếp DB của service khác
- **API-first**: Mọi giao tiếp giữa services qua API (gRPC internal, REST external)
- **12-Factor App**: Tuân thủ 12-factor methodology cho cloud-native deployment

### 1.2 Technology Stack

| Layer | Technology |
|---|---|
| Language | Go 1.22+ |
| HTTP Framework | [Gin](https://github.com/gin-gonic/gin) hoặc [Chi](https://github.com/go-chi/chi) |
| gRPC | google.golang.org/grpc + protobuf |
| Database | PostgreSQL 15+ |
| ORM/Query Builder | [sqlc](https://sqlc.dev/) (type-safe SQL) hoặc [GORM](https://gorm.io/) |
| Migration | [golang-migrate](https://github.com/golang-migrate/migrate) |
| Cache | Redis 7+ |
| Message Broker | NATS JetStream (primary), với adapter cho Kafka/Google PubSub |
| Service Discovery | Kubernetes DNS (native) |
| Observability | OpenTelemetry (traces + metrics + logs) |
| Logging | [zerolog](https://github.com/rs/zerolog) (structured JSON) |
| Config | [Viper](https://github.com/spf13/viper) |
| Auth | JWT (RS256), OAuth2, OIDC |
| Container | Docker + Kubernetes |
| CI/CD | GitHub Actions |
| API Docs | OpenAPI 3.0 (REST) + protobuf docs (gRPC) |
| Testing | Go standard `testing` + [testify](https://github.com/stretchr/testify) + [testcontainers-go](https://github.com/testcontainers/testcontainers-go) |

### 1.3 Kiến trúc tổng thể

```
                        ┌─────────────┐
                        │   Frontend  │
                        │  (React SPA)│
                        └──────┬──────┘
                               │ HTTPS
                        ┌──────▼──────┐
                        │ API Gateway │
                        │  (Go + Gin) │
                        │             │
                        │ • Routing   │
                        │ • Auth MW   │
                        │ • Rate Limit│
                        │ • Circuit   │
                        │   Breaker   │
                        │ • CORS      │
                        │ • Serve SPA │
                        └──────┬──────┘
                               │ gRPC (internal)
          ┌────────────────────┼────────────────────┐
          │                    │                    │
    ┌─────▼─────┐     ┌───────▼──────┐    ┌───────▼───────┐
    │   Auth    │     │   Catalog    │    │  Scaffolder   │
    │  Service  │     │   Service    │    │   Service     │
    │           │     │              │    │               │
    │ • OAuth2  │     │ • Entities   │    │ • Templates   │
    │ • OIDC    │     │ • Locations  │    │ • Task Broker │
    │ • JWT     │     │ • Ingestion  │    │ • Actions     │
    │ • Session │     │ • Processing │    │ • Workspace   │
    └─────┬─────┘     └──────┬───────┘    └───────┬───────┘
          │ PG               │ PG                 │ PG
          ▼                  ▼                    ▼
    ┌─────────┐       ┌──────────┐         ┌──────────┐
    │auth_db  │       │catalog_db│         │scaffold_db│
    └─────────┘       └──────────┘         └──────────┘

    ┌───────────┐   ┌───────────┐   ┌──────────────┐
    │  Search   │   │ TechDocs  │   │  Kubernetes  │
    │  Service  │   │  Service  │   │   Service    │
    │           │   │           │   │              │
    │ • Index   │   │ • Build   │   │ • Clusters   │
    │ • Query   │   │ • Prepare │   │ • Resources  │
    │ • Collate │   │ • Publish │   │ • Proxy      │
    └─────┬─────┘   └─────┬─────┘   └──────┬───────┘
          │ PG/ES         │ S3/GCS         │ (no local DB)
          ▼               ▼                ▼
    ┌─────────┐    ┌───────────┐    ┌────────────┐
    │search_db│    │Object Store│   │ K8s Clusters│
    └─────────┘    └───────────┘    └────────────┘

    ┌───────────┐   ┌───────────┐   ┌──────────────┐
    │Permission │   │Notification│  │   Signal     │
    │  Service  │   │  Service   │  │   Service    │
    │           │   │            │  │              │
    │ • Policy  │   │ • CRUD     │  │ • WebSocket  │
    │ • Evaluate│   │ • Process  │  │ • Pub/Sub    │
    └─────┬─────┘   └─────┬──────┘  └──────┬───────┘
          │ PG            │ PG             │ Redis
          ▼               ▼                ▼
    ┌─────────┐    ┌───────────┐    ┌──────────┐
    │perm_db  │    │notif_db   │    │  Redis   │
    └─────────┘    └───────────┘    └──────────┘

    ┌───────────┐   ┌───────────┐   ┌──────────────┐
    │  Event    │   │   Proxy   │   │  DevTools    │
    │  Service  │   │  Service  │   │   Service    │
    │           │   │           │   │              │
    │ • Bus     │   │ • Forward │   │ • Health     │
    │ • Topics  │   │ • Config  │   │ • Config     │
    │ • Webhook │   │           │   │ • Diagnostic │
    └─────┬─────┘   └───────────┘   └──────────────┘
          │ NATS
          ▼
    ┌──────────┐
    │NATS Server│
    └──────────┘

    ┌───────────┐
    │   MCP     │
    │  Service  │
    │           │
    │ • Actions │
    │ • Tools   │
    │ • Context │
    └───────────┘
```

## 2. Clean Architecture — Cấu trúc mỗi Service

```
service-name/
├── cmd/
│   └── server/
│       └── main.go                 # Entry point, wire dependencies
│
├── internal/
│   ├── entity/                     # Layer 1: Enterprise Business Rules
│   │   ├── model.go                #   Domain models (structs)
│   │   ├── errors.go               #   Domain-specific errors
│   │   └── value_objects.go        #   Value objects
│   │
│   ├── usecase/                    # Layer 2: Application Business Rules
│   │   ├── interfaces.go           #   Repository & service interfaces
│   │   ├── feature_usecase.go      #   Use case implementations
│   │   └── feature_usecase_test.go #   Unit tests (mock repositories)
│   │
│   ├── adapter/                    # Layer 3: Interface Adapters
│   │   ├── handler/                #   HTTP/gRPC request handlers
│   │   │   ├── http/
│   │   │   │   ├── router.go       #     Route definitions
│   │   │   │   ├── handler.go      #     Handler implementations
│   │   │   │   └── middleware.go   #     Route-level middleware
│   │   │   └── grpc/
│   │   │       ├── server.go       #     gRPC server setup
│   │   │       └── handler.go      #     gRPC handler implementations
│   │   ├── repository/             #   Repository implementations
│   │   │   ├── postgres/
│   │   │   │   ├── repository.go   #     PostgreSQL implementation
│   │   │   │   └── queries.sql     #     SQL queries (for sqlc)
│   │   │   └── redis/
│   │   │       └── cache.go        #     Redis cache implementation
│   │   └── presenter/              #   Response formatting
│   │       ├── json.go             #     JSON response builders
│   │       └── grpc.go             #     gRPC response builders
│   │
│   └── infrastructure/             # Layer 4: Frameworks & Drivers
│       ├── config/
│       │   └── config.go           #   Viper config loading
│       ├── database/
│       │   ├── postgres.go         #   DB connection pool
│       │   └── migrations/         #   SQL migration files
│       ├── server/
│       │   ├── http.go             #   HTTP server setup (Gin/Chi)
│       │   └── grpc.go             #   gRPC server setup
│       ├── logger/
│       │   └── logger.go           #   Zerolog setup
│       ├── telemetry/
│       │   └── otel.go             #   OpenTelemetry setup
│       └── client/                 #   External service gRPC clients
│           └── catalog_client.go
│
├── api/
│   ├── proto/                      # Protobuf definitions
│   │   └── service.proto
│   └── openapi/                    # OpenAPI specs
│       └── openapi.yaml
│
├── migrations/                     # Database migrations
│   ├── 000001_init.up.sql
│   └── 000001_init.down.sql
│
├── config/
│   ├── config.yaml                 # Default config
│   └── config.docker.yaml          # Docker/K8s config
│
├── Dockerfile
├── Makefile
├── go.mod
└── go.sum
```

## 3. Communication Patterns

### 3.1 Synchronous (Request-Reply)

| Pattern | Protocol | Khi nào dùng |
|---|---|---|
| Gateway → Service | gRPC (unary) | Mọi request từ frontend |
| Service → Service | gRPC (unary) | Query data từ service khác |
| Service → Service | gRPC (streaming) | Bulk data transfer |

### 3.2 Asynchronous (Event-Driven)

| Pattern | Transport | Khi nào dùng |
|---|---|---|
| Publish-Subscribe | NATS JetStream | Entity changes, catalog refresh |
| Event Sourcing | NATS JetStream | Audit trail, scaffolder tasks |
| Webhook | HTTP POST | External integrations (GitHub, GitLab) |

### 3.3 Event Topics

```
backstage.catalog.entity.created
backstage.catalog.entity.updated
backstage.catalog.entity.deleted
backstage.catalog.location.created
backstage.scaffolder.task.created
backstage.scaffolder.task.completed
backstage.scaffolder.task.failed
backstage.auth.user.login
backstage.auth.user.logout
backstage.notification.created
backstage.signal.broadcast
backstage.search.index.updated
```

## 4. Shared Libraries (Go Modules)

```
backstage-go/
├── pkg/
│   ├── auth/                   # JWT validation, token parsing
│   │   ├── jwt.go
│   │   ├── claims.go
│   │   └── middleware.go
│   ├── errors/                 # Standard error types
│   │   ├── errors.go           # NotFoundError, InputError, etc.
│   │   └── handler.go          # Error-to-HTTP-status mapping
│   ├── logger/                 # Shared logging config
│   │   └── logger.go
│   ├── config/                 # Config parsing utilities
│   │   └── config.go
│   ├── database/               # DB connection helpers
│   │   └── postgres.go
│   ├── middleware/              # Shared HTTP middleware
│   │   ├── cors.go
│   │   ├── recovery.go
│   │   ├── request_id.go
│   │   └── audit.go
│   ├── telemetry/              # OpenTelemetry helpers
│   │   └── otel.go
│   ├── pagination/             # Cursor-based pagination
│   │   ├── cursor.go
│   │   └── page.go
│   ├── filter/                 # Entity filter predicates
│   │   └── filter.go
│   └── health/                 # Health check utilities
│       └── health.go
└── proto/                      # Shared protobuf definitions
    ├── common/
    │   └── common.proto        # Shared message types
    ├── auth/
    │   └── auth.proto
    ├── catalog/
    │   └── catalog.proto
    ├── permission/
    │   └── permission.proto
    └── events/
        └── events.proto
```

## 5. Deployment Architecture

### 5.1 Kubernetes Deployment

```yaml
# Mỗi service là một Deployment + Service riêng
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backstage-catalog-service
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: catalog-service
        image: backstage/catalog-service:latest
        ports:
        - containerPort: 8080  # HTTP (health/metrics)
        - containerPort: 9090  # gRPC
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: catalog-db-secret
              key: url
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
        readinessProbe:
          httpGet:
            path: /readyz
            port: 8080
```

### 5.2 Docker Compose (Development)

```yaml
version: '3.8'
services:
  gateway:
    build: ./services/gateway
    ports: ["7007:7007"]
    depends_on: [auth, catalog, scaffolder]

  auth:
    build: ./services/auth-service
    ports: ["8001:8080", "9001:9090"]
    depends_on: [postgres-auth, redis]

  catalog:
    build: ./services/catalog-service
    ports: ["8002:8080", "9002:9090"]
    depends_on: [postgres-catalog, nats]

  scaffolder:
    build: ./services/scaffolder-service
    ports: ["8003:8080", "9003:9090"]
    depends_on: [postgres-scaffolder]

  search:
    build: ./services/search-service
    ports: ["8004:8080", "9004:9090"]
    depends_on: [postgres-search]

  techdocs:
    build: ./services/techdocs-service
    ports: ["8005:8080", "9005:9090"]

  kubernetes:
    build: ./services/kubernetes-service
    ports: ["8006:8080", "9006:9090"]

  permission:
    build: ./services/permission-service
    ports: ["8007:8080", "9007:9090"]
    depends_on: [postgres-permission]

  notification:
    build: ./services/notification-service
    ports: ["8008:8080", "9008:9090"]
    depends_on: [postgres-notification, redis]

  signal:
    build: ./services/signal-service
    ports: ["8009:8080", "9009:9090"]
    depends_on: [redis, nats]

  event:
    build: ./services/event-service
    ports: ["8010:8080", "9010:9090"]
    depends_on: [nats]

  proxy:
    build: ./services/proxy-service
    ports: ["8011:8080"]

  devtools:
    build: ./services/devtools-service
    ports: ["8012:8080"]

  mcp:
    build: ./services/mcp-service
    ports: ["8013:8080", "9013:9090"]

  # Infrastructure
  postgres-auth:
    image: postgres:15
    environment:
      POSTGRES_DB: backstage_auth
  postgres-catalog:
    image: postgres:15
    environment:
      POSTGRES_DB: backstage_catalog
  postgres-scaffolder:
    image: postgres:15
    environment:
      POSTGRES_DB: backstage_scaffolder
  postgres-search:
    image: postgres:15
    environment:
      POSTGRES_DB: backstage_search
  postgres-permission:
    image: postgres:15
    environment:
      POSTGRES_DB: backstage_permission
  postgres-notification:
    image: postgres:15
    environment:
      POSTGRES_DB: backstage_notification

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  nats:
    image: nats:latest
    command: ["--jetstream"]
    ports: ["4222:4222"]
```

## 6. Mapping: TypeScript Plugin → Go Service

| TypeScript Plugin | Go Service | Port HTTP | Port gRPC | Database |
|---|---|---|---|---|
| `plugin-app-backend` | gateway | 7007 | — | — |
| `plugin-auth-backend` | auth-service | 8001 | 9001 | auth_db |
| `plugin-catalog-backend` | catalog-service | 8002 | 9002 | catalog_db |
| `plugin-scaffolder-backend` | scaffolder-service | 8003 | 9003 | scaffolder_db |
| `plugin-search-backend` | search-service | 8004 | 9004 | search_db |
| `plugin-techdocs-backend` | techdocs-service | 8005 | 9005 | — |
| `plugin-kubernetes-backend` | kubernetes-service | 8006 | 9006 | — |
| `plugin-permission-backend` | permission-service | 8007 | 9007 | permission_db |
| `plugin-notifications-backend` | notification-service | 8008 | 9008 | notification_db |
| `plugin-signals-backend` | signal-service | 8009 | 9009 | — |
| `plugin-events-backend` | event-service | 8010 | 9010 | — |
| `plugin-proxy-backend` | proxy-service | 8011 | — | — |
| `plugin-devtools-backend` | devtools-service | 8012 | — | — |
| `plugin-mcp-actions-backend` | mcp-service | 8013 | 9013 | — |

## 7. Security Considerations

### 7.1 Authentication Flow

```
Client → Gateway (JWT validation) → Service (gRPC with metadata)
```

1. Gateway nhận request, validate JWT token
2. Extract user identity từ JWT claims
3. Forward identity qua gRPC metadata (`x-user-id`, `x-user-entity-ref`)
4. Mỗi service trust identity từ Gateway (mutual TLS giữa services)

### 7.2 Service-to-Service Auth

- **mTLS**: Tất cả gRPC connections giữa services dùng mutual TLS
- **Service Account Tokens**: Mỗi service có service account JWT để call services khác
- **No direct external access**: Chỉ Gateway expose ra external network

### 7.3 Security Middleware (Gateway)

```go
// Thứ tự middleware
router.Use(
    middleware.RequestID(),       // Trace ID
    middleware.Recovery(),        // Panic recovery
    middleware.CORS(corsConfig),  // CORS
    middleware.Helmet(),          // Security headers
    middleware.RateLimit(config), // Rate limiting
    middleware.Audit(logger),     // Audit logging
    middleware.Auth(jwtConfig),   // JWT validation
)
```

## 8. Monitoring & Observability

### 8.1 Metrics (Prometheus)

Mỗi service expose metrics tại `/metrics`:
- `http_request_duration_seconds` — Request latency histogram
- `http_requests_total` — Request counter by status code
- `grpc_server_handled_total` — gRPC calls counter
- `db_query_duration_seconds` — Database query latency
- Service-specific business metrics

### 8.2 Distributed Tracing (Jaeger/Tempo)

- OpenTelemetry SDK tích hợp trong mỗi service
- Trace propagation qua gRPC metadata
- Span cho mỗi: HTTP request, gRPC call, DB query, external call

### 8.3 Logging (Loki/ELK)

```json
{
  "level": "info",
  "service": "catalog-service",
  "trace_id": "abc123",
  "span_id": "def456",
  "method": "GET",
  "path": "/entities",
  "status": 200,
  "duration_ms": 45,
  "user": "user:default/admin",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 9. Chiến lược Migration

### Phase 1: Foundation (2 tuần)
- Setup shared libraries (`pkg/`)
- Setup protobuf definitions
- Setup Gateway + Auth Service
- CI/CD pipeline

### Phase 2: Core Services (4 tuần)
- Catalog Service
- Permission Service
- Search Service
- Scaffolder Service

### Phase 3: Supporting Services (3 tuần)
- TechDocs Service
- Kubernetes Service
- Notification Service
- Signal Service

### Phase 4: Auxiliary Services (2 tuần)
- Event Service
- Proxy Service
- DevTools Service
- MCP Service

### Phase 5: Integration & Testing (2 tuần)
- End-to-end testing
- Performance benchmarks
- Security audit
- Documentation
