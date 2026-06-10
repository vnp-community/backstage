# 02 — Auth Service

## 1. Tổng quan

Auth Service quản lý toàn bộ xác thực người dùng: OAuth2/OIDC flows, token issuing (JWT), session management, và multi-provider authentication.

**Tương ứng TypeScript**:
- `plugin-auth-backend` — Core auth logic, OIDC router, token factory
- `plugin-auth-backend-module-github-provider` — GitHub OAuth
- `plugin-auth-backend-module-guest-provider` — Guest/anonymous auth
- `plugin-auth-backend-module-openshift-provider` — OpenShift auth
- Các auth provider modules khác (Google, GitLab, Okta, OIDC generic, etc.)

## 2. Responsibilities

- **OAuth2/OIDC Flows**: Authorization Code, PKCE, Implicit
- **Token Management**: Issue, refresh, revoke JWT tokens
- **Session Management**: Server-side sessions với Redis/PostgreSQL
- **Multi-Provider**: Support nhiều identity providers cùng lúc
- **User Identity Resolution**: Map external identity → Backstage user entity ref
- **Ownership Resolution**: Determine user's ownership claims
- **Key Management**: Manage signing keys (RSA/EC), JWKS endpoint
- **Offline Access**: Manage refresh tokens cho offline access

## 3. Cấu trúc dự án

```
auth-service/
├── cmd/server/main.go
├── internal/
│   ├── entity/
│   │   ├── user.go                  # User identity model
│   │   ├── token.go                 # Token claims, token pair
│   │   ├── session.go               # Session model
│   │   ├── provider.go              # Auth provider config
│   │   ├── key.go                   # Signing key model
│   │   └── errors.go                # AuthError, TokenExpiredError
│   │
│   ├── usecase/
│   │   ├── interfaces.go            # Repository & provider interfaces
│   │   ├── auth_usecase.go          # Start/complete auth flow
│   │   ├── token_usecase.go         # Issue, refresh, revoke tokens
│   │   ├── session_usecase.go       # Session management
│   │   ├── key_usecase.go           # Key rotation
│   │   ├── user_info_usecase.go     # User info lookup & cache
│   │   └── oidc_usecase.go          # OIDC server implementation
│   │
│   ├── adapter/
│   │   ├── handler/
│   │   │   ├── http/
│   │   │   │   ├── router.go
│   │   │   │   ├── oauth_handler.go     # OAuth2 flow endpoints
│   │   │   │   ├── oidc_handler.go      # OIDC discovery & token
│   │   │   │   ├── jwks_handler.go      # JWKS public keys
│   │   │   │   ├── session_handler.go   # Session endpoints
│   │   │   │   └── user_info_handler.go # User info endpoint
│   │   │   └── grpc/
│   │   │       ├── server.go
│   │   │       └── auth_handler.go      # ValidateToken, GetUserInfo
│   │   ├── repository/
│   │   │   ├── postgres/
│   │   │   │   ├── user_repo.go
│   │   │   │   ├── session_repo.go
│   │   │   │   ├── key_repo.go
│   │   │   │   └── oidc_repo.go
│   │   │   └── redis/
│   │   │       └── token_cache.go       # Token blacklist, refresh cache
│   │   └── provider/                    # Auth provider implementations
│   │       ├── github.go
│   │       ├── google.go
│   │       ├── gitlab.go
│   │       ├── microsoft.go
│   │       ├── okta.go
│   │       ├── oidc_generic.go
│   │       ├── oauth2_generic.go
│   │       ├── guest.go
│   │       ├── oauth2_proxy.go
│   │       └── provider_registry.go     # Registry pattern
│   │
│   └── infrastructure/
│       ├── config/config.go
│       ├── database/
│       │   ├── postgres.go
│       │   └── migrations/
│       │       ├── 000001_create_users.up.sql
│       │       ├── 000002_create_sessions.up.sql
│       │       ├── 000003_create_keys.up.sql
│       │       └── 000004_create_oidc.up.sql
│       ├── server/
│       │   ├── http.go
│       │   └── grpc.go
│       └── crypto/
│           ├── jwt.go                   # JWT signing/validation
│           └── keys.go                  # Key generation (RS256, ES256)
│
├── api/
│   ├── proto/auth.proto
│   └── openapi/openapi.yaml
├── migrations/
├── config/config.yaml
├── Dockerfile
└── go.mod
```

## 4. Entity Models

```go
// internal/entity/user.go

type UserIdentity struct {
    UserEntityRef  string   `json:"userEntityRef"`   // "user:default/admin"
    OwnershipRefs  []string `json:"ownershipEntityRefs"` // ["user:default/admin", "group:default/team-a"]
}

type BackstageToken struct {
    Token     string    `json:"token"`
    ExpiresAt time.Time `json:"expiresAt"`
}

type TokenPair struct {
    AccessToken  BackstageToken `json:"accessToken"`
    RefreshToken string         `json:"refreshToken,omitempty"`
}

type UserInfo struct {
    Claims     map[string]interface{} `json:"claims"`
    OwnerRefs  []string               `json:"ownershipEntityRefs"`
}
```

```go
// internal/entity/provider.go

type AuthProvider struct {
    ID          string                 `json:"id"`       // "github", "google", etc.
    DisplayName string                `json:"displayName"`
    Type        ProviderType          `json:"type"`      // oauth2, oidc, saml
    Config      map[string]interface{} `json:"config"`
}

type ProviderType string

const (
    ProviderTypeOAuth2 ProviderType = "oauth2"
    ProviderTypeOIDC   ProviderType = "oidc"
    ProviderTypeSAML   ProviderType = "saml"
    ProviderTypeGuest  ProviderType = "guest"
)
```

```go
// internal/entity/key.go

type SigningKey struct {
    ID          string    `json:"kid"`
    Algorithm   string    `json:"alg"`     // RS256, ES256
    PublicKey   []byte    `json:"publicKey"`
    PrivateKey  []byte    `json:"-"`       // never serialized
    CreatedAt   time.Time `json:"createdAt"`
    ExpiresAt   time.Time `json:"expiresAt"`
}
```

## 5. Use Case Interfaces

```go
// internal/usecase/interfaces.go

type UserRepository interface {
    FindByEntityRef(ctx context.Context, entityRef string) (*entity.UserInfo, error)
    UpsertUserInfo(ctx context.Context, entityRef string, info *entity.UserInfo) error
}

type SessionRepository interface {
    Create(ctx context.Context, session *entity.Session) error
    FindByID(ctx context.Context, sessionID string) (*entity.Session, error)
    Delete(ctx context.Context, sessionID string) error
    DeleteByUser(ctx context.Context, userEntityRef string) error
}

type KeyRepository interface {
    GetActiveKeys(ctx context.Context) ([]*entity.SigningKey, error)
    Store(ctx context.Context, key *entity.SigningKey) error
    GetByID(ctx context.Context, kid string) (*entity.SigningKey, error)
}

type TokenCache interface {
    Blacklist(ctx context.Context, tokenID string, exp time.Duration) error
    IsBlacklisted(ctx context.Context, tokenID string) (bool, error)
    StoreRefreshToken(ctx context.Context, token string, userRef string, exp time.Duration) error
    GetRefreshToken(ctx context.Context, token string) (string, error)
}

// Auth provider interface — mỗi provider implement interface này
type AuthProviderHandler interface {
    // Start initiates the auth flow (redirect to provider)
    Start(ctx context.Context, req *AuthStartRequest) (*AuthStartResponse, error)
    // Handler handles the callback from the provider
    Handler(ctx context.Context, req *AuthCallbackRequest) (*AuthCallbackResponse, error)
    // Refresh refreshes an existing session
    Refresh(ctx context.Context, req *AuthRefreshRequest) (*AuthRefreshResponse, error)
    // Logout cleans up provider-specific session data
    Logout(ctx context.Context, req *AuthLogoutRequest) error
}
```

## 6. API Endpoints

### 6.1 REST API (External — qua Gateway)

| Method | Path | Description |
|---|---|---|
| `GET` | `/:provider/start` | Bắt đầu OAuth flow → redirect đến provider |
| `GET` | `/:provider/handler/frame` | Callback handler (popup mode) |
| `POST` | `/:provider/handler/frame` | Callback handler (POST mode) |
| `POST` | `/:provider/refresh` | Refresh session/token |
| `POST` | `/:provider/logout` | Logout khỏi provider |
| `GET` | `/.well-known/jwks.json` | JWKS public keys endpoint |
| `GET` | `/.well-known/openid-configuration` | OIDC discovery document |
| `POST` | `/oauth2/token` | OIDC token endpoint |
| `POST` | `/oauth2/revoke` | OIDC token revocation |
| `GET` | `/oauth2/authorize` | OIDC authorization endpoint |
| `GET` | `/oauth2/userinfo` | OIDC userinfo endpoint |

### 6.2 gRPC API (Internal — service-to-service)

```protobuf
// api/proto/auth.proto

syntax = "proto3";
package backstage.auth.v1;

service AuthService {
    // Validate a JWT token and return user identity
    rpc ValidateToken(ValidateTokenRequest) returns (ValidateTokenResponse);
    
    // Get user info by entity ref
    rpc GetUserInfo(GetUserInfoRequest) returns (GetUserInfoResponse);
    
    // Issue a service-to-service token
    rpc IssueServiceToken(IssueServiceTokenRequest) returns (IssueServiceTokenResponse);
    
    // Get JWKS for token validation
    rpc GetJWKS(GetJWKSRequest) returns (GetJWKSResponse);
}

message ValidateTokenRequest {
    string token = 1;
}

message ValidateTokenResponse {
    string user_entity_ref = 1;
    repeated string ownership_refs = 2;
    int64 expires_at = 3;  // Unix timestamp
}

message GetUserInfoRequest {
    string user_entity_ref = 1;
}

message GetUserInfoResponse {
    string user_entity_ref = 1;
    repeated string ownership_refs = 2;
    map<string, string> claims = 3;
}

message IssueServiceTokenRequest {
    string service_name = 1;
    repeated string target_services = 2;
}

message IssueServiceTokenResponse {
    string token = 1;
    int64 expires_at = 2;
}
```

## 7. Database Schema

```sql
-- migrations/000001_create_users.up.sql

CREATE TABLE user_info (
    user_entity_ref VARCHAR(255) PRIMARY KEY,
    ownership_refs  JSONB NOT NULL DEFAULT '[]',
    claims          JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_info_updated_at ON user_info(updated_at);
```

```sql
-- migrations/000002_create_sessions.up.sql

CREATE TABLE auth_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_entity_ref VARCHAR(255) NOT NULL,
    provider_id     VARCHAR(100) NOT NULL,
    provider_data   JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_sessions_user ON auth_sessions(user_entity_ref);
CREATE INDEX idx_sessions_expires ON auth_sessions(expires_at);

-- Express-session compatible table
CREATE TABLE sessions (
    sid     VARCHAR(255) PRIMARY KEY NOT NULL,
    sess    JSONB NOT NULL,
    expired TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_sessions_expired ON sessions(expired);
```

```sql
-- migrations/000003_create_keys.up.sql

CREATE TABLE signing_keys (
    kid         VARCHAR(255) PRIMARY KEY,
    algorithm   VARCHAR(10) NOT NULL DEFAULT 'RS256',
    public_key  BYTEA NOT NULL,
    private_key BYTEA NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_keys_expires ON signing_keys(expires_at);
```

```sql
-- migrations/000004_create_oidc.up.sql

CREATE TABLE oidc_clients (
    client_id     VARCHAR(255) PRIMARY KEY,
    client_secret VARCHAR(255) NOT NULL,
    redirect_uris JSONB NOT NULL DEFAULT '[]',
    grant_types   JSONB NOT NULL DEFAULT '["authorization_code"]',
    scopes        JSONB NOT NULL DEFAULT '["openid"]',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE oidc_authorization_codes (
    code            VARCHAR(255) PRIMARY KEY,
    client_id       VARCHAR(255) NOT NULL REFERENCES oidc_clients(client_id),
    user_entity_ref VARCHAR(255) NOT NULL,
    redirect_uri    VARCHAR(1024) NOT NULL,
    scopes          JSONB NOT NULL DEFAULT '[]',
    code_challenge  VARCHAR(255),
    code_challenge_method VARCHAR(10),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL
);

CREATE TABLE oidc_refresh_tokens (
    token           VARCHAR(255) PRIMARY KEY,
    client_id       VARCHAR(255) NOT NULL REFERENCES oidc_clients(client_id),
    user_entity_ref VARCHAR(255) NOT NULL,
    scopes          JSONB NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL
);
```

## 8. Provider Architecture (Plugin Pattern)

```go
// internal/adapter/provider/provider_registry.go

type ProviderRegistry struct {
    providers map[string]AuthProviderHandler
}

func NewProviderRegistry() *ProviderRegistry {
    return &ProviderRegistry{
        providers: make(map[string]AuthProviderHandler),
    }
}

func (r *ProviderRegistry) Register(name string, handler AuthProviderHandler) {
    r.providers[name] = handler
}

func (r *ProviderRegistry) Get(name string) (AuthProviderHandler, error) {
    h, ok := r.providers[name]
    if !ok {
        return nil, fmt.Errorf("unknown auth provider '%s'", name)
    }
    return h, nil
}

// Registration at startup:
func RegisterProviders(registry *ProviderRegistry, config *Config) {
    if cfg := config.Providers.GitHub; cfg != nil {
        registry.Register("github", NewGitHubProvider(cfg))
    }
    if cfg := config.Providers.Google; cfg != nil {
        registry.Register("google", NewGoogleProvider(cfg))
    }
    if cfg := config.Providers.Guest; cfg != nil {
        registry.Register("guest", NewGuestProvider(cfg))
    }
    // ... more providers
}
```

## 9. Configuration

```yaml
auth:
  session:
    secret: "${AUTH_SESSION_SECRET}"
  
  identity_token:
    algorithm: "RS256"
    expiration: "1h"
    key_duration: "24h"
    omit_ownership_claim: true

  providers:
    github:
      client_id: "${GITHUB_CLIENT_ID}"
      client_secret: "${GITHUB_CLIENT_SECRET}"
      sign_in:
        resolvers:
          - resolver: "usernameMatchingUserEntityName"
    
    google:
      client_id: "${GOOGLE_CLIENT_ID}"
      client_secret: "${GOOGLE_CLIENT_SECRET}"
      sign_in:
        resolvers:
          - resolver: "emailMatchingUserEntityProfileEmail"
    
    guest:
      dangerouslyAllowOutsideDevelopment: false

  oidc:
    enabled: true
    issuer: "http://localhost:7007/api/auth"

database:
  host: "postgres-auth"
  port: 5432
  name: "backstage_auth"
  user: "${DB_USER}"
  password: "${DB_PASSWORD}"
  max_open_conns: 20
  max_idle_conns: 5

redis:
  addr: "redis:6379"
  db: 0
```

## 10. Security Considerations

- **Token Signing**: Sử dụng RS256 (asymmetric) — private key chỉ ở Auth Service, public key chia sẻ qua JWKS
- **Session Storage**: Server-side sessions trong PostgreSQL (không cookie-based)
- **PKCE**: Bắt buộc cho tất cả OAuth2 authorization code flows
- **Token Rotation**: Signing keys tự động rotate theo `key_duration`
- **Refresh Token Rotation**: Mỗi lần refresh sẽ issue refresh token mới, invalidate cũ
- **Rate Limiting**: Rate limit trên login attempts per user/IP
- **SSRF Protection**: Validate tất cả redirect URIs, không cho phép internal IPs
