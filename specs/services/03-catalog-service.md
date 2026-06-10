# 03 — Catalog Service

## 1. Tổng quan

Catalog Service là trái tim của Backstage — quản lý Software Catalog chứa tất cả entities (Components, APIs, Systems, Domains, Groups, Users, Resources, Locations). Service này xử lý ingestion pipeline, entity processing, stitching, và cung cấp API query entities.

**Tương ứng TypeScript**:
- `plugin-catalog-backend` — Core catalog logic, entity CRUD, location management
- `plugin-catalog-backend-module-unprocessed` — Unprocessed entities management
- `plugin-catalog-backend-module-ai-model` — AI Model entity kind
- `plugin-catalog-backend-module-scaffolder-entity-model` — Template entity kind
- `plugin-catalog-backend-module-logs` — Catalog processing logs
- `plugin-catalog-backend-module-backstage-openapi` — OpenAPI spec entities
- Các catalog modules khác (GitHub, GitLab, Bitbucket, LDAP, etc.)

## 2. Responsibilities

- **Entity Management**: CRUD operations trên software catalog entities
- **Location Management**: Register, update, delete catalog locations (git repos, URLs)
- **Ingestion Pipeline**: Fetch, process, validate entities từ external sources
- **Entity Processing**: Transform raw entities qua processor chain
- **Stitching**: Assemble final entities từ multiple sources
- **Entity Query**: Filter, search, paginate entities
- **Entity Facets**: Aggregate entity metadata facets
- **Entity Ancestry**: Track entity provenance (origin → processed)
- **Batch Operations**: Bulk entity retrieval by refs
- **Validation**: Validate entity envelope và content
- **Location Analysis**: Analyze potential catalog locations

## 3. Cấu trúc dự án

```
catalog-service/
├── cmd/server/main.go
├── internal/
│   ├── entity/
│   │   ├── catalog_entity.go        # Entity model (kind, metadata, spec, relations)
│   │   ├── location.go              # Location model
│   │   ├── entity_ref.go            # EntityRef value object
│   │   ├── filter.go                # Filter predicate types
│   │   ├── cursor.go                # Pagination cursor
│   │   ├── facet.go                 # Facet result type
│   │   ├── ancestry.go              # Entity ancestry model
│   │   ├── processing.go            # Processing state model
│   │   └── errors.go
│   │
│   ├── usecase/
│   │   ├── interfaces.go
│   │   ├── entity_usecase.go        # CRUD entities
│   │   ├── query_usecase.go         # Query/filter entities
│   │   ├── batch_usecase.go         # Batch entity retrieval
│   │   ├── facet_usecase.go         # Entity facets
│   │   ├── ancestry_usecase.go      # Entity ancestry
│   │   ├── location_usecase.go      # Location management
│   │   ├── refresh_usecase.go       # Entity refresh
│   │   ├── validation_usecase.go    # Entity validation
│   │   ├── analysis_usecase.go      # Location analysis
│   │   └── ingestion/
│   │       ├── ingestion_usecase.go # Ingestion pipeline orchestrator
│   │       ├── processor.go         # Entity processor interface & chain
│   │       └── stitcher.go          # Entity stitching logic
│   │
│   ├── adapter/
│   │   ├── handler/
│   │   │   ├── http/
│   │   │   │   ├── router.go
│   │   │   │   ├── entity_handler.go
│   │   │   │   ├── query_handler.go
│   │   │   │   ├── location_handler.go
│   │   │   │   ├── facet_handler.go
│   │   │   │   ├── validation_handler.go
│   │   │   │   └── refresh_handler.go
│   │   │   └── grpc/
│   │   │       ├── server.go
│   │   │       └── catalog_handler.go
│   │   ├── repository/
│   │   │   └── postgres/
│   │   │       ├── entity_repo.go       # Entity storage
│   │   │       ├── location_repo.go     # Location storage
│   │   │       ├── processing_repo.go   # Processing state
│   │   │       ├── search_repo.go       # Full-text entity search
│   │   │       ├── relations_repo.go    # Entity relations
│   │   │       └── refresh_state_repo.go
│   │   ├── presenter/
│   │   │   ├── entity_presenter.go
│   │   │   └── location_presenter.go
│   │   └── provider/                    # Entity providers (modules)
│   │       ├── provider_registry.go
│   │       ├── github/
│   │       │   ├── github_provider.go
│   │       │   └── github_org_provider.go
│   │       ├── gitlab/
│   │       │   └── gitlab_provider.go
│   │       ├── url/
│   │       │   └── url_provider.go
│   │       └── file/
│   │           └── file_provider.go
│   │
│   └── infrastructure/
│       ├── config/config.go
│       ├── database/
│       │   ├── postgres.go
│       │   └── migrations/
│       │       ├── 000001_create_entities.up.sql
│       │       ├── 000002_create_locations.up.sql
│       │       ├── 000003_create_relations.up.sql
│       │       ├── 000004_create_search.up.sql
│       │       ├── 000005_create_refresh_state.up.sql
│       │       └── 000006_create_processing_log.up.sql
│       ├── server/
│       │   ├── http.go
│       │   └── grpc.go
│       └── client/
│           ├── permission_client.go     # Check entity permissions
│           └── auth_client.go           # Validate credentials
│
├── api/
│   ├── proto/catalog.proto
│   └── openapi/openapi.yaml
├── migrations/
├── config/config.yaml
├── Dockerfile
└── go.mod
```

## 4. Entity Models

```go
// internal/entity/catalog_entity.go

type Entity struct {
    APIVersion string            `json:"apiVersion"` // "backstage.io/v1alpha1"
    Kind       string            `json:"kind"`       // Component, API, System, etc.
    Metadata   EntityMetadata    `json:"metadata"`
    Spec       map[string]any    `json:"spec,omitempty"`
    Relations  []EntityRelation  `json:"relations,omitempty"`
    Status     *EntityStatus     `json:"status,omitempty"`
}

type EntityMetadata struct {
    UID         string            `json:"uid"`
    Etag        string            `json:"etag"`
    Name        string            `json:"name"`
    Namespace   string            `json:"namespace"` // default: "default"
    Title       string            `json:"title,omitempty"`
    Description string            `json:"description,omitempty"`
    Labels      map[string]string `json:"labels,omitempty"`
    Annotations map[string]string `json:"annotations,omitempty"`
    Tags        []string          `json:"tags,omitempty"`
    Links       []EntityLink      `json:"links,omitempty"`
}

type EntityRelation struct {
    Type      string    `json:"type"`      // "ownedBy", "partOf", "dependsOn"
    TargetRef string    `json:"targetRef"` // "group:default/team-a"
}

type EntityLink struct {
    URL   string `json:"url"`
    Title string `json:"title,omitempty"`
    Icon  string `json:"icon,omitempty"`
    Type  string `json:"type,omitempty"`
}

type EntityStatus struct {
    Items []EntityStatusItem `json:"items,omitempty"`
}

type EntityStatusItem struct {
    Type    string `json:"type"`
    Level   string `json:"level"` // "info", "warning", "error"
    Message string `json:"message"`
    Error   *struct {
        Name    string `json:"name"`
        Message string `json:"message"`
    } `json:"error,omitempty"`
}
```

```go
// internal/entity/location.go

type Location struct {
    ID        string `json:"id"`
    Type      string `json:"type"`   // "url", "file"
    Target    string `json:"target"` // URL or file path
}

type LocationInput struct {
    Type   string `json:"type" binding:"required"`
    Target string `json:"target" binding:"required"`
}
```

```go
// internal/entity/filter.go

type EntityFilter struct {
    AllOf []EntityFilterCriteria `json:"allOf,omitempty"`
    AnyOf []EntityFilterCriteria `json:"anyOf,omitempty"`
    Not   *EntityFilter          `json:"not,omitempty"`
}

type EntityFilterCriteria struct {
    Key    string   `json:"key"`     // "kind", "metadata.name", "spec.type"
    Values []string `json:"values"`  // filter values
}

type EntityOrder struct {
    Field string `json:"field"` // "metadata.name", "metadata.namespace"
    Order string `json:"order"` // "asc", "desc"
}

type QueryEntitiesRequest struct {
    Filter     *EntityFilter  `json:"filter,omitempty"`
    Fields     []string       `json:"fields,omitempty"`     // field projection
    OrderFields []EntityOrder `json:"orderFields,omitempty"`
    Limit      int            `json:"limit,omitempty"`
    Cursor     string         `json:"cursor,omitempty"`     // opaque pagination cursor
    FullTextFilter *FullTextFilter `json:"fullTextFilter,omitempty"`
}

type FullTextFilter struct {
    Term   string   `json:"term"`
    Fields []string `json:"fields,omitempty"` // search trong specific fields
}

type QueryEntitiesResponse struct {
    Items      []Entity `json:"items"`
    TotalItems int      `json:"totalItems"`
    PageInfo   PageInfo `json:"pageInfo"`
}

type PageInfo struct {
    NextCursor string `json:"nextCursor,omitempty"`
    PrevCursor string `json:"prevCursor,omitempty"`
}
```

## 5. Use Case Interfaces

```go
// internal/usecase/interfaces.go

type EntityRepository interface {
    // Query
    GetByUID(ctx context.Context, uid string) (*entity.Entity, error)
    GetByRef(ctx context.Context, kind, namespace, name string) (*entity.Entity, error)
    GetByRefs(ctx context.Context, refs []string, filter *entity.EntityFilter, fields []string) ([]entity.Entity, error)
    QueryEntities(ctx context.Context, req *entity.QueryEntitiesRequest) (*entity.QueryEntitiesResponse, error)
    ListEntities(ctx context.Context, filter *entity.EntityFilter, fields []string, order []entity.EntityOrder) ([]entity.Entity, error)
    
    // Mutate
    InsertEntity(ctx context.Context, e *entity.Entity) error
    UpdateEntity(ctx context.Context, e *entity.Entity) error
    DeleteEntityByUID(ctx context.Context, uid string) error
    
    // Facets
    GetFacets(ctx context.Context, filter *entity.EntityFilter, facets []string) ([]entity.FacetResult, error)
    
    // Ancestry
    GetAncestry(ctx context.Context, entityRef string) (*entity.AncestryResponse, error)
}

type LocationRepository interface {
    Create(ctx context.Context, loc *entity.LocationInput) (*entity.Location, error)
    List(ctx context.Context) ([]entity.Location, error)
    Query(ctx context.Context, limit int, afterID string, query string) ([]entity.Location, int, error)
    GetByID(ctx context.Context, id string) (*entity.Location, error)
    Update(ctx context.Context, id string, loc *entity.LocationInput) (*entity.Location, error)
    Delete(ctx context.Context, id string) error
    GetByEntity(ctx context.Context, kind, namespace, name string) (*entity.Location, error)
}

type RefreshStateRepository interface {
    SetRefreshNeeded(ctx context.Context, entityRef string) error
    GetPendingRefreshes(ctx context.Context, limit int) ([]string, error)
}

type ProcessingRepository interface {
    GetUnprocessed(ctx context.Context, limit int) ([]entity.Entity, error)
    SetProcessed(ctx context.Context, uid string, result *ProcessingResult) error
    LogProcessing(ctx context.Context, uid string, log *ProcessingLog) error
}

type PermissionChecker interface {
    CheckEntityPermission(ctx context.Context, entityRef string, permission string, credentials Credentials) error
}

type EventPublisher interface {
    PublishEntityCreated(ctx context.Context, e *entity.Entity) error
    PublishEntityUpdated(ctx context.Context, e *entity.Entity) error
    PublishEntityDeleted(ctx context.Context, entityRef string) error
    PublishLocationCreated(ctx context.Context, loc *entity.Location) error
}
```

## 6. API Endpoints

### 6.1 REST API

| Method | Path | Description |
|---|---|---|
| `GET` | `/entities` | List all entities (streaming JSON) |
| `GET` | `/entities/by-query` | Query entities with filter/sort/pagination |
| `POST` | `/entities/by-query` | Query entities (body params) |
| `GET` | `/entities/by-uid/:uid` | Get entity by UID |
| `DELETE` | `/entities/by-uid/:uid` | Delete entity by UID |
| `GET` | `/entities/by-name/:kind/:namespace/:name` | Get entity by name |
| `GET` | `/entities/by-name/:kind/:namespace/:name/ancestry` | Get entity ancestry |
| `POST` | `/entities/by-refs` | Batch get entities by refs |
| `GET` | `/entity-facets` | Get entity facets |
| `POST` | `/entity-facets` | Get entity facets (body params) |
| `POST` | `/locations` | Register new location |
| `GET` | `/locations` | List all locations |
| `POST` | `/locations/by-query` | Query locations |
| `GET` | `/locations/:id` | Get location by ID |
| `PUT` | `/locations/:id` | Update location |
| `DELETE` | `/locations/:id` | Delete location |
| `GET` | `/locations/by-entity/:kind/:ns/:name` | Get location by entity |
| `POST` | `/analyze-location` | Analyze a potential location |
| `POST` | `/validate-entity` | Validate entity content |
| `POST` | `/refresh` | Trigger entity refresh |

### 6.2 gRPC API

```protobuf
// api/proto/catalog.proto

syntax = "proto3";
package backstage.catalog.v1;

service CatalogService {
    // Entity operations
    rpc GetEntity(GetEntityRequest) returns (EntityResponse);
    rpc GetEntitiesByRefs(GetEntitiesByRefsRequest) returns (EntitiesBatchResponse);
    rpc QueryEntities(QueryEntitiesRequest) returns (QueryEntitiesResponse);
    rpc DeleteEntity(DeleteEntityRequest) returns (google.protobuf.Empty);
    
    // Location operations
    rpc CreateLocation(CreateLocationRequest) returns (CreateLocationResponse);
    rpc ListLocations(ListLocationsRequest) returns (ListLocationsResponse);
    rpc DeleteLocation(DeleteLocationRequest) returns (google.protobuf.Empty);
    
    // Refresh
    rpc RefreshEntity(RefreshEntityRequest) returns (google.protobuf.Empty);
    
    // Validation
    rpc ValidateEntity(ValidateEntityRequest) returns (ValidateEntityResponse);
    
    // Facets
    rpc GetEntityFacets(GetEntityFacetsRequest) returns (GetEntityFacetsResponse);
    
    // Ancestry
    rpc GetEntityAncestry(GetEntityAncestryRequest) returns (GetEntityAncestryResponse);
}

message GetEntityRequest {
    oneof identifier {
        string uid = 1;
        EntityRef ref = 2;
    }
    repeated string fields = 3;   // field projection
}

message EntityRef {
    string kind = 1;
    string namespace = 2;
    string name = 3;
}

message EntityResponse {
    bytes entity_json = 1;   // JSON-encoded entity (flexible schema)
}

message GetEntitiesByRefsRequest {
    repeated string entity_refs = 1;
    repeated string fields = 2;
    EntityFilter filter = 3;
}

message EntitiesBatchResponse {
    repeated bytes items = 1;  // JSON-encoded entities
}

message QueryEntitiesRequest {
    EntityFilter filter = 1;
    repeated string fields = 2;
    repeated OrderField order_fields = 3;
    int32 limit = 4;
    string cursor = 5;
    FullTextFilter full_text_filter = 6;
    bool skip_total_items = 7;
}

message EntityFilter {
    repeated FilterCriteria all_of = 1;
    repeated FilterCriteria any_of = 2;
    EntityFilter not = 3;
}

message FilterCriteria {
    string key = 1;
    repeated string values = 2;
}

message OrderField {
    string field = 1;
    string order = 2;  // "asc" or "desc"
}

message FullTextFilter {
    string term = 1;
    repeated string fields = 2;
}

message QueryEntitiesResponse {
    repeated bytes items = 1;
    int32 total_items = 2;
    PageInfo page_info = 3;
}

message PageInfo {
    string next_cursor = 1;
    string prev_cursor = 2;
}
```

## 7. Database Schema

```sql
-- migrations/000001_create_entities.up.sql

-- Final stitched entities (read-optimized)
CREATE TABLE final_entities (
    uid           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    etag          VARCHAR(255) NOT NULL DEFAULT gen_random_uuid()::text,
    entity_ref    VARCHAR(512) NOT NULL UNIQUE,
    kind          VARCHAR(100) NOT NULL,
    namespace     VARCHAR(255) NOT NULL DEFAULT 'default',
    name          VARCHAR(255) NOT NULL,
    
    -- Full entity JSON
    final_entity  JSONB NOT NULL,
    
    -- Denormalized fields for fast filtering
    title         TEXT,
    description   TEXT,
    labels        JSONB NOT NULL DEFAULT '{}',
    annotations   JSONB NOT NULL DEFAULT '{}',
    tags          JSONB NOT NULL DEFAULT '[]',
    spec_type     VARCHAR(100),     -- spec.type for Components
    spec_lifecycle VARCHAR(100),    -- spec.lifecycle for Components
    owner         VARCHAR(512),     -- spec.owner entity ref
    system        VARCHAR(512),     -- spec.system entity ref
    
    -- Timestamps
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Origin tracking
    origin_location_ref VARCHAR(1024),
    location_ref        VARCHAR(1024)
);

CREATE INDEX idx_entities_kind ON final_entities(kind);
CREATE INDEX idx_entities_namespace ON final_entities(namespace);
CREATE INDEX idx_entities_name ON final_entities(name);
CREATE INDEX idx_entities_kind_ns_name ON final_entities(kind, namespace, name);
CREATE INDEX idx_entities_spec_type ON final_entities(spec_type);
CREATE INDEX idx_entities_owner ON final_entities(owner);
CREATE INDEX idx_entities_system ON final_entities(system);
CREATE INDEX idx_entities_labels ON final_entities USING gin(labels);
CREATE INDEX idx_entities_tags ON final_entities USING gin(tags);
CREATE INDEX idx_entities_updated ON final_entities(updated_at);

-- Full-text search
ALTER TABLE final_entities ADD COLUMN search_vector tsvector;
CREATE INDEX idx_entities_search ON final_entities USING gin(search_vector);
```

```sql
-- migrations/000002_create_locations.up.sql

CREATE TABLE locations (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type       VARCHAR(100) NOT NULL,  -- "url", "file"
    target     TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(type, target)
);
```

```sql
-- migrations/000003_create_relations.up.sql

CREATE TABLE entity_relations (
    originating_entity_uid UUID NOT NULL REFERENCES final_entities(uid) ON DELETE CASCADE,
    type                   VARCHAR(100) NOT NULL,
    target_entity_ref      VARCHAR(512) NOT NULL,
    
    PRIMARY KEY (originating_entity_uid, type, target_entity_ref)
);

CREATE INDEX idx_relations_target ON entity_relations(target_entity_ref);
CREATE INDEX idx_relations_type ON entity_relations(type);
```

```sql
-- migrations/000005_create_refresh_state.up.sql

CREATE TABLE refresh_state (
    entity_ref       VARCHAR(512) PRIMARY KEY,
    location_ref     VARCHAR(1024),
    unprocessed_entity JSONB,
    processed_entity   JSONB,
    errors           JSONB,
    next_update_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_discovery_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Processing state
    state            VARCHAR(50) NOT NULL DEFAULT 'pending' -- pending, processing, done, error
);

CREATE INDEX idx_refresh_next_update ON refresh_state(next_update_at) WHERE state != 'done';
```

```sql
-- migrations/000006_create_processing_log.up.sql

CREATE TABLE entity_processing_log (
    id          BIGSERIAL PRIMARY KEY,
    entity_ref  VARCHAR(512) NOT NULL,
    level       VARCHAR(10) NOT NULL,  -- info, warning, error
    message     TEXT NOT NULL,
    source      VARCHAR(255),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_processing_log_ref ON entity_processing_log(entity_ref);
CREATE INDEX idx_processing_log_time ON entity_processing_log(created_at);
```

## 8. Ingestion Pipeline

```go
// internal/usecase/ingestion/ingestion_usecase.go

// Pipeline: Discover → Read → Parse → Process → Stitch → Store

type IngestionPipeline struct {
    providers  []EntityProvider
    processors []EntityProcessor
    stitcher   *Stitcher
    entityRepo EntityRepository
    publisher  EventPublisher
    logger     zerolog.Logger
}

// EntityProvider discovers and reads entities from external sources
type EntityProvider interface {
    Name() string
    Connect(ctx context.Context) error
    Read(ctx context.Context) (<-chan EntityProviderResult, error)
    GetRefreshSchedule() time.Duration
}

// EntityProcessor transforms/enriches entities
type EntityProcessor interface {
    Name() string
    // PreProcess runs before main processing
    PreProcess(ctx context.Context, entity *entity.Entity) (*entity.Entity, error)
    // PostProcess runs after main processing  
    PostProcess(ctx context.Context, entity *entity.Entity) (*entity.Entity, error)
    // ValidateEntityKind validates entity kind-specific schema
    ValidateEntityKind(ctx context.Context, entity *entity.Entity) error
}

// Built-in processors
// 1. AnnotationProcessor — set default annotations
// 2. RelationProcessor — extract relations from spec
// 3. OwnerProcessor — resolve spec.owner to entity ref
// 4. LifecycleProcessor — normalize lifecycle field
// 5. SearchIndexProcessor — update search vector
```

## 9. Configuration

```yaml
catalog:
  readonly: false
  
  processing:
    interval: "100ms"        # Interval between processing runs
    workers: 4               # Number of parallel processing workers
    max_items_per_run: 100   # Max entities per processing run
  
  locations:
    # Built-in locations
    - type: url
      target: https://github.com/backstage/backstage/blob/master/catalog-info.yaml
  
  providers:
    github:
      - host: github.com
        organization: "my-org"
        catalog_path: "/catalog-info.yaml"
        schedule:
          frequency: "30m"
          timeout: "3m"
    
    gitlab:
      - host: gitlab.com
        branch: "main"
        catalog_path: "/catalog-info.yaml"

  rules:
    - allow: [Component, System, API, Resource, Location, Template, Domain, Group, User]

database:
  host: "postgres-catalog"
  port: 5432
  name: "backstage_catalog"
  user: "${DB_USER}"
  password: "${DB_PASSWORD}"
  max_open_conns: 30
  max_idle_conns: 10
```

## 10. Event Publishing

Catalog Service publish events khi entities thay đổi:

```
backstage.catalog.entity.created   — New entity registered
backstage.catalog.entity.updated   — Entity updated
backstage.catalog.entity.deleted   — Entity removed
backstage.catalog.location.created — New location added
backstage.catalog.location.deleted — Location removed
backstage.catalog.refresh.requested — Manual refresh triggered
```

Các service khác (Search, Notifications) subscribe để react to changes.
