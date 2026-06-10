# 06 — TechDocs Service

## 1. Tổng quan

TechDocs Service quản lý documentation cho entities — build docs từ Markdown/MkDocs, publish lên object storage, và serve cho frontend.

**Tương ứng TypeScript**:
- `plugin-techdocs-backend` — Core techdocs: prepare, generate, publish, serve

## 2. Responsibilities

- **Doc Preparation**: Fetch docs source từ SCM (Git repos)
- **Doc Generation**: Build static HTML từ MkDocs/Markdown
- **Doc Publishing**: Upload generated docs lên object storage (S3/GCS/Azure Blob/Local)
- **Doc Serving**: Serve static doc files cho frontend
- **Build Strategy**: Configurable local vs. external build
- **Cache Management**: Cache built docs cho performance

## 3. Cấu trúc dự án

```
techdocs-service/
├── cmd/server/main.go
├── internal/
│   ├── entity/
│   │   ├── doc_entity.go            # TechDocs entity info
│   │   ├── build.go                 # Build request/result
│   │   ├── publisher.go             # Publisher config
│   │   └── errors.go
│   │
│   ├── usecase/
│   │   ├── interfaces.go
│   │   ├── build_usecase.go         # Prepare + Generate + Publish
│   │   ├── serve_usecase.go         # Serve static docs
│   │   ├── sync_usecase.go          # Sync/check if docs need rebuild
│   │   └── metadata_usecase.go      # Get techdocs metadata
│   │
│   ├── adapter/
│   │   ├── handler/
│   │   │   ├── http/
│   │   │   │   ├── router.go
│   │   │   │   ├── docs_handler.go      # Serve docs content
│   │   │   │   ├── sync_handler.go      # Sync/build trigger
│   │   │   │   └── metadata_handler.go  # Entity techdocs metadata
│   │   │   └── grpc/
│   │   │       ├── server.go
│   │   │       └── techdocs_handler.go
│   │   ├── preparer/
│   │   │   ├── preparer_interface.go
│   │   │   ├── url_preparer.go          # Fetch from URL
│   │   │   ├── git_preparer.go          # Clone from Git
│   │   │   └── dir_preparer.go          # Local directory
│   │   ├── generator/
│   │   │   ├── generator_interface.go
│   │   │   └── mkdocs_generator.go      # MkDocs site generation
│   │   └── publisher/
│   │       ├── publisher_interface.go
│   │       ├── local_publisher.go       # Local filesystem
│   │       ├── s3_publisher.go          # AWS S3
│   │       ├── gcs_publisher.go         # Google Cloud Storage
│   │       └── azure_publisher.go       # Azure Blob Storage
│   │
│   └── infrastructure/
│       ├── config/config.go
│       ├── server/
│       │   ├── http.go
│       │   └── grpc.go
│       ├── cache/
│       │   └── file_cache.go
│       └── client/
│           └── catalog_client.go
│
├── api/
│   ├── proto/techdocs.proto
│   └── openapi/openapi.yaml
├── config/config.yaml
├── Dockerfile
└── go.mod
```

## 4. API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/static/docs/:namespace/:kind/:name/**` | Serve static doc files |
| `GET` | `/metadata/techdocs/:namespace/:kind/:name` | Get techdocs metadata (etag, build timestamp) |
| `GET` | `/metadata/entity/:namespace/:kind/:name` | Get entity techdocs metadata |
| `POST` | `/sync/:namespace/:kind/:name` | Trigger doc sync/rebuild |
| `GET` | `/health` | Health check |

## 5. Build Pipeline

```
1. Preparer: Clone/fetch source code from SCM
       ↓
2. Generator: Run `mkdocs build` to generate static HTML
       ↓
3. Publisher: Upload generated files to object storage
       ↓
4. Cache: Update cache metadata (etag, timestamp)
```

```go
type BuildStrategy interface {
    ShouldBuild(ctx context.Context, entityRef string) (bool, error)
}

// "local" strategy — build docs in this service
// "external" strategy — docs already built by CI/CD pipeline
```

## 6. Configuration

```yaml
techdocs:
  builder: "local"            # "local" or "external"
  generator:
    runIn: "local"            # "local" or "docker"
    mkdocs:
      default_plugins:
        - techdocs-core
  
  publisher:
    type: "local"             # "local", "googleGcs", "awsS3", "azureBlobStorage"
    local:
      publish_dir: "./techdocs-output"
    googleGcs:
      bucket: "backstage-techdocs"
      project_id: "${GCP_PROJECT_ID}"
    awsS3:
      bucket: "backstage-techdocs"
      region: "us-east-1"
  
  cache:
    ttl: "30m"

  security:
    # Allowlisted mkdocs.yml keys to prevent code execution
    mkdocs_allowlist:
      - site_name
      - site_description
      - repo_url
      - edit_uri
      - docs_dir
      - nav
      - theme
      - plugins
      - markdown_extensions
      - extra
```
