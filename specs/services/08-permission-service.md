# 08 — Permission Service

## 1. Tổng quan

Permission Service là authorization engine cho Backstage — evaluate quyền truy cập dựa trên configurable policies, support resource-based và basic permissions.

**Tương ứng TypeScript**:
- `plugin-permission-backend` — Core permission evaluation
- `plugin-permission-backend-module-allow-all-policy` — Default allow-all policy

## 2. Responsibilities

- **Permission Evaluation**: Evaluate permission requests against policies
- **Policy Management**: Load và manage permission policies
- **Conditional Decisions**: Support conditional permissions (resource-based)
- **Batch Evaluation**: Evaluate multiple permissions in one request
- **Permission Discovery**: Expose available permissions for UI

## 3. Cấu trúc dự án

```
permission-service/
├── cmd/server/main.go
├── internal/
│   ├── entity/
│   │   ├── permission.go            # Permission definition
│   │   ├── policy.go                # Policy model
│   │   ├── decision.go              # Authorization decision
│   │   └── errors.go
│   │
│   ├── usecase/
│   │   ├── interfaces.go
│   │   ├── evaluate_usecase.go      # Evaluate permissions
│   │   ├── policy_usecase.go        # Policy management
│   │   └── discovery_usecase.go     # Permission discovery
│   │
│   ├── adapter/
│   │   ├── handler/
│   │   │   ├── http/
│   │   │   │   ├── router.go
│   │   │   │   ├── authorize_handler.go
│   │   │   │   └── health_handler.go
│   │   │   └── grpc/
│   │   │       ├── server.go
│   │   │       └── permission_handler.go
│   │   ├── policy/
│   │   │   ├── policy_interface.go
│   │   │   ├── allow_all_policy.go
│   │   │   ├── rbac_policy.go        # Role-based policy
│   │   │   └── opa_policy.go         # Open Policy Agent
│   │   └── repository/
│   │       └── postgres/
│   │           └── policy_repo.go
│   │
│   └── infrastructure/
│       ├── config/config.go
│       ├── database/
│       │   ├── postgres.go
│       │   └── migrations/
│       │       └── 000001_create_policies.up.sql
│       └── server/
│           ├── http.go
│           └── grpc.go
│
├── api/
│   ├── proto/permission.proto
│   └── openapi/openapi.yaml
├── config/config.yaml
├── Dockerfile
└── go.mod
```

## 4. Entity Models

```go
// internal/entity/permission.go

type AuthorizationDecision string

const (
    DecisionAllow      AuthorizationDecision = "ALLOW"
    DecisionDeny       AuthorizationDecision = "DENY"
    DecisionConditional AuthorizationDecision = "CONDITIONAL"
)

type PermissionRequest struct {
    Permission Permission    `json:"permission"`
    ResourceRef string       `json:"resourceRef,omitempty"`
}

type Permission struct {
    Name       string   `json:"name"`
    Type       string   `json:"type"`   // "basic", "resource"
    ResourceType string `json:"resourceType,omitempty"`
    Attributes map[string]string `json:"attributes,omitempty"`
}

type AuthorizeRequest struct {
    Items []PermissionRequestItem `json:"items"`
}

type PermissionRequestItem struct {
    ID          string     `json:"id"`
    Permission  Permission `json:"permission"`
    ResourceRef string     `json:"resourceRef,omitempty"`
}

type AuthorizeResponse struct {
    Items []AuthorizeResponseItem `json:"items"`
}

type AuthorizeResponseItem struct {
    ID       string                `json:"id"`
    Result   AuthorizationDecision `json:"result"`
    Conditions *PermissionConditions `json:"conditions,omitempty"`
}

type PermissionConditions struct {
    Rule   string         `json:"rule"`
    Params map[string]any `json:"params,omitempty"`
    AllOf  []PermissionConditions `json:"allOf,omitempty"`
    AnyOf  []PermissionConditions `json:"anyOf,omitempty"`
    Not    *PermissionConditions  `json:"not,omitempty"`
}
```

## 5. Use Case Interfaces

```go
type PermissionPolicy interface {
    Handle(ctx context.Context, request PermissionRequest, user UserIdentity) (AuthorizationDecision, error)
}

type UserIdentity struct {
    UserEntityRef string
    OwnershipRefs []string
}
```

## 6. API Endpoints

### 6.1 REST API

| Method | Path | Description |
|---|---|---|
| `POST` | `/authorize` | Evaluate permission requests |
| `GET` | `/health` | Health check |

### 6.2 gRPC API

```protobuf
syntax = "proto3";
package backstage.permission.v1;

service PermissionService {
    rpc Authorize(AuthorizeRequest) returns (AuthorizeResponse);
    rpc ListPermissions(ListPermissionsRequest) returns (ListPermissionsResponse);
}
```

## 7. Configuration

```yaml
permission:
  enabled: true
  policy: "allow-all"    # "allow-all", "rbac", "opa"
  
  rbac:
    admin_refs:
      - "user:default/admin"
    policies:
      - effect: "allow"
        permission: "catalog.entity.read"
        roles: ["*"]
      - effect: "allow"
        permission: "catalog.entity.create"
        roles: ["admin", "developer"]
  
  opa:
    url: "http://opa-server:8181"
    policy_path: "/v1/data/backstage/authz"
```
