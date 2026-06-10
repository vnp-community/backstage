# Software Requirements Specification (SRS)

## Backstage — Open Source Developer Portal

| Thông tin | Chi tiết |
|-----------|----------|
| **Dự án** | Backstage |
| **Phiên bản** | 1.51.0 |
| **Chuẩn tham chiếu** | IEEE 830-1998 |
| **Ngày tạo tài liệu** | 27/05/2026 |

---

## 1. Giới thiệu

### 1.1. Mục đích

Tài liệu này mô tả chi tiết các yêu cầu phần mềm (Software Requirements) cho hệ thống Backstage Developer Portal, bao gồm yêu cầu chức năng, phi chức năng, giao diện, và ràng buộc thiết kế.

### 1.2. Phạm vi

Backstage là một framework mã nguồn mở cho việc xây dựng Developer Portal. Hệ thống bao gồm:

- **Frontend Application**: Ứng dụng Single Page Application (SPA) dựa trên React
- **Backend Application**: API server dựa trên Node.js/Express
- **Plugin System**: Hệ thống plugin cho cả frontend và backend
- **CLI Tooling**: Bộ công cụ dòng lệnh cho phát triển và vận hành

### 1.3. Thuật ngữ và viết tắt

| Thuật ngữ | Định nghĩa |
|-----------|-----------|
| **Entity** | Đơn vị cơ bản trong Software Catalog (Component, API, System, Domain, Resource, User, Group, Location, Template) |
| **Plugin** | Module mở rộng chức năng cho Backstage, có thể là frontend plugin, backend plugin, hoặc cả hai |
| **Scaffolder** | Hệ thống tạo project từ template (Software Templates) |
| **TechDocs** | Hệ thống tài liệu kỹ thuật tích hợp sử dụng MkDocs |
| **Collator** | Component trong hệ thống Search thu thập dữ liệu để index |
| **Extension** | Đơn vị mở rộng UI trong frontend plugin system mới |
| **Blueprint** | Pattern factory để tạo extensions |
| **Feature Loader** | Cơ chế lazy-loading backend features dựa trên configuration |

### 1.4. Tài liệu tham chiếu

- [Backstage Architecture Overview](https://backstage.io/docs/overview/architecture-overview)
- [Backstage Threat Model](https://backstage.io/docs/overview/threat-model)
- [Backstage Versioning Policy](https://backstage.io/docs/overview/versioning-policy)
- [CNCF Incubation Requirements](https://www.cncf.io/projects)
- PRD.md — Product Requirements Document
- URD.md — User Requirements Document

---

## 2. Mô tả tổng thể

### 2.1. Perspective hệ thống

Backstage hoạt động như một **unified developer portal** — lớp UX tập trung nằm trên toàn bộ hạ tầng phần mềm và công cụ của tổ chức. Hệ thống không thay thế các công cụ hiện có mà tích hợp và cung cấp giao diện thống nhất.

```
┌────────────────────────────────────────────────────────────┐
│                      Người dùng (Browser)                  │
└─────────────────────────┬──────────────────────────────────┘
                          │ HTTPS
┌─────────────────────────▼──────────────────────────────────┐
│                   Frontend (React SPA)                     │
│  Port: 3000 (dev) / Served by Backend (prod)               │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────────┐    │
│  │ Core UI     │ │ Plugin UIs   │ │ Extension System │    │
│  │ Components  │ │ (Catalog,    │ │ (Blueprints,     │    │
│  │ (@backstage/│ │  Scaffolder, │ │  Modules)        │    │
│  │ core-       │ │  TechDocs,   │ │                  │    │
│  │ components) │ │  Search,...) │ │                  │    │
│  └─────────────┘ └──────────────┘ └──────────────────┘    │
├────────────────────────────────────────────────────────────┤
│              Backend API Gateway (Express.js)              │
│  Port: 7007                                                │
│  ┌─────────────────────────────────────────────────┐      │
│  │         Backend Plugin API Framework             │      │
│  │  createBackend() → plugin registration           │      │
│  │  createBackendFeatureLoader() → lazy loading     │      │
│  └─────────────────────────────────────────────────┘      │
│  ┌──────┐ ┌──────────┐ ┌────────┐ ┌──────┐ ┌──────┐     │
│  │Auth  │ │Catalog   │ │Scaffold│ │Search│ │Events│     │
│  │Plugin│ │Plugin    │ │Plugin  │ │Plugin│ │Plugin│     │
│  └──┬───┘ └──┬───────┘ └───┬────┘ └──┬───┘ └──┬───┘     │
├─────┼────────┼─────────────┼─────────┼────────┼──────────┤
│     ▼        ▼             ▼         ▼        ▼          │
│  ┌──────┐ ┌──────┐    ┌──────┐  ┌────────┐ ┌──────┐     │
│  │IdP   │ │DB    │    │SCM   │  │Search  │ │Event │     │
│  │GitHub │ │PgSQL │    │GitHub│  │Engine  │ │Sources│    │
│  │Google │ │SQLite│    │GitLab│  │OS/ES   │ │Kafka │     │
│  │Okta  │ │      │    │Azure │  │        │ │PubSub│     │
│  │...   │ │      │    │...   │  │        │ │...   │     │
│  └──────┘ └──────┘    └──────┘  └────────┘ └──────┘     │
└────────────────────────────────────────────────────────────┘
```

### 2.2. Chức năng sản phẩm (Product Functions)

1. **Software Catalog**: Quản lý tập trung các software entities
2. **Software Templates**: Tạo nhanh project từ template chuẩn hóa
3. **TechDocs**: Tài liệu kỹ thuật tích hợp (docs-as-code)
4. **Search**: Tìm kiếm xuyên suốt toàn bộ portal
5. **Authentication**: Xác thực người dùng đa provider
6. **Authorization**: Phân quyền truy cập (Permission System)
7. **Kubernetes Dashboard**: Hiển thị K8s workloads
8. **Notifications**: Hệ thống thông báo
9. **Signals**: Real-time updates
10. **Events**: Event-driven backend architecture
11. **API Documentation**: Hiển thị API specs
12. **DevTools**: Công cụ quản trị

### 2.3. Đặc điểm người dùng

Xem chi tiết trong URD.md — Mục 2 (Nhóm người dùng).

### 2.4. Ràng buộc thiết kế

| Ràng buộc | Chi tiết |
|-----------|----------|
| **License** | Apache License 2.0 |
| **Runtime** | Node.js 22 hoặc 24 |
| **Package Manager** | Yarn 4.8.1 (Berry) |
| **Monorepo** | Yarn Workspaces (`packages/*`, `plugins/*`) |
| **TypeScript** | Version ~5.7.0, strict mode |
| **React** | Version ^18.0.2 |
| **Routing** | React Router 6 |
| **Styling** | Material UI 4 (legacy), Backstage UI (BUI) cho components mới |
| **Backend Framework** | Express.js (wrapped bởi Backstage Backend Plugin API) |
| **Database ORM** | Knex.js |
| **Configuration** | YAML-based (`app-config.yaml`) |
| **API Design** | Named exports (ADR003), avoid React.FC (ADR006) |
| **Testing** | Jest 30 (unit), Playwright (e2e), MSW (mocking - ADR007) |
| **Date Library** | Luxon (ADR010, ADR012) |
| **HTTP Client** | Fetch API (ADR014) |

### 2.5. Giả định và phụ thuộc

Xem chi tiết trong URD.md — Mục 6 và Mục 7.

---

## 3. Yêu cầu chức năng (Functional Requirements)

### 3.1. Module: Software Catalog

#### FR-CAT-001: Entity Registration

| Thuộc tính | Mô tả |
|------------|-------|
| **Input** | YAML file (`catalog-info.yaml`) chứa entity descriptor |
| **Processing** | - Parse YAML theo entity format (apiVersion, kind, metadata, spec)<br>- Validate theo registered entity kinds<br>- Xử lý entity references<br>- Lưu vào database |
| **Output** | Entity được đăng ký trong catalog, hiển thị trên UI |
| **Entity Kinds hỗ trợ** | Component, API, Resource, System, Domain, Location, User, Group, Template, AiResource |

**Descriptor Format (catalog-info.yaml):**

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: <string>          # required, unique identifier
  description: <string>   # optional
  labels: <map>           # optional
  annotations: <map>      # optional
  links:                  # optional
    - title: <string>
      url: <string>
spec:
  type: <string>          # service, website, library, etc.
  owner: <entity-ref>     # required
  lifecycle: <string>     # production, experimental, deprecated
  system: <entity-ref>    # optional
  dependsOn: [<entity-ref>]  # optional
  providesApis: [<entity-ref>]  # optional
  consumesApis: [<entity-ref>]  # optional
```

#### FR-CAT-002: Entity Discovery Providers

| Thuộc tính | Mô tả |
|------------|-------|
| **Providers** | GitHub, GitLab, Bitbucket Cloud, Bitbucket Server, Azure DevOps, Gerrit, Gitea, AWS, GCP, LDAP, Microsoft Graph, Azure Blob |
| **Schedule** | Cấu hình frequency và timeout cho mỗi provider |
| **Processing** | Incremental ingestion hoặc full scan tùy provider |

**Configuration mẫu:**

```yaml
catalog:
  providers:
    azureBlob:
      accountName: ${ACCOUNT_NAME}
      containerName: ${CONTAINER_NAME}
      schedule:
        frequency: { minutes: 30 }
        timeout: { minutes: 3 }
```

#### FR-CAT-003: Entity Processing Pipeline

| Thuộc tính | Mô tả |
|------------|-------|
| **Input** | Raw entity data từ locations hoặc providers |
| **Pipeline stages** | 1. Fetch (lấy YAML từ source)<br>2. Parse (validate format)<br>3. Pre-process (enrich metadata)<br>4. Validate (check references, kind-specific rules)<br>5. Emit (tạo/cập nhật entity, emit relations) |
| **Output** | Processed entities với relations, annotations, statuses |
| **Error handling** | Unprocessed entities được log và hiển thị trong DevTools |

#### FR-CAT-004: Catalog API

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/api/catalog/entities` | GET | List entities với filter |
| `/api/catalog/entities/{uid}` | GET | Get entity by UID |
| `/api/catalog/entities/by-name/{kind}/{namespace}/{name}` | GET | Get entity by name |
| `/api/catalog/locations` | POST | Register new location |
| `/api/catalog/locations` | GET | List locations |
| `/api/catalog/refresh` | POST | Trigger refresh |

#### FR-CAT-005: Catalog UI Components

| Component | Mô tả |
|-----------|-------|
| `CatalogIndexPage` | Trang danh sách catalog entities |
| `CatalogEntityPage` | Trang chi tiết entity |
| `EntityAboutCard` | Card hiển thị metadata |
| `EntityLinksCard` | Card hiển thị links |
| `EntityLabelsCard` | Card hiển thị labels |
| `EntityRelationsGraph` | Graph visualization |
| `CatalogImportPage` | Trang import entity |

---

### 3.2. Module: Software Templates (Scaffolder)

#### FR-TPL-001: Template Execution Engine

| Thuộc tính | Mô tả |
|------------|-------|
| **Input** | Template YAML + User-provided parameters |
| **Processing** | 1. Validate parameters theo JSON Schema<br>2. Execute actions tuần tự<br>3. Report progress qua streaming |
| **Output** | Generated files/repository + registered catalog entity |
| **Audit** | Task parameter logging (max length: 256 characters) |

#### FR-TPL-002: Built-in Template Actions

| Action Category | Actions |
|----------------|---------|
| **Fetch** | `fetch:plain`, `fetch:template` |
| **Publish** | GitHub, GitLab, Bitbucket Cloud/Server, Azure, Gerrit, Gitea |
| **Catalog** | `catalog:register`, `catalog:write` |
| **Debug** | `debug:log`, `debug:wait` |
| **Filesystem** | `fs:delete`, `fs:rename`, `fs:append` |
| **Notifications** | `notification:send` |
| **CI/CD** | GCP (Cloud Build), Sentry, Rails, Yeoman, Cookiecutter |

#### FR-TPL-003: Template UI

| Tính năng | Mô tả |
|-----------|-------|
| **Template List** | Hiển thị templates nhóm theo danh mục (filter by `spec.type`) |
| **Wizard Form** | Multi-step form dựa trên JSON Schema |
| **Custom Step Layouts** | Cho phép tùy chỉnh layout từng step |
| **BUI Form Theme** | Theme mới với Backstage UI components (experimental) |
| **Progress View** | Real-time task execution progress |
| **Dry Run** | Preview kết quả mà không thực thi |

**Template configuration mẫu:**

```yaml
scaffolder:
  defaultAuthor:
    name: Scaffolder
    email: scaffolder@backstage.io
  defaultCommitMessage: 'Initial commit'
  auditor:
    taskParameterMaxLength: 256
```

---

### 3.3. Module: TechDocs

#### FR-DOC-001: Documentation Build Pipeline

| Thuộc tính | Mô tả |
|------------|-------|
| **Input** | MkDocs project (mkdocs.yml + Markdown files) |
| **Builder** | Local (trong Backstage process) hoặc External (CI/CD) |
| **Generator** | MkDocs chạy trong Docker hoặc local environment |
| **Docker Image** | Custom image hoặc default `mkdocs-techdocs-core` |
| **Output** | Static HTML site được publish lên storage |

**Configuration:**

```yaml
techdocs:
  builder: 'local'          # hoặc 'external'
  generator:
    runIn: 'docker'          # hoặc 'local'
  publisher:
    type: 'local'            # hoặc 'googleGcs', 'awsS3', 'azureBlobStorage', 'openStackSwift'
```

#### FR-DOC-002: TechDocs Publisher

| Storage Type | Configuration |
|-------------|---------------|
| **Local** | Filesystem-based, cho development |
| **Google GCS** | `clientEmail`, `privateKey`, `bucketName` |
| **AWS S3** | `endpoint`, `accessKeyId`, `secretAccessKey`, `bucketName` |
| **Azure Blob** | `accountName`, `containerName`, `accountKey` hoặc AAD credentials |
| **OpenStack Swift** | Endpoint + credentials |

#### FR-DOC-003: TechDocs UI

| Component | Mô tả |
|-----------|-------|
| `TechDocsIndexPage` | Danh sách tất cả entities có TechDocs |
| `TechDocsReaderPage` | Reader page (`/docs/:namespace/:kind/:name/*`) |
| `EntityTechdocsContent` | Entity tab hiển thị docs inline |
| **Addons** | Extension system cho TechDocs reader |

---

### 3.4. Module: Search

#### FR-SRC-001: Search Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Collators   │────▶│ Search Index │────▶│ Search Engine  │
│  - Catalog   │     │  Pipeline    │     │  - In-memory   │
│  - TechDocs  │     │              │     │  - OpenSearch  │
│  - Explore   │     │              │     │  - Elastic     │
│  - Custom    │     │              │     │                │
└─────────────┘     └──────────────┘     └───────┬───────┘
                                                  │
                                          ┌───────▼───────┐
                                          │  Search API   │
                                          │  /api/search  │
                                          └───────┬───────┘
                                                  │
                                          ┌───────▼───────┐
                                          │  Search UI    │
                                          │  SearchBar    │
                                          │  SearchPage   │
                                          └───────────────┘
```

#### FR-SRC-002: Search Engine Configuration

| Engine | Configuration |
|--------|---------------|
| **In-memory** | Mặc định, không cần cấu hình |
| **OpenSearch** | `search.elasticsearch.provider: opensearch`<br>`search.elasticsearch.node: <url>` |
| **Elasticsearch** | `search.elasticsearch.node: <url>` |

#### FR-SRC-003: Search Collators

| Collator | Source | Data |
|----------|--------|------|
| `CatalogCollator` | Software Catalog | Entities metadata |
| `TechDocsCollator` | TechDocs | Documentation content |
| `ExploreCollator` | Explore | Tools và resources |
| `StackOverflowCollator` | Stack Overflow | Q&A entries |

---

### 3.5. Module: Authentication

#### FR-AUTH-001: Authentication Flow

```
┌────────┐     ┌──────────┐     ┌──────────┐     ┌────────┐
│ User   │────▶│ Frontend │────▶│ Auth     │────▶│ IdP    │
│ Browser│     │ Auth UI  │     │ Backend  │     │ (OAuth)│
└────────┘     └──────────┘     └──────────┘     └────────┘
                                     │
                               ┌─────▼─────┐
                               │ Sign-in   │
                               │ Resolver  │
                               │ (map to   │
                               │  catalog) │
                               └───────────┘
```

#### FR-AUTH-002: Provider Configuration

**Cấu hình mẫu cho GitHub OAuth:**

```yaml
auth:
  environment: development
  providers:
    github:
      development:
        clientId: ${AUTH_GITHUB_CLIENT_ID}
        clientSecret: ${AUTH_GITHUB_CLIENT_SECRET}
        enterpriseInstanceUrl: ${AUTH_GITHUB_ENTERPRISE_INSTANCE_URL}
```

#### FR-AUTH-003: Sign-in Resolver

| Thuộc tính | Mô tả |
|------------|-------|
| **Mục đích** | Map identity từ IdP sang Backstage user entity |
| **Input** | OAuth profile (email, username, groups) |
| **Output** | Backstage identity token (JWT) |
| **Custom resolvers** | Hỗ trợ viết custom sign-in resolvers |

#### FR-AUTH-004: Service-to-Service Auth

| Thuộc tính | Mô tả |
|------------|-------|
| **Mục đích** | Authentication giữa các backend plugins |
| **Cơ chế** | Token-based (JWT) |
| **Configuration** | `backend.auth.keys` hoặc `dangerouslyDisableDefaultAuthPolicy` (development) |

#### FR-AUTH-005: Dynamic Client Registration

| Thuộc tính | Mô tả |
|------------|-------|
| **Status** | Experimental |
| **Mục đích** | Cho phép OAuth clients đăng ký động |
| **Configuration** | `auth.experimentalDynamicClientRegistration.enabled: true` |

---

### 3.6. Module: Permission System

#### FR-PERM-001: Permission Policy Engine

| Thuộc tính | Mô tả |
|------------|-------|
| **Input** | Permission request (principal, resource, action) |
| **Processing** | Policy evaluation chain |
| **Output** | ALLOW hoặc DENY |
| **Default** | Allow-all policy (development) |

#### FR-PERM-002: Permission Configuration

```yaml
permission:
  enabled: true  # Global toggle
```

---

### 3.7. Module: Events System

#### FR-EVT-001: Event Bus

| Thuộc tính | Mô tả |
|------------|-------|
| **Mục đích** | Pub/Sub event bus cho backend plugins |
| **Supported Sources** | AWS SQS, Azure Service Bus, Bitbucket Cloud/Server, Gerrit, GitHub, GitLab, Google Pub/Sub, Kafka |
| **Pattern** | Subscribe to topics, publish events |

---

### 3.8. Module: Notifications

#### FR-NTF-001: Notification Service

| Thuộc tính | Mô tả |
|------------|-------|
| **Backend** | REST API cho tạo/quản lý notifications |
| **Frontend** | UI component hiển thị notification bell + notification page |
| **Channels** | In-app (default), Email, Slack |
| **Processors** | Custom notification processors |

---

### 3.9. Module: Kubernetes

#### FR-K8S-001: Kubernetes Backend

| Thuộc tính | Mô tả |
|------------|-------|
| **Mục đích** | Kết nối với K8s clusters và lấy workload data |
| **Authentication** | Service Account, OIDC, AWS IAM, Google Cloud |
| **Data** | Pods, Deployments, Services, ReplicaSets, HPA, Ingresses |

#### FR-K8S-002: Kubernetes UI

| Component | Mô tả |
|-----------|-------|
| `KubernetesClusterPage` | Cluster overview |
| `EntityKubernetesContent` | Entity-scoped K8s workloads |

---

### 3.10. Module: API Documentation

#### FR-API-001: API Docs Rendering

| Spec Format | Renderer |
|-------------|----------|
| OpenAPI 2.0/3.x | Swagger UI |
| AsyncAPI | AsyncAPI React component |
| GraphQL | GraphQL Voyager |
| gRPC (Protobuf) | protoc-gen-doc |

#### FR-API-002: API Entity Relations

| Relation | Mô tả |
|----------|-------|
| `providesApi` | Component cung cấp API |
| `consumesApi` | Component sử dụng API |
| `apiProvidedBy` | API được cung cấp bởi Component |
| `apiConsumedBy` | API được sử dụng bởi Component |

---

### 3.11. Module: Proxy

#### FR-PRX-001: Backend Proxy

| Thuộc tính | Mô tả |
|------------|-------|
| **Mục đích** | Proxy requests từ frontend qua backend đến external APIs |
| **Configuration** | Trong `proxy.endpoints` |
| **Headers** | Inject authentication headers |

**Configuration mẫu:**

```yaml
proxy:
  endpoints:
    '/pagerduty':
      target: https://api.pagerduty.com
      headers:
        Authorization: Token token=${PAGERDUTY_TOKEN}
```

---

### 3.12. Module: Signals

#### FR-SIG-001: Real-time Signal Service

| Thuộc tính | Mô tả |
|------------|-------|
| **Protocol** | WebSocket |
| **Backend** | Signal publishing service |
| **Frontend** | React hooks cho subscribing to signals |
| **Use cases** | Real-time catalog updates, notification alerts |

---

## 4. Yêu cầu phi chức năng (Non-Functional Requirements)

### 4.1. Hiệu năng (Performance)

| ID | Yêu cầu | Metric |
|----|----------|--------|
| NFR-PERF-001 | Frontend initial load time | FCP < 2s, TTI < 5s |
| NFR-PERF-002 | Catalog API response time | p95 < 500ms |
| NFR-PERF-003 | Search query response time | p95 < 1s |
| NFR-PERF-004 | Lighthouse Performance Score | > 80 |
| NFR-PERF-005 | Backend memory usage | Stable under load (no memory leaks) |
| NFR-PERF-006 | TypeScript compilation | Hỗ trợ incremental builds |

### 4.2. Bảo mật (Security)

| ID | Yêu cầu | Mô tả |
|----|----------|-------|
| NFR-SEC-001 | Input Validation | Sử dụng `resolveSafeChildPath` cho file path resolution |
| NFR-SEC-002 | XSS Prevention | Express responses phải dùng `.json()` hoặc `.end()`, không dùng `.send()` cho user input |
| NFR-SEC-003 | CSP Headers | Content-Security-Policy configuration qua Helmet |
| NFR-SEC-004 | CORS | Configurable CORS policy (origin, methods, credentials) |
| NFR-SEC-005 | Secrets Management | Secrets qua environment variables `${VAR_NAME}`, không hardcode |
| NFR-SEC-006 | Vulnerability Scanning | Snyk integration, `.snyk` policy files |
| NFR-SEC-007 | Security Reporting | HackerOne bug bounty program |
| NFR-SEC-008 | CVE Management | GitHub Security Advisories, CVSS scoring |
| NFR-SEC-009 | Authentication | Bắt buộc authentication cho production |
| NFR-SEC-010 | Authorization | Permission-based access control |

### 4.3. Khả năng mở rộng (Scalability)

| ID | Yêu cầu | Mô tả |
|----|----------|-------|
| NFR-SCL-001 | Horizontal Scaling | Backend hỗ trợ multiple instances behind load balancer |
| NFR-SCL-002 | Database Scaling | PostgreSQL connection pooling |
| NFR-SCL-003 | Search Scaling | External search engine (OpenSearch/Elasticsearch) |
| NFR-SCL-004 | Cache | Redis caching layer |
| NFR-SCL-005 | Plugin Architecture | Loose coupling giữa plugins, independent deployment |

### 4.4. Tính sẵn sàng (Availability)

| ID | Yêu cầu | Mô tả |
|----|----------|-------|
| NFR-AVL-001 | Graceful Degradation | Plugin failure không ảnh hưởng toàn bộ hệ thống |
| NFR-AVL-002 | Health Checks | Backend health endpoints |
| NFR-AVL-003 | Database Failover | Hỗ trợ PostgreSQL replication |

### 4.5. Khả năng bảo trì (Maintainability)

| ID | Yêu cầu | Mô tả |
|----|----------|-------|
| NFR-MNT-001 | Code Quality | ESLint + Prettier + TypeScript strict |
| NFR-MNT-002 | API Stability | API Reports tự động với API Extractor |
| NFR-MNT-003 | Versioning | Semantic Versioning + Changesets |
| NFR-MNT-004 | Testing | Unit (Jest), E2E (Playwright), Visual (Storybook) |
| NFR-MNT-005 | Documentation | Inline TSDoc, Architecture Decision Records |
| NFR-MNT-006 | Monorepo | Yarn Workspaces cho dependency management |
| NFR-MNT-007 | Release Tags | Validate release tags cho API surfaces |

### 4.6. Khả năng tương tác (Compatibility)

| ID | Yêu cầu | Mô tả |
|----|----------|-------|
| NFR-CMP-001 | Browser Support | Chrome, Firefox, Safari (latest versions) |
| NFR-CMP-002 | Node.js | Version 22 hoặc 24 |
| NFR-CMP-003 | Database | PostgreSQL 17+ (prod), SQLite (dev) |
| NFR-CMP-004 | Container | Docker, Kubernetes |
| NFR-CMP-005 | OS | Linux, macOS (development) |

### 4.7. Observability

| ID | Yêu cầu | Mô tả |
|----|----------|-------|
| NFR-OBS-001 | Tracing | OpenTelemetry auto-instrumentation |
| NFR-OBS-002 | Metrics | Prometheus exporter (port 9090) |
| NFR-OBS-003 | Logging | Structured logging (JSON format) |
| NFR-OBS-004 | Rate Limiting | Configurable request rate limiting |

**Instrumentation configuration:**

```javascript
// packages/backend/src/instrumentation.js
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { PrometheusExporter } = require('@opentelemetry/exporter-prometheus');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
```

---

## 5. Yêu cầu giao diện (Interface Requirements)

### 5.1. User Interface (Frontend)

#### 5.1.1. Navigation Structure

```
┌─────────────────────────────────────────┐
│ Sidebar (Left)                          │
│ ┌─────────────────────┐                 │
│ │ Home                │                 │
│ │ Catalog             │                 │
│ │ API Docs            │                 │
│ │ TechDocs            │                 │
│ │ Templates           │                 │
│ │ Search              │                 │
│ │ Kubernetes          │                 │
│ │ Notifications       │                 │
│ │ DevTools            │                 │
│ │ Settings            │                 │
│ └─────────────────────┘                 │
│                                         │
│ Main Content Area (Right)               │
│ ┌─────────────────────────────────────┐ │
│ │ Header (Breadcrumb + Actions)       │ │
│ ├─────────────────────────────────────┤ │
│ │ Content (Dynamic per route)         │ │
│ │                                     │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

#### 5.1.2. Entity Page Layout

```
┌──────────────────────────────────────────┐
│ Entity Header (Name, Type, Owner, Links) │
├──────────────────────────────────────────┤
│ Tab Navigation                           │
│ [Overview][Docs][APIs][Kubernetes][...]   │
├──────────────────────────────────────────┤
│ Tab Content                              │
│ ┌──────────────┐ ┌────────────────────┐  │
│ │ About Card   │ │ Relations Graph    │  │
│ └──────────────┘ └────────────────────┘  │
│ ┌──────────────┐ ┌────────────────────┐  │
│ │ Links Card   │ │ Has APIs Card      │  │
│ └──────────────┘ └────────────────────┘  │
└──────────────────────────────────────────┘
```

**Entity Page Groups (configurable):**

| Group | Title | Mô tả |
|-------|-------|-------|
| `overview` | Overview | Default tab, hiển thị tổng quan |
| `documentation` | Docs | TechDocs content |
| `deployment` | Deployments | Kubernetes workloads |
| `custom` | Custom | Custom content cards |

### 5.2. API Interface (Backend)

#### 5.2.1. API Base URLs

| Service | URL | Port |
|---------|-----|------|
| Frontend (dev) | `http://localhost:3000` | 3000 |
| Backend | `http://localhost:7007` | 7007 |

#### 5.2.2. API Authentication

- Service-to-service: Bearer token (JWT)
- User requests: Cookie-based session hoặc Bearer token
- Development: `dangerouslyDisableDefaultAuthPolicy: true`

#### 5.2.3. API Error Handling

```typescript
// Sử dụng @backstage/errors
import { NotFoundError, InputError } from '@backstage/errors';

// Throw errors, middleware sẽ convert sang JSON response
throw new NotFoundError(`Entity not found: ${entityRef}`);
throw new InputError(`Invalid id: '${req.params.id}'`);
```

### 5.3. External Interfaces

#### 5.3.1. SCM Integrations

```yaml
integrations:
  github:
    - host: github.com
      token: ${GITHUB_TOKEN}
  gitlab:
    - host: gitlab.com
      token: ${GITLAB_TOKEN}
  azure:
    - host: dev.azure.com
      token: ${AZURE_TOKEN}
  awsS3:
    - endpoint: ${AWS_S3_ENDPOINT}
      accessKeyId: ${AWS_ACCESS_KEY_ID}
      secretAccessKey: ${AWS_SECRET_ACCESS_KEY}
```

#### 5.3.2. Database Interface

```yaml
# Development
backend:
  database:
    client: better-sqlite3
    connection: ':memory:'

# Production (Docker)
backend:
  database:
    client: pg
    connection:
      host: localhost
      port: 5432
      user: postgres
      password: postgres
```

#### 5.3.3. Cache Interface

```yaml
backend:
  cache:
    store: redis
    connection: redis://localhost:6379
```

---

## 6. Configuration System

### 6.1. Configuration Files

| File | Mô tả | Priority |
|------|--------|----------|
| `app-config.yaml` | Default configuration | Base |
| `app-config.local.yaml` | Local overrides (git-ignored) | Override |
| `app-config.docker.yaml` | Docker environment config | Conditional |
| `app-config.production.yaml` | Production config | Conditional |

### 6.2. Environment Variables

- Format: `${ENV_VAR_NAME}`
- Hỗ trợ trong tất cả config files
- Secrets bắt buộc dùng environment variables

### 6.3. Configuration Schema

- Plugins định nghĩa configuration schema
- Validation tự động khi startup
- `@backstage/plugin-config-schema` để inspect full schema

### 6.4. App Extensions Configuration

```yaml
app:
  extensions:
    - entity-card:catalog/about:
        config:
          type: info
    - page:catalog:
        config:
          exportSettings:
            enabled: true
    - api:app/app-language:
        config:
          availableLanguages: ['en', 'es', 'fr', 'de', 'ja']
          defaultLanguage: 'en'
```

---

## 7. Deployment Requirements

### 7.1. Docker Deployment

**Dockerfile (multi-stage build):**

| Stage | Base Image | Mô tả |
|-------|-----------|-------|
| Production | `node:24-trixie-slim` | Slim image cho production |

**Build steps:**
1. `yarn install`
2. `yarn tsc`
3. `yarn build:backend`
4. Docker build từ `packages/backend/Dockerfile`

**Container configuration:**
- User: `node` (non-root)
- Working directory: `/app`
- NODE_ENV: `production`
- Entry point: `node packages/backend --config app-config.yaml`

### 7.2. Docker Compose Dependencies

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| PostgreSQL | `postgres:17.9` | 5432 | Primary database |
| Redis | `redis:8.2.1-alpine` | 6379 | Caching |
| OpenSearch | `opensearchproject/opensearch:2.19.5` | 9200, 9600 | Full-text search |

### 7.3. Kubernetes Deployment

- Hỗ trợ deployment trên Kubernetes
- Horizontal Pod Autoscaler (HPA) cho backend
- Persistent Volume Claims (PVC) cho local TechDocs storage
- ConfigMaps/Secrets cho configuration

---

## 8. Testing Requirements

### 8.1. Unit Testing

| Aspect | Requirement |
|--------|-------------|
| **Framework** | Jest 30 |
| **VM** | `--experimental-vm-modules` flag |
| **Coverage** | Codecov integration |
| **Mocking** | MSW (Mock Service Worker) cho network requests (ADR007) |
| **Network** | `rejectFrontendNetworkRequests: true` (block real network in tests) |
| **Snapshot** | `--no-node-snapshot` flag |

### 8.2. End-to-End Testing

| Aspect | Requirement |
|--------|-------------|
| **Framework** | Playwright |
| **Configuration** | `playwright.config.ts` |
| **Scope** | Critical user flows (catalog, search, scaffolder) |

### 8.3. Visual Testing

| Aspect | Requirement |
|--------|-------------|
| **Framework** | Storybook 10 |
| **Hosting** | Local (port 6006) và Chromatic |
| **Accessibility** | `@storybook/addon-a11y` |

### 8.4. API Testing

| Aspect | Requirement |
|--------|-------------|
| **API Reports** | API Extractor cho type-checking public APIs |
| **Build command** | `yarn build:api-reports` |
| **Validation** | `--validate-release-tags` |

### 8.5. Lighthouse Audits

| Aspect | Requirement |
|--------|-------------|
| **Configuration** | `lighthouserc.js` |
| **CI Integration** | `.lighthouseci` directory |
| **Metrics** | Performance, Accessibility, Best Practices, SEO |

---

## 9. Build & Release System

### 9.1. Build Pipeline

```
yarn install          → Fetch dependencies (Yarn Berry)
yarn tsc              → TypeScript compilation
yarn build:all        → Build all packages
yarn build:backend    → Build backend bundle
yarn build:api-reports → Generate API Reports
yarn lint:all         → ESLint + code quality
yarn test:all         → Full test suite
yarn build-storybook  → Build Storybook
```

### 9.2. Release Process

| Step | Tool | Mô tả |
|------|------|-------|
| 1. Changeset | `@changesets/cli` | Ghi nhận thay đổi |
| 2. Version bump | `changeset version` | Bump version theo semver |
| 3. CHANGELOG | Auto-generated | Tạo CHANGELOG.md entries |
| 4. NPM Publish | Yarn publish | Publish packages lên NPM |
| 5. Git Tag | Auto | Tag release version |

### 9.3. Monorepo Management

| Tool | Mục đích |
|------|----------|
| **Yarn Workspaces** | Dependency management |
| **workspace:^** | Internal package references |
| **backstage-cli** | Build, test, lint commands |
| **backstage-repo-tools** | API reports, catalog info generation |
| **Changesets** | Version management |
| **Husky** | Git hooks (pre-commit) |
| **lint-staged** | Run lint on staged files only |

---

## 10. Traceability Matrix

| User Requirement | Functional Requirement | Module |
|------------------|----------------------|--------|
| UR-CAT-001 | FR-CAT-004, FR-CAT-005 | Catalog |
| UR-CAT-002 | FR-CAT-001 | Catalog |
| UR-CAT-003 | FR-CAT-005 | Catalog |
| UR-CAT-004 | FR-CAT-004, FR-CAT-005 | Catalog |
| UR-CAT-005 | FR-CAT-002, FR-CAT-003 | Catalog |
| UR-TPL-001 | FR-TPL-001, FR-TPL-003 | Scaffolder |
| UR-TPL-002 | FR-TPL-003 | Scaffolder |
| UR-TPL-003 | FR-TPL-002 | Scaffolder |
| UR-DOC-001 | FR-DOC-003 | TechDocs |
| UR-DOC-002 | FR-DOC-001 | TechDocs |
| UR-DOC-003 | FR-DOC-002 | TechDocs |
| UR-SRC-001 | FR-SRC-001, FR-SRC-002, FR-SRC-003 | Search |
| UR-SRC-002 | FR-SRC-001 | Search |
| UR-AUTH-001 | FR-AUTH-001, FR-AUTH-002, FR-AUTH-003 | Auth |
| UR-AUTH-002 | FR-PERM-001, FR-PERM-002 | Permission |
| UR-AUTH-003 | FR-AUTH-002 | Auth |
| UR-K8S-001 | FR-K8S-001, FR-K8S-002 | Kubernetes |
| UR-NTF-001 | FR-NTF-001 | Notifications |
| UR-API-001 | FR-API-001, FR-API-002 | API Docs |

---

## 11. Phụ lục

### 11.1. Architecture Decision Records (ADRs)

| ADR | Tiêu đề | Quyết định |
|-----|---------|-----------|
| ADR001 | ADR Log | Sử dụng ADR để ghi nhận quyết định kiến trúc |
| ADR002 | Catalog File Format | YAML descriptor format |
| ADR003 | Named Exports | Ưu tiên named exports, tránh default exports |
| ADR004 | Module Export Structure | Chuẩn hóa cấu trúc export cho packages |
| ADR005 | Catalog Core Entities | Định nghĩa entity types cốt lõi |
| ADR006 | Avoid React.FC | Không sử dụng React.FC/React.SFC |
| ADR007 | MSW for Mocking | Sử dụng Mock Service Worker cho test |
| ADR008 | Catalog File Name | `catalog-info.yaml` là tên file mặc định |
| ADR009 | Entity References | Format: `[<kind>:][<namespace>/]<name>` |
| ADR010 | Luxon Date Library | Sử dụng Luxon thay cho Moment.js |
| ADR011 | Plugin Package Structure | Chuẩn hóa cấu trúc package cho plugins |
| ADR012 | Luxon Locale | Sử dụng Luxon locale và date presets |
| ADR013 | node-fetch | Sử dụng node-fetch (deprecated) |
| ADR014 | Fetch API | Chuyển sang native fetch API |

### 11.2. Glossary

| Thuật ngữ | Định nghĩa |
|-----------|-----------|
| **Backstage** | Framework mã nguồn mở để xây dựng Developer Portal |
| **Plugin** | Module mở rộng cho Backstage (frontend, backend, hoặc cả hai) |
| **Entity** | Đơn vị trong Software Catalog |
| **Component** | Entity loại software component (service, website, library) |
| **System** | Tập hợp các entities liên quan tạo thành một hệ thống |
| **Domain** | Lĩnh vực kinh doanh chứa một hoặc nhiều systems |
| **Scaffolder** | Hệ thống tạo project từ templates |
| **TechDocs** | Hệ thống tài liệu kỹ thuật docs-as-code |
| **Collator** | Component thu thập dữ liệu cho Search index |
| **Extension** | Đơn vị UI mở rộng trong frontend plugin system |
| **Blueprint** | Factory pattern để tạo extensions |
