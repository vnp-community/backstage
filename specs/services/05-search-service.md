# 05 — Search Service

## 1. Tổng quan

Search Service cung cấp full-text search cho toàn bộ Backstage, hỗ trợ multiple search engines (Lunr built-in, Elasticsearch, PostgreSQL), indexing pipeline với collators và decorators.

**Tương ứng TypeScript**:
- `plugin-search-backend` — Core search engine, authorized search
- `plugin-search-backend-module-catalog` — Catalog entity collator
- `plugin-search-backend-module-techdocs` — TechDocs content collator
- `plugin-search-backend-module-explore` — Explore tools collator
- `plugin-search-backend-module-elasticsearch` — Elasticsearch engine
- `plugin-search-backend-module-pg` — PostgreSQL search engine

## 2. Responsibilities

- **Search Query**: Xử lý search queries với filters, pagination
- **Search Indexing**: Index documents từ multiple sources qua collators
- **Collator Management**: Register và run collators (catalog, techdocs, etc.)
- **Decorator Management**: Enrich search documents trước khi index
- **Search Engine Abstraction**: Pluggable search engine (Lunr, ES, PG)
- **Permission-aware Search**: Filter results based on user permissions
- **Scheduled Indexing**: Periodic re-index theo schedule

## 3. Cấu trúc dự án

```
search-service/
├── cmd/server/main.go
├── internal/
│   ├── entity/
│   │   ├── document.go              # Search document model
│   │   ├── query.go                 # Search query model
│   │   ├── result.go                # Search result model
│   │   ├── index.go                 # Index configuration
│   │   └── errors.go
│   │
│   ├── usecase/
│   │   ├── interfaces.go
│   │   ├── search_usecase.go        # Execute search queries
│   │   ├── index_usecase.go         # Manage indexing pipeline
│   │   └── schedule_usecase.go      # Scheduled indexing
│   │
│   ├── adapter/
│   │   ├── handler/
│   │   │   ├── http/
│   │   │   │   ├── router.go
│   │   │   │   └── search_handler.go
│   │   │   └── grpc/
│   │   │       ├── server.go
│   │   │       └── search_handler.go
│   │   ├── engine/                   # Search engine implementations
│   │   │   ├── engine_interface.go
│   │   │   ├── lunr/                 # Built-in Lunr (bleve for Go)
│   │   │   │   └── lunr_engine.go
│   │   │   ├── elasticsearch/
│   │   │   │   └── es_engine.go
│   │   │   └── postgres/
│   │   │       └── pg_engine.go
│   │   ├── collator/                 # Search collators
│   │   │   ├── collator_interface.go
│   │   │   ├── catalog_collator.go   # Index catalog entities
│   │   │   ├── techdocs_collator.go  # Index techdocs content
│   │   │   └── explore_collator.go   # Index explore tools
│   │   └── decorator/
│   │       └── decorator_interface.go
│   │
│   └── infrastructure/
│       ├── config/config.go
│       ├── database/postgres.go
│       ├── server/
│       │   ├── http.go
│       │   └── grpc.go
│       └── client/
│           ├── catalog_client.go
│           ├── techdocs_client.go
│           └── permission_client.go
│
├── api/
│   ├── proto/search.proto
│   └── openapi/openapi.yaml
├── config/config.yaml
├── Dockerfile
└── go.mod
```

## 4. Entity Models

```go
// internal/entity/document.go

type SearchDocument struct {
    Title       string            `json:"title"`
    Text        string            `json:"text"`
    Location    string            `json:"location"`    // URL to the item
    DocType     string            `json:"type"`        // "software-catalog", "techdocs"
    
    // Additional fields (flexible)
    Fields      map[string]any    `json:"fields,omitempty"`
}

type IndexableDocument struct {
    SearchDocument
    Authorization AuthorizationInfo `json:"authorization,omitempty"`
}

type AuthorizationInfo struct {
    ResourceRef string `json:"resourceRef"`  // entity ref for permission check
}
```

```go
// internal/entity/query.go

type SearchQuery struct {
    Term    string            `json:"term"`
    Filters map[string]any   `json:"filters,omitempty"`
    Types   []string          `json:"types,omitempty"`    // document types
    PageCursor string         `json:"pageCursor,omitempty"`
}

type SearchResult struct {
    Results    []SearchResultItem `json:"results"`
    NextPage   string             `json:"nextPageCursor,omitempty"`
    TotalCount int                `json:"numberOfResults,omitempty"`
}

type SearchResultItem struct {
    Type      string         `json:"type"`
    Document  SearchDocument `json:"document"`
    Highlight HighlightInfo  `json:"highlight,omitempty"`
    Rank      float64        `json:"rank"`
}

type HighlightInfo struct {
    PreTag  string `json:"preTag"`
    PostTag string `json:"postTag"`
    Fields  map[string]string `json:"fields"`
}
```

## 5. Use Case Interfaces

```go
type SearchEngine interface {
    // Index a batch of documents for a given type
    Index(ctx context.Context, docType string, documents []IndexableDocument) error
    // Execute a search query
    Query(ctx context.Context, query SearchQuery) (*SearchResult, error)
    // Get all registered document types
    GetDocumentTypes() map[string]DocumentTypeInfo
}

type Collator interface {
    // Type returns the document type this collator produces
    Type() string
    // Collect gathers documents from the source
    Collect(ctx context.Context) (<-chan IndexableDocument, error)
    // Schedule returns how often to re-collect
    Schedule() time.Duration
}

type Decorator interface {
    // Decorate enriches a document before indexing
    Decorate(ctx context.Context, doc *IndexableDocument) error
}

type PermissionChecker interface {
    FilterResults(ctx context.Context, results []SearchResultItem, userRef string) ([]SearchResultItem, error)
}
```

## 6. API Endpoints

### 6.1 REST API

| Method | Path | Description |
|---|---|---|
| `GET` | `/query` | Execute search query (query params) |
| `POST` | `/query` | Execute search query (body params) |

### 6.2 gRPC API

```protobuf
syntax = "proto3";
package backstage.search.v1;

service SearchService {
    rpc Query(SearchQueryRequest) returns (SearchResultResponse);
    rpc GetDocumentTypes(GetDocumentTypesRequest) returns (GetDocumentTypesResponse);
    rpc TriggerReindex(TriggerReindexRequest) returns (google.protobuf.Empty);
}
```

## 7. Indexing Pipeline

```go
// Indexing flow:
// 1. Collator collects documents from source (catalog, techdocs)
// 2. Decorators enrich documents
// 3. Search engine indexes documents

func (u *IndexUseCase) RunIndexing(ctx context.Context) {
    for _, collator := range u.collators {
        docChan, err := collator.Collect(ctx)
        if err != nil {
            u.logger.Error().Err(err).Str("type", collator.Type()).Msg("Collation failed")
            continue
        }
        
        var batch []IndexableDocument
        for doc := range docChan {
            // Apply decorators
            for _, decorator := range u.decorators {
                decorator.Decorate(ctx, &doc)
            }
            batch = append(batch, doc)
            
            if len(batch) >= 500 {
                u.engine.Index(ctx, collator.Type(), batch)
                batch = batch[:0]
            }
        }
        
        if len(batch) > 0 {
            u.engine.Index(ctx, collator.Type(), batch)
        }
    }
}
```

## 8. Configuration

```yaml
search:
  engine: "lunr"   # "lunr", "elasticsearch", "postgres"
  
  elasticsearch:
    node: "http://elasticsearch:9200"
    username: "${ES_USER}"
    password: "${ES_PASSWORD}"
    
  indexing:
    schedule: "10m"          # Re-index every 10 minutes
    batch_size: 500
    
  collators:
    catalog:
      enabled: true
      schedule: "10m"
      filter:
        kind: ["Component", "API", "System", "Domain"]
    
    techdocs:
      enabled: true
      schedule: "30m"
```
