# Product Requirements Document (PRD)

## Backstage — Open Source Developer Portal

| Thông tin | Chi tiết |
|-----------|----------|
| **Dự án** | Backstage |
| **Phiên bản** | 1.51.0 |
| **License** | Apache License 2.0 |
| **Tổ chức** | CNCF (Cloud Native Computing Foundation) — Incubation Level |
| **Khởi tạo bởi** | Spotify |
| **Ngày tạo tài liệu** | 27/05/2026 |

---

## 1. Tổng quan sản phẩm

### 1.1. Giới thiệu

Backstage là một **framework mã nguồn mở** dùng để xây dựng **Developer Portal** (cổng thông tin cho nhà phát triển). Backstage cung cấp một nền tảng tập trung giúp tổ chức quản lý toàn bộ hạ tầng phần mềm, công cụ, dịch vụ và tài liệu kỹ thuật trong một giao diện duy nhất (single-pane-of-glass).

### 1.2. Tầm nhìn sản phẩm

> *"Kubernetes cho trải nghiệm phát triển phần mềm"* — Backstage hướng tới trở thành bộ công cụ tiêu chuẩn đáng tin cậy (UX layer) cho hệ sinh thái hạ tầng mã nguồn mở.

### 1.3. Vấn đề cần giải quyết

- **Sự phân mảnh công cụ**: Đội ngũ phát triển phải chuyển đổi giữa nhiều công cụ, dashboard, hệ thống khác nhau.
- **Thiếu tổng quan**: Không có cách nhìn toàn cảnh (holistic view) về toàn bộ hệ thống microservices, thư viện, pipeline, website.
- **Onboarding chậm**: Nhà phát triển mới mất nhiều thời gian để hiểu kiến trúc và quy trình.
- **Tài liệu rời rạc**: Tài liệu kỹ thuật nằm rải rác ở nhiều nơi, khó tìm kiếm và bảo trì.
- **Thiếu chuẩn hóa**: Mỗi đội tự chọn template và best practices riêng, gây ra sự không nhất quán.

---

## 2. Các tính năng chính (Core Features)

### 2.1. Software Catalog

| Thuộc tính | Mô tả |
|------------|-------|
| **Mục đích** | Quản lý tập trung toàn bộ phần mềm: microservices, thư viện, data pipelines, websites, ML models |
| **Định dạng** | YAML descriptor (`catalog-info.yaml`) |
| **Entity Types** | Component, API, Resource, System, Domain, Location, User, Group, Template, AiResource |
| **Khả năng mở rộng** | Hỗ trợ extending model với custom entity types |

**Các tính năng con:**
- Đăng ký và quản lý component qua file YAML
- Hiển thị quan hệ giữa các entity (relations graph)
- Import tự động từ SCM providers (GitHub, GitLab, Bitbucket, Azure DevOps, Gerrit, Gitea)
- Tìm kiếm và lọc catalog theo nhiều tiêu chí
- Export dữ liệu catalog
- Well-known annotations, relations và statuses

### 2.2. Software Templates (Scaffolder)

| Thuộc tính | Mô tả |
|------------|-------|
| **Mục đích** | Tạo nhanh dự án mới từ template chuẩn hóa |
| **Template Engine** | Nunjucks với custom filters |
| **Built-in Actions** | Tích hợp sẵn nhiều actions cho GitHub, GitLab, Bitbucket, Azure, GCP |

**Các tính năng con:**
- Wizard-based UI để tạo project mới
- Custom actions cho scaffolding pipeline
- Dry-run testing trước khi thực thi
- Audit trail cho task parameters
- Custom step layouts
- Nhóm templates theo danh mục (ví dụ: Services, Documentation)

### 2.3. TechDocs

| Thuộc tính | Mô tả |
|------------|-------|
| **Mục đích** | Hệ thống tài liệu kỹ thuật tích hợp theo phương pháp "docs-like-code" |
| **Công nghệ** | MkDocs với `mkdocs-techdocs-core` |
| **Build modes** | Local hoặc External (CI/CD) |
| **Storage** | Local, Google GCS, AWS S3, Azure Blob Storage, OpenStack Swift |

**Các tính năng con:**
- Tự động build tài liệu từ markdown trong repo
- Tìm kiếm nội dung tài liệu (full-text search)
- Extension system cho TechDocs (addons)
- Embedded trong entity page

### 2.4. Backstage Search

| Thuộc tính | Mô tả |
|------------|-------|
| **Mục đích** | Tìm kiếm toàn diện xuyên suốt developer portal |
| **Search Engines** | In-memory (mặc định), Elasticsearch, OpenSearch |
| **Collators** | Catalog, TechDocs, Explore, Stack Overflow |

**Các tính năng con:**
- Tìm kiếm catalog entities
- Tìm kiếm nội dung tài liệu TechDocs
- Extensible collator architecture
- Configurable search engine backend

### 2.5. Kubernetes Integration

| Thuộc tính | Mô tả |
|------------|-------|
| **Mục đích** | Hiển thị thông tin Kubernetes workloads liên quan đến từng service |
| **Tính năng** | Xem pods, deployments, services trực tiếp trong entity page |

### 2.6. Hệ thống Authentication

**Providers được hỗ trợ:**

| Provider | Loại |
|----------|------|
| GitHub | OAuth |
| GitLab | OAuth |
| Google | OAuth |
| Microsoft/Azure | OAuth |
| Okta | OAuth |
| Auth0 | OAuth |
| Bitbucket / Bitbucket Server | OAuth |
| Atlassian | OAuth |
| OneLogin | OAuth |
| OIDC (Generic) | OpenID Connect |
| SAML | SAML 2.0 |
| OAuth2 (Generic) | OAuth 2.0 |
| OAuth2 Proxy | Proxy |
| AWS ALB | AWS |
| GCP IAP | GCP |
| Cloudflare Access | Proxy |
| Azure EasyAuth | Azure |
| VMware Cloud | OAuth |
| OpenShift | OAuth |
| Pinniped | Kubernetes |
| Guest | Development |

### 2.7. Permission System

| Thuộc tính | Mô tả |
|------------|-------|
| **Mục đích** | Kiểm soát quyền truy cập (authorization) cho toàn bộ hệ thống |
| **Mô hình** | Plugin-based policy engine |
| **Mặc định** | Allow-all policy (development) |

### 2.8. Notifications

| Thuộc tính | Mô tả |
|------------|-------|
| **Mục đích** | Hệ thống thông báo cho người dùng |
| **Channels** | In-app, Email, Slack |
| **Extensibility** | Custom notification processors |

### 2.9. Signals (Real-time)

| Thuộc tính | Mô tả |
|------------|-------|
| **Mục đích** | Cung cấp real-time updates qua WebSocket |
| **Tích hợp** | Backend signals service, Frontend signals hooks |

### 2.10. Events System

| Thuộc tính | Mô tả |
|------------|-------|
| **Mục đích** | Hệ thống event-driven cho backend plugins |
| **Sources** | AWS SQS, Azure, Bitbucket, Gerrit, GitHub, GitLab, Google Pub/Sub, Kafka |

### 2.11. DevTools

| Thuộc tính | Mô tả |
|------------|-------|
| **Mục đích** | Công cụ quản trị và debug cho Backstage instance |
| **Tính năng** | Xem scheduled tasks, configuration info |

### 2.12. MCP Actions

| Thuộc tính | Mô tả |
|------------|-------|
| **Mục đích** | Tích hợp Model Context Protocol cho AI-driven actions |
| **Plugin** | `@backstage/plugin-mcp-actions-backend` |

---

## 3. Kiến trúc hệ thống

### 3.1. Tổng quan kiến trúc

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (React)                  │
│  ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌────────┐ │
│  │ Catalog │ │Scaffolder│ │ TechDocs  │ │ Search │ │
│  │  Plugin │ │  Plugin  │ │  Plugin   │ │ Plugin │ │
│  └─────────┘ └──────────┘ └───────────┘ └────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐           │
│  │  K8s     │ │   Auth   │ │Permissions│           │
│  │  Plugin  │ │  Plugin  │ │  Plugin   │           │
│  └──────────┘ └──────────┘ └───────────┘           │
├─────────────────────────────────────────────────────┤
│                Backend (Node.js)                    │
│  ┌─────────────────────────────────────────────┐    │
│  │         Backend Plugin API                   │    │
│  │  (createBackend / createBackendFeatureLoader)│    │
│  └─────────────────────────────────────────────┘    │
│  ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌────────┐ │
│  │Catalog  │ │Scaffolder│ │ TechDocs  │ │ Search │ │
│  │Backend  │ │ Backend  │ │  Backend  │ │Backend │ │
│  └─────────┘ └──────────┘ └───────────┘ └────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐           │
│  │  Auth    │ │Permission│ │  Events   │           │
│  │ Backend  │ │ Backend  │ │  Backend  │           │
│  └──────────┘ └──────────┘ └───────────┘           │
├─────────────────────────────────────────────────────┤
│              Infrastructure Layer                   │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐           │
│  │PostgreSQL│ │  Redis   │ │OpenSearch │           │
│  │/ SQLite  │ │ (Cache)  │ │(Search)   │           │
│  └──────────┘ └──────────┘ └───────────┘           │
└─────────────────────────────────────────────────────┘
```

### 3.2. Monorepo Structure

```
backstage/
├── packages/          # 69 core packages
│   ├── app/           # Frontend application (React)
│   ├── backend/       # Backend application (Node.js)
│   ├── cli/           # Backstage CLI tooling
│   ├── core-*/        # Core libraries (components, APIs)
│   ├── frontend-*/    # Frontend framework packages
│   ├── backend-*/     # Backend framework packages
│   ├── catalog-*/     # Catalog model & client
│   ├── config*/       # Configuration system
│   └── ...
├── plugins/           # 155 plugin directories
│   ├── catalog*/      # Software Catalog plugins
│   ├── scaffolder*/   # Software Templates plugins
│   ├── techdocs*/     # TechDocs plugins
│   ├── search*/       # Search plugins
│   ├── auth*/         # Authentication plugins
│   ├── kubernetes*/   # Kubernetes plugins
│   ├── permission*/   # Permission plugins
│   ├── notifications*/# Notification plugins
│   ├── events*/       # Events system plugins
│   └── ...
├── workspaces/        # Standalone workspaces
│   └── ui/            # UI workspace
└── microsite/         # Documentation website
```

### 3.3. Technology Stack

| Layer | Công nghệ |
|-------|-----------|
| **Frontend** | React 18, TypeScript 5.7, Material UI 4, React Router 6 |
| **Backend** | Node.js 22/24, TypeScript, Express.js |
| **Database** | PostgreSQL 17 (production), SQLite (development) |
| **Cache** | Redis 8.x |
| **Search** | OpenSearch 2.x / Elasticsearch |
| **Build** | Yarn 4.8 (Berry), Backstage CLI, Vite 7 |
| **Testing** | Jest 30, Playwright, Storybook 10 |
| **Observability** | OpenTelemetry, Prometheus |
| **Container** | Docker, Node 24 base image |
| **CI/CD** | GitHub Actions |
| **Linting** | ESLint, Prettier, Vale (docs) |

---

## 4. Tích hợp bên ngoài (Integrations)

### 4.1. Source Code Management

| Platform | Tính năng |
|----------|-----------|
| **GitHub** | Locations, Discovery, Org Data, GitHub Apps |
| **GitLab** | Locations, Discovery |
| **Bitbucket Cloud** | Locations, Discovery |
| **Bitbucket Server** | Locations, Discovery |
| **Azure DevOps** | Locations, Discovery, Org Data |
| **Gerrit** | Locations, Discovery |
| **Gitea** | Locations, Discovery |
| **AWS CodeCommit** | Locations |

### 4.2. Cloud Storage

| Provider | Tính năng |
|----------|-----------|
| **AWS S3** | TechDocs storage, Locations |
| **Google GCS** | TechDocs storage, Locations |
| **Azure Blob Storage** | TechDocs storage, Catalog provider |

### 4.3. Identity Providers

- LDAP (Microsoft Active Directory, OpenLDAP)
- Microsoft Graph API (Azure AD / Entra ID)

### 4.4. Monitoring & Observability

- PagerDuty (qua proxy)
- Datadog RUM
- OpenTelemetry (traces, metrics)
- Prometheus (metrics export)

---

## 5. Yêu cầu phi chức năng

### 5.1. Hiệu năng

- Frontend phải tải dưới 3 giây (First Contentful Paint)
- Backend API response time < 500ms cho 95th percentile
- Hỗ trợ scaling horizontal cho backend

### 5.2. Bảo mật

- Hỗ trợ đa dạng authentication providers
- Service-to-service authentication
- Permission-based authorization
- Content Security Policy (CSP) configuration
- CORS configuration
- Input validation chống path traversal (`resolveSafeChildPath`)
- Express response security (JSON-only responses)
- Vulnerability scanning với Snyk
- Security reporting qua HackerOne bug bounty

### 5.3. Khả năng mở rộng

- Plugin architecture cho cả frontend và backend
- Hệ sinh thái hơn 155 plugins nội bộ + community plugins
- Custom entity types cho Software Catalog
- Extensible search collators
- Module Federation support
- Dynamic feature loading

### 5.4. Khả năng triển khai

- Docker containerization
- Kubernetes deployment
- Multi-environment configuration (development, staging, production)
- Infrastructure dependencies: PostgreSQL, Redis, OpenSearch

### 5.5. Khả năng bảo trì

- Monorepo architecture với Yarn Workspaces
- Changeset-based release management
- API Reports tự động với API Extractor
- Semantic Versioning
- TypeScript strict mode
- Comprehensive test suite (Jest, Playwright, Storybook)

---

## 6. Đối tượng người dùng

| Vai trò | Mô tả |
|---------|-------|
| **Software Developer** | Sử dụng portal hàng ngày để tra cứu services, tạo project mới, đọc tài liệu |
| **Platform Engineer** | Quản trị Backstage instance, cấu hình plugins, tích hợp hệ thống |
| **Engineering Manager** | Xem tổng quan ownership, theo dõi catalog, đánh giá tech health |
| **DevOps Engineer** | Tích hợp CI/CD, monitoring Kubernetes, quản lý infrastructure |
| **Technical Writer** | Viết và quản lý tài liệu kỹ thuật qua TechDocs |

---

## 7. Metrics & KPIs

| Metric | Mô tả |
|--------|-------|
| **Catalog Coverage** | % services/components được đăng ký trong catalog |
| **Template Usage** | Số lượng project được tạo từ templates/tháng |
| **TechDocs Adoption** | % entities có tài liệu TechDocs |
| **Search Usage** | Số lượng search queries/ngày |
| **Developer Satisfaction** | NPS score từ internal survey |
| **Onboarding Time** | Thời gian trung bình để developer mới bắt đầu productive |

---

## 8. Roadmap tham khảo

Thông tin roadmap chi tiết được cập nhật tại: [https://backstage.io/docs/overview/roadmap](https://backstage.io/docs/overview/roadmap)

---

## 9. Phụ lục

### 9.1. Tài liệu tham khảo

- [Backstage Official Documentation](https://backstage.io/docs)
- [GitHub Repository](https://github.com/backstage/backstage)
- [CNCF Project Page](https://www.cncf.io/projects)
- [Backstage Community](https://github.com/backstage/community)
- [Plugin Marketplace](https://backstage.io/plugins)
- [Architecture Decision Records (ADRs)](https://backstage.io/docs/architecture-decisions/)
