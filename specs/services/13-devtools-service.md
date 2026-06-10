# 13 — DevTools Service

## 1. Tổng quan

DevTools Service cung cấp developer tools cho Backstage admins — inspect configuration, xem thông tin hệ thống, quản lý packages, diagnostics.

**Tương ứng TypeScript**:
- `plugin-devtools-backend` — Config info, external dependencies, package info

## 2. Responsibilities

- **Config Inspection**: Xem (sanitized) app configuration
- **System Info**: Go runtime info, service versions, build info
- **External Dependencies**: Check external service connectivity
- **Package Info**: List loaded plugins/modules
- **Health Diagnostics**: Detailed health diagnostics

## 3. Cấu trúc dự án

```
devtools-service/
├── cmd/server/main.go
├── internal/
│   ├── entity/
│   │   ├── config_info.go
│   │   ├── system_info.go
│   │   └── dependency.go
│   │
│   ├── usecase/
│   │   ├── interfaces.go
│   │   ├── config_usecase.go
│   │   ├── system_usecase.go
│   │   └── dependency_usecase.go
│   │
│   ├── adapter/
│   │   └── handler/
│   │       └── http/
│   │           ├── router.go
│   │           ├── config_handler.go
│   │           ├── system_handler.go
│   │           └── dependency_handler.go
│   │
│   └── infrastructure/
│       ├── config/config.go
│       └── server/http.go
│
├── config/config.yaml
├── Dockerfile
└── go.mod
```

## 4. API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/config` | Get sanitized configuration |
| `GET` | `/info` | Get system/runtime info |
| `GET` | `/dependencies` | List & check external dependencies |
| `GET` | `/health` | Health check |

## 5. Responses

```go
// GET /info
type SystemInfo struct {
    GoVersion     string    `json:"goVersion"`
    GOOS          string    `json:"goos"`
    GOARCH        string    `json:"goarch"`
    NumCPU        int       `json:"numCPU"`
    NumGoroutine  int       `json:"numGoroutine"`
    MemAlloc      uint64    `json:"memAllocBytes"`
    BuildVersion  string    `json:"buildVersion"`
    BuildCommit   string    `json:"buildCommit"`
    BuildDate     string    `json:"buildDate"`
    Uptime        string    `json:"uptime"`
    Services      []ServiceInfo `json:"services"`
}

// GET /dependencies
type DependencyCheck struct {
    Name    string `json:"name"`     // "postgres-catalog", "redis", "nats"
    Type    string `json:"type"`     // "database", "cache", "message-broker"
    Status  string `json:"status"`   // "ok", "error", "degraded"
    Latency string `json:"latency"`
    Error   string `json:"error,omitempty"`
}
```
