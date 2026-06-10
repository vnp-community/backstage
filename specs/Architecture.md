# System Architecture Document

## Backstage — Open Source Developer Portal

| Thông tin | Chi tiết |
|-----------|----------|
| **Dự án** | Backstage |
| **Phiên bản** | 1.51.0 |
| **Ngày tạo tài liệu** | 27/05/2026 |
| **Tham chiếu** | Phân tích từ source code thực tế |

---

## 1. Tổng quan kiến trúc

### 1.1. Triết lý kiến trúc

Backstage được thiết kế theo mô hình **Plugin-First Architecture** — toàn bộ chức năng (bao gồm cả core features) được triển khai dưới dạng plugins. Framework cung cấp hệ thống **wiring** (kết nối) và **services** (dịch vụ) để plugins hoạt động trong một môi trường thống nhất.

**Các nguyên tắc kiến trúc chính:**

1. **Plugin Isolation**: Mỗi plugin là một đơn vị độc lập, có thể thêm/bớt mà không ảnh hưởng hệ thống
2. **Service Injection**: Dependencies được inject thông qua hệ thống `ServiceRef` / `ServiceFactory`
3. **Extension Points**: Plugins mở rộng nhau qua `ExtensionPoint` (backend) và `Extension` (frontend)
4. **Configuration-Driven**: Hành vi hệ thống được điều khiển qua YAML configuration
5. **Monorepo**: Toàn bộ core packages và plugins nằm trong một monorepo duy nhất

### 1.2. Kiến trúc tổng thể (High-Level Architecture)

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                   Browser (React SPA)                      │  │
│  │  ┌─────────────┐  ┌───────────────┐  ┌─────────────────┐  │  │
│  │  │ App Shell   │  │ Plugin UIs    │  │ Extension       │  │  │
│  │  │ (Router,    │  │ (Catalog,     │  │ System          │  │  │
│  │  │  Theme,     │  │  Scaffolder,  │  │ (Blueprints,    │  │  │
│  │  │  Nav)       │  │  TechDocs...) │  │  Modules)       │  │  │
│  │  └──────┬──────┘  └───────┬───────┘  └────────┬────────┘  │  │
│  │         └─────────────────┴───────────────────┘            │  │
│  │                    Frontend Plugin API                      │  │
│  │              createFrontendPlugin / createApp               │  │
│  └────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│                      API GATEWAY LAYER                           │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              HTTP / WebSocket (Express.js)                 │  │
│  │    Port 7007  ─── CORS ─── CSP ─── Auth Middleware         │  │
│  │    ┌──────────────────────────────────────────────────┐    │  │
│  │    │           Root HTTP Router Service               │    │  │
│  │    │   /api/{pluginId}/* → Plugin HTTP Router         │    │  │
│  │    └──────────────────────────────────────────────────┘    │  │
│  └────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│                     APPLICATION LAYER                            │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Backend Plugin System                         │  │
│  │  ┌───────────────────────────────────────────────────┐    │  │
│  │  │        BackendInitializer (Orchestrator)          │    │  │
│  │  │  ┌──────────────┐  ┌──────────────────────────┐   │    │  │
│  │  │  │ ServiceReg-  │  │ Feature Loader           │   │    │  │
│  │  │  │ istry        │  │ (Lazy plugin loading)    │   │    │  │
│  │  │  └──────────────┘  └──────────────────────────┘   │    │  │
│  │  └───────────────────────────────────────────────────┘    │  │
│  │                                                            │  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐  │  │
│  │  │Cata- │ │Scaf- │ │Tech- │ │Search│ │Auth  │ │Perm- │  │  │
│  │  │log   │ │folder│ │Docs  │ │      │ │      │ │ission│  │  │
│  │  │Plugin│ │Plugin│ │Plugin│ │Plugin│ │Plugin│ │Plugin│  │  │
│  │  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘  │  │
│  │     │        │        │        │        │        │        │  │
│  │  ┌──┴────────┴────────┴────────┴────────┴────────┴──┐    │  │
│  │  │           Core Services (coreServices)           │    │  │
│  │  │  auth · database · cache · logger · scheduler    │    │  │
│  │  │  httpRouter · httpAuth · discovery · permissions │    │  │
│  │  │  lifecycle · urlReader · auditor · config        │    │  │
│  │  └──────────────────────────────────────────────────┘    │  │
│  └────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│                    INFRASTRUCTURE LAYER                           │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌─────────────┐    │
│  │PostgreSQL│  │  Redis   │  │ OpenSearch │  │ File System │    │
│  │ (Knex)   │  │ (Cache)  │  │ (Search)  │  │ (TechDocs)  │    │
│  └──────────┘  └──────────┘  └───────────┘  └─────────────┘    │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐                     │
│  │  GitHub  │  │  GitLab  │  │   Cloud   │                     │
│  │   API    │  │   API    │  │  Storage  │                     │
│  └──────────┘  └──────────┘  └───────────┘                     │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Backend Architecture

### 2.1. Backend Bootstrap Flow

Backstage backend khởi động theo quy trình sau, được orchestrate bởi `BackendInitializer`:

```
createBackend()
    │
    ▼
BackstageBackend
    │
    ├── backend.add(plugin)      // Đăng ký plugins
    ├── backend.add(module)      // Đăng ký modules
    ├── backend.add(loader)      // Đăng ký feature loaders
    ├── backend.add(factory)     // Đăng ký service factories
    │
    ▼
backend.start()
    │
    ▼
BackendInitializer
    │
    ├── 1. Load configuration (app-config.yaml)
    ├── 2. Initialize ServiceRegistry
    │      ├── Register root services (config, logger, httpRouter, lifecycle)
    │      └── Register plugin services (auth, database, cache, etc.)
    ├── 3. Resolve Feature Loaders
    │      └── Execute loader functions with root service deps
    ├── 4. Collect all registrations
    │      ├── plugin-v1.1 registrations
    │      └── module-v1.1 registrations
    ├── 5. Initialize Extension Points
    │      └── Match modules → plugins via pluginId
    ├── 6. Resolve & inject dependencies (DI)
    ├── 7. Run init() for each plugin/module
    ├── 8. Start HTTP server (port 7007)
    └── 9. Run lifecycle startup hooks
```

**Source code reference:**
- `BackstageBackend` → `packages/backend-app-api/src/wiring/BackstageBackend.ts`
- `BackendInitializer` → `packages/backend-app-api/src/wiring/BackendInitializer.ts`
- `ServiceRegistry` → `packages/backend-app-api/src/wiring/ServiceRegistry.ts`

### 2.2. Service Architecture (Dependency Injection)

Backstage sử dụng hệ thống **Dependency Injection** tự phát triển dựa trên `ServiceRef` và `ServiceFactory`.

#### 2.2.1. Service Scopes

```
┌─────────────────────────────────────────────┐
│              Root Services                   │
│   (Singleton cho toàn bộ backend)           │
│                                             │
│   rootConfig    rootLogger    rootLifecycle  │
│   rootHttpRouter   rootHealth               │
│   rootInstanceMetadata                      │
└─────────────────────┬───────────────────────┘
                      │ shared across
┌─────────────────────▼───────────────────────┐
│           Plugin Services                    │
│   (Instance riêng cho mỗi plugin)           │
│                                             │
│   auth        database      cache           │
│   logger      httpRouter    httpAuth        │
│   discovery   permissions   scheduler       │
│   lifecycle   urlReader     auditor         │
│   pluginMetadata   permissionsRegistry      │
│   userInfo                                  │
└─────────────────────────────────────────────┘
```

#### 2.2.2. Service Resolution Pattern

```typescript
// 1. Định nghĩa ServiceRef (interface contract)
const myServiceRef = createServiceRef<MyService>({
  id: 'my.service',
  scope: 'plugin',       // 'root' | 'plugin'
  // multiton: false     // 'singleton' (default) | 'multiton'
});

// 2. Triển khai ServiceFactory
const myServiceFactory = createServiceFactory({
  service: myServiceRef,
  deps: {
    config: coreServices.rootConfig,
    logger: coreServices.logger,
  },
  factory({ config, logger }) {
    return new MyServiceImpl(config, logger);
  },
});

// 3. Sử dụng trong plugin
createBackendPlugin({
  pluginId: 'my-plugin',
  register(reg) {
    reg.registerInit({
      deps: {
        myService: myServiceRef,
        httpRouter: coreServices.httpRouter,
      },
      async init({ myService, httpRouter }) {
        // Plugin initialization with injected services
      },
    });
  },
});
```

#### 2.2.3. Core Services Registry

| Service Ref | Scope | Type | Mô tả |
|-------------|-------|------|--------|
| `coreServices.rootConfig` | root | singleton | Configuration (Config interface) |
| `coreServices.rootLogger` | root | singleton | Root logger |
| `coreServices.rootHttpRouter` | root | singleton | Express root router |
| `coreServices.rootLifecycle` | root | singleton | App lifecycle hooks |
| `coreServices.rootHealth` | root | singleton | Health check endpoints |
| `coreServices.rootInstanceMetadata` | root | singleton | Installed plugins metadata |
| `coreServices.auth` | plugin | singleton | Authentication service |
| `coreServices.httpAuth` | plugin | singleton | HTTP request authentication |
| `coreServices.database` | plugin | singleton | Database (Knex) per-plugin |
| `coreServices.cache` | plugin | singleton | Cache (Redis) per-plugin |
| `coreServices.logger` | plugin | singleton | Logger per-plugin (child of root) |
| `coreServices.httpRouter` | plugin | singleton | HTTP router per-plugin |
| `coreServices.discovery` | plugin | singleton | Service discovery |
| `coreServices.permissions` | plugin | singleton | Permission evaluation |
| `coreServices.permissionsRegistry` | plugin | singleton | Permission rules registry |
| `coreServices.scheduler` | plugin | singleton | Task scheduling |
| `coreServices.lifecycle` | plugin | singleton | Plugin lifecycle hooks |
| `coreServices.urlReader` | plugin | singleton | URL content reader |
| `coreServices.auditor` | plugin | singleton | Audit logging |
| `coreServices.userInfo` | plugin | singleton | User info retrieval |
| `coreServices.pluginMetadata` | plugin | singleton | Plugin metadata |

### 2.3. Plugin Architecture (Backend)

#### 2.3.1. Plugin ↔ Module Relationship

```
┌──────────────────────────────────────────────┐
│           Backend Plugin (plugin-v1.1)       │
│  pluginId: "catalog"                         │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │      Extension Points               │    │
│  │  ┌────────────────────────────────┐  │    │
│  │  │ catalogProcessingExtension-    │  │    │
│  │  │ Point                          │  │    │
│  │  │  - addProcessor()             │  │    │
│  │  │  - addEntityProvider()        │  │    │
│  │  └────────────────────────────────┘  │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  registerInit({                              │
│    deps: { database, httpRouter, ... },      │
│    init: async ({ database, httpRouter }) => │
│      { /* setup routes, start processing */ }│
│  })                                          │
└──────────────────┬───────────────────────────┘
                   │ extends via pluginId match
    ┌──────────────┼──────────────────┐
    ▼              ▼                  ▼
┌────────┐  ┌──────────┐  ┌──────────────────┐
│Module  │  │Module    │  │Module            │
│github  │  │gitlab   │  │unprocessed       │
│        │  │         │  │                  │
│register│  │register │  │register          │
│Init({  │  │Init({   │  │Init({            │
│ deps:{ │  │ deps:{  │  │ deps:{           │
│  ext,  │  │  ext,   │  │  ext,            │
│  ...   │  │  ...    │  │  ...             │
│ },     │  │ },      │  │ },               │
│ init:  │  │ init:   │  │ init:            │
│ ext.add│  │ ext.add │  │ ext.addProcessor │
│ Entity │  │ Entity  │  │                  │
│Provider│  │Provider │  │                  │
│})      │  │})       │  │})                │
└────────┘  └──────────┘  └──────────────────┘
```

#### 2.3.2. Plugin Registration Types

```typescript
// Registration type discriminator
type InternalBackendRegistrations = {
  $$type: '@backstage/BackendFeature';
  version: 'v1';
  featureType: 'registrations';
  getRegistrations(): Array<
    | { type: 'plugin-v1.1'; pluginId: string; ... }
    | { type: 'module-v1.1'; pluginId: string; moduleId: string; ... }
  >;
};
```

### 2.4. HTTP Routing Architecture

```
                    Express Application
                          │
              ┌───────────┴───────────┐
              │   Root HTTP Router    │
              │   (rootHttpRouter)    │
              └───────────┬───────────┘
                          │
    ┌─────────────────────┼──────────────────────┐
    │                     │                      │
    ▼                     ▼                      ▼
/api/catalog/*      /api/scaffolder/*      /api/auth/*
    │                     │                      │
Plugin httpRouter   Plugin httpRouter     Plugin httpRouter
    │                     │                      │
    ├── Auth Policy       ├── Auth Policy        ├── Auth Policy
    │   (allow/deny)      │   (allow/deny)       │   (unauthenticated)
    │                     │                      │
    └── Express           └── Express            └── Express
        Handlers              Handlers               Handlers
```

**Auth Policy cho routes:**

```typescript
httpRouter.addAuthPolicy({
  path: '/health',
  allow: 'unauthenticated',      // Public endpoint
});

httpRouter.addAuthPolicy({
  path: '/static',
  allow: 'user-cookie',          // Cookie-based auth
});
// Tất cả routes khác yêu cầu Bearer token (default)
```

### 2.5. Authentication Architecture

```
┌──────────┐    ┌────────────┐    ┌──────────────┐    ┌─────────┐
│ Browser  │───▶│ Frontend   │───▶│ Auth Backend │───▶│  IdP    │
│          │    │ /api/auth  │    │ Plugin       │    │ (OAuth) │
└──────────┘    └────────────┘    └──────┬───────┘    └─────────┘
                                        │
                                        ▼
                              ┌──────────────────┐
                              │  Sign-in Resolver │
                              │  (maps IdP user   │
                              │   to Backstage    │
                              │   identity)       │
                              └────────┬─────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │  Backstage Token │
                              │  (JWT)           │
                              │                  │
                              │  Principal types:│
                              │  • user          │
                              │  • service       │
                              │  • none          │
                              └──────────────────┘
```

**Credential Types:**

| Principal Type | Mô tả | Use Case |
|---------------|--------|----------|
| `user` | Người dùng đã xác thực | Browser requests |
| `service` | Backend plugin-to-plugin | Inter-service calls |
| `none` | Không có identity | Unauthenticated endpoints |

**Service-to-Service Auth Flow:**

```typescript
// Plugin A gọi Plugin B
const { token } = await auth.getPluginRequestToken({
  onBehalfOf: credentials,     // User hoặc service credentials
  targetPluginId: 'catalog',   // Plugin đích
});

// Plugin B xác thực
const credentials = await httpAuth.credentials(req);
if (auth.isPrincipal(credentials, 'user')) {
  // Handle user request
}
```

### 2.6. Startup Resilience

```yaml
# config: backend.startup
backend:
  startup:
    default:
      onPluginBootFailure: 'abort'         # 'continue' | 'abort'
      onPluginModuleBootFailure: 'abort'
    plugins:
      catalog:
        onPluginBootFailure: 'abort'       # Critical plugin
        modules:
          github:
            onPluginModuleBootFailure: 'continue'  # Non-critical module
```

---

## 3. Frontend Architecture

### 3.1. Frontend Application Model

```
createApp({ features: [...] })
    │
    ▼
┌──────────────────────────────────────────────┐
│              App Shell                       │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │         Extension Tree                │  │
│  │                                        │  │
│  │  app/root                              │  │
│  │  ├── app/layout                        │  │
│  │  │   ├── app/nav                       │  │
│  │  │   └── app/routes                    │  │
│  │  │       ├── page:catalog              │  │
│  │  │       │   └── page:catalog/entity   │  │
│  │  │       │       ├── entity-content:*  │  │
│  │  │       │       └── entity-card:*     │  │
│  │  │       ├── page:scaffolder           │  │
│  │  │       ├── page:techdocs             │  │
│  │  │       ├── page:search               │  │
│  │  │       └── page:home                 │  │
│  │  ├── app/root-element:*                │  │
│  │  └── api:*                             │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

### 3.2. Extension System

#### 3.2.1. Extension ID Format

```
{kind}:{namespace}[/{name}]

Ví dụ:
  page:catalog                      → Catalog page
  page:catalog/entity               → Catalog entity detail page
  entity-card:catalog/about         → About card trên entity page
  entity-content:techdocs           → TechDocs content tab
  api:app/app-language              → Language API extension
  sub-page:scaffolder/templates     → Scaffolder templates sub-page
```

#### 3.2.2. Extension Blueprint Pattern

```
┌─────────────────────────────────────────────────────┐
│                ExtensionBlueprint                   │
│                                                     │
│  kind: "page"                                       │
│  attachTo: { id: "app/routes", input: "routes" }    │
│  output: [coreExtensionData.reactElement]            │
│  configSchema: { path: z.string() }                  │
│                                                     │
│  factory(params, { config, inputs }) {               │
│    yield coreExtensionData.reactElement(<Page/>)     │
│  }                                                   │
└─────────────────────┬───────────────────────────────┘
                      │ .make()
                      ▼
┌─────────────────────────────────────────────────────┐
│            ExtensionDefinition                      │
│                                                     │
│  id: "page:my-plugin"                               │
│  kind: "page"                                       │
│  namespace: "my-plugin"                              │
│  attachTo: { id: "app/routes", input: "routes" }    │
│  disabled: false                                     │
│  output: [...]                                       │
│  factory: (ctx) => [...]                             │
└─────────────────────────────────────────────────────┘
```

**Built-in Blueprints:**

| Blueprint | Kind | Attach To | Mô tả |
|-----------|------|-----------|--------|
| `PageBlueprint` | `page` | `app/routes` | Top-level pages |
| `SubPageBlueprint` | `sub-page` | Parent page | Sub-pages |
| `ApiBlueprint` | `api` | `app/apis` | API implementations |
| `AppRootElementBlueprint` | `app-root-element` | `app/root` | Root-level elements |
| `AnalyticsImplementationBlueprint` | `analytics-implementation` | `app/analytics` | Analytics |
| `PluginWrapperBlueprint` | `plugin-wrapper` | Plugin | Plugin wrappers |
| `PluginHeaderActionBlueprint` | `plugin-header-action` | Plugin header | Header actions |

#### 3.2.3. Plugin Creation & Override Pattern

```typescript
// 1. Tạo plugin
const myPlugin = createFrontendPlugin({
  pluginId: 'my-plugin',
  title: 'My Plugin',
  icon: MyIcon,
  extensions: [
    PageBlueprint.make({
      params: {
        defaultPath: '/my-plugin',
        loader: () => import('./MyPage'),
      },
    }),
  ],
  routes: { root: rootRouteRef },
  externalRoutes: { catalog: catalogRouteRef },
});

// 2. Override extensions
const customPlugin = myPlugin.withOverrides({
  title: 'Custom Title',
  extensions: [
    myPlugin.getExtension('page:my-plugin').override({
      params: { /* override params */ },
    }),
  ],
});

// 3. Tạo module (cross-plugin extension)
const myModule = createFrontendModule({
  pluginId: 'target-plugin',
  extensions: [/* additional extensions */],
});
```

### 3.3. Configuration-Driven UI

```yaml
app:
  extensions:
    # Enable/disable extensions
    - page:catalog-unprocessed-entities: false

    # Configure extension
    - entity-card:catalog/about:
        config:
          type: info

    # Configure page
    - page:catalog/entity:
        config:
          showNavItemIcons: true
          groups:
            - overview:
                title: Overview
            - documentation:
                title: Docs
                icon: docs
            - deployment:
                title: Deployments
            - custom:
                title: Custom
```

### 3.4. Legacy Compatibility Layer

```typescript
// Convert legacy plugins to new extension system
const convertedPlugin = convertLegacyPlugin(legacyPlugin, {
  extensions: [
    convertLegacyPageExtension(LegacyPage, {
      name: 'index',
      path: '/legacy-path',
    }),
    convertLegacyEntityContentExtension(LegacyEntityContent),
  ],
});

// Convert legacy app root
const collectedLegacyPlugins = convertLegacyAppRoot(
  <FlatRoutes>
    <Route path="/legacy" element={<LegacyPage />} />
  </FlatRoutes>,
);
```

---

## 4. Data Architecture

### 4.1. Entity Processing Pipeline (Catalog)

```
┌────────────────┐    ┌──────────────────┐    ┌────────────────┐
│ Entity         │    │ Processing       │    │ Database       │
│ Providers      │───▶│ Pipeline         │───▶│ (Entities)     │
│                │    │                  │    │                │
│ • GitHub       │    │ ┌──────────────┐ │    │ ┌────────────┐ │
│ • GitLab       │    │ │ 1. Fetch     │ │    │ │ entities   │ │
│ • Bitbucket    │    │ │ 2. Parse     │ │    │ │ relations  │ │
│ • Azure        │    │ │ 3. Validate  │ │    │ │ locations  │ │
│ • LDAP         │    │ │ 4. Process   │ │    │ │ search     │ │
│ • File         │    │ │ 5. Emit      │ │    │ └────────────┘ │
│ • URL          │    │ └──────────────┘ │    │                │
└────────────────┘    │                  │    └────────────────┘
                      │ ┌──────────────┐ │
                      │ │ Processors   │ │
                      │ │ (chain)      │ │
                      │ └──────────────┘ │
                      │                  │
                      │ ┌──────────────┐ │
                      │ │ Stitching    │ │
                      │ │ (merge       │ │
                      │ │  relations)  │ │
                      │ └──────────────┘ │
                      └──────────────────┘
```

**Catalog Backend Internal Structure:**

```
plugins/catalog-backend/src/
├── catalog/            # Core catalog logic
├── database/           # Database layer (Knex)
├── ingestion/          # Entity ingestion pipeline
├── model/              # Data models
├── permissions/        # Permission rules
├── processing/         # Entity processing engine
├── processors/         # Built-in processors
├── providers/          # Built-in entity providers
├── schema/             # JSON schemas
├── service/            # Business logic services
├── stitching/          # Entity stitching (relation merging)
└── util/               # Utilities
```

### 4.2. Database Architecture

```
┌──────────────────────────────────────────┐
│          Database Service                │
│                                          │
│  ServiceRef: coreServices.database       │
│  ORM: Knex.js                           │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │     Per-Plugin Database           │  │
│  │                                    │  │
│  │  Plugin "catalog" → schema/tables │  │
│  │  Plugin "search"  → schema/tables │  │
│  │  Plugin "auth"    → schema/tables │  │
│  │  Plugin "scaffolder" → schema/    │  │
│  │                        tables     │  │
│  └────────────────────────────────────┘  │
│                                          │
│  Clients:                                │
│  • better-sqlite3 (development)         │
│  • pg (PostgreSQL, production)          │
│                                          │
│  Features:                               │
│  • Auto-migration (skip option)         │
│  • Connection pooling                   │
│  • Conflict detection (isDatabaseConflictError) │
└──────────────────────────────────────────┘
```

### 4.3. Search Index Architecture

```
┌──────────────┐     ┌───────────────┐     ┌────────────────┐
│  Collators    │     │ Index Builder │     │ Search Engine  │
│              │     │               │     │                │
│ ┌──────────┐ │     │ Scheduler     │     │ ┌────────────┐ │
│ │ Catalog  │─┼────▶│ runs colators │────▶│ │ In-memory  │ │
│ │ Collator │ │     │ periodically  │     │ │ (default)  │ │
│ └──────────┘ │     │               │     │ └────────────┘ │
│ ┌──────────┐ │     │ Transforms    │     │ ┌────────────┐ │
│ │ TechDocs │─┼────▶│ documents for │────▶│ │ OpenSearch │ │
│ │ Collator │ │     │ indexing      │     │ │            │ │
│ └──────────┘ │     │               │     │ └────────────┘ │
│ ┌──────────┐ │     │               │     │ ┌────────────┐ │
│ │ Explore  │─┼────▶│               │────▶│ │ Elastic-   │ │
│ │ Collator │ │     │               │     │ │ search     │ │
│ └──────────┘ │     │               │     │ └────────────┘ │
└──────────────┘     └───────────────┘     └────────┬───────┘
                                                    │
                                           ┌────────▼───────┐
                                           │  Search API    │
                                           │  /api/search   │
                                           │  /query        │
                                           └────────────────┘
```

### 4.4. Caching Architecture

```
┌──────────────────────────────────┐
│         Cache Service            │
│                                  │
│  Interface: CacheService         │
│  Operations:                     │
│  • get<T>(key) → T | undefined  │
│  • set(key, value, { ttl })     │
│  • delete(key)                  │
│  • withOptions({ defaultTtl })  │
│                                  │
│  Backends:                       │
│  • memory (default, dev)        │
│  • redis (production)           │
│                                  │
│  Scoping:                        │
│  • Per-plugin namespace          │
│  • Configurable TTL             │
│  • JSON serializable values     │
└──────────────────────────────────┘
```

---

## 5. Events & Signals Architecture

### 5.1. Events System (Backend)

```
┌──────────────────────────────────────────────┐
│              Events Backend                  │
│                                              │
│  ┌─────────────────────────────────────┐    │
│  │          Event Bus                  │    │
│  │                                     │    │
│  │  publish(topic, event)              │    │
│  │  subscribe(topic, handler)          │    │
│  └────────────────┬────────────────────┘    │
│                   │                          │
│    ┌──────────────┼──────────────────┐      │
│    ▼              ▼                  ▼      │
│ ┌────────┐  ┌──────────┐  ┌──────────────┐ │
│ │GitHub  │  │GitLab    │  │Google PubSub │ │
│ │Webhook │  │Webhook   │  │Subscription  │ │
│ │Module  │  │Module    │  │Module        │ │
│ └────────┘  └──────────┘  └──────────────┘ │
│ ┌────────┐  ┌──────────┐  ┌──────────────┐ │
│ │AWS SQS │  │Azure     │  │Kafka         │ │
│ │Module  │  │Module    │  │Module        │ │
│ └────────┘  └──────────┘  └──────────────┘ │
└──────────────────────────────────────────────┘
```

### 5.2. Signals System (Real-time)

```
┌──────────┐     WebSocket      ┌──────────────────┐
│ Browser  │◀──────────────────▶│ Signals Backend  │
│ (React)  │                    │                  │
│          │  subscribe(topic)  │  publish(topic,  │
│ useSignal│  ────────────────▶ │    payload)      │
│ Hook     │  event data        │                  │
│          │  ◀──────────────── │  Other plugins   │
└──────────┘                    │  can publish     │
                                │  signals         │
                                └──────────────────┘
```

---

## 6. Permission Architecture

```
┌──────────────────────────────────────────────────┐
│              Permission System                    │
│                                                  │
│  ┌──────────────┐     ┌───────────────────────┐  │
│  │ Permission   │     │ Permission Backend    │  │
│  │ Service      │────▶│                       │  │
│  │ (per-plugin) │     │ ┌───────────────────┐ │  │
│  │              │     │ │  Policy Engine     │ │  │
│  │ authorize()  │     │ │                   │ │  │
│  │ authorize-   │     │ │  ┌─────────────┐  │ │  │
│  │ Conditional()│     │ │  │Allow-All    │  │ │  │
│  └──────────────┘     │ │  │Policy       │  │ │  │
│                       │ │  │(default)    │  │ │  │
│  ┌──────────────┐     │ │  └─────────────┘  │ │  │
│  │ Permissions  │     │ │  ┌─────────────┐  │ │  │
│  │ Registry     │     │ │  │Custom       │  │ │  │
│  │              │     │ │  │Policy       │  │ │  │
│  │ addPermission│     │ │  │(pluggable)  │  │ │  │
│  │ addRules()   │     │ │  └─────────────┘  │ │  │
│  │ addResource  │     │ └───────────────────┘ │  │
│  │ Type()       │     └───────────────────────┘  │
│  └──────────────┘                                │
│                                                  │
│  Flow:                                           │
│  Request → Credentials → Permission Check →      │
│  Policy Evaluation → ALLOW/DENY                  │
└──────────────────────────────────────────────────┘
```

---

## 7. Deployment Architecture

### 7.1. Docker Deployment

```
┌──────────────────────────────────────────────────┐
│                Docker Host                        │
│                                                  │
│  ┌──────────────────────────────────────────┐    │
│  │ backstage-backend                        │    │
│  │ (node:24-trixie-slim)                    │    │
│  │                                          │    │
│  │ User: node (non-root)                    │    │
│  │ Workdir: /app                            │    │
│  │ Entry: node packages/backend             │    │
│  │         --config app-config.yaml         │    │
│  │                                          │    │
│  │ Exposed: Port 7007                       │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │PostgreSQL│  │  Redis   │  │  OpenSearch   │  │
│  │ :5432    │  │  :6379   │  │  :9200/:9600  │  │
│  │ v17.9    │  │ v8.2.1   │  │  v2.19.5     │  │
│  └──────────┘  └──────────┘  └───────────────┘  │
└──────────────────────────────────────────────────┘
```

### 7.2. Docker Build Pipeline

```
yarn install
    │
    ▼
yarn tsc                   (TypeScript compilation)
    │
    ▼
yarn build:backend         (Webpack bundling)
    │
    ├── dist/skeleton.tar.gz   (package.json files only)
    └── dist/bundle.tar.gz     (compiled source code)
    │
    ▼
docker build               (Multi-stage Dockerfile)
    │
    ├── Stage 1: Install system deps (sqlite3, python, mkdocs)
    ├── Stage 2: Copy skeleton → yarn install (production deps)
    └── Stage 3: Copy bundle → extract → CMD node packages/backend
```

### 7.3. Observability Stack

```
┌──────────────────────────────────────────┐
│           Backstage Backend              │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │     OpenTelemetry SDK              │  │
│  │                                    │  │
│  │  Auto-Instrumentation:            │  │
│  │  • HTTP requests                  │  │
│  │  • Database queries (Knex)        │  │
│  │  • Express middleware             │  │
│  │                                    │  │
│  │  Exporters:                       │  │
│  │  • Prometheus (:9090/metrics)     │  │
│  │  • OTLP (configurable)           │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │     Rate Limiting                 │  │
│  │                                    │  │
│  │  windowMs: configurable           │  │
│  │  incomingRequestLimit: per-window │  │
│  │  ipAllowList: whitelist           │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

---

## 8. Monorepo Architecture

### 8.1. Package Organization

```
backstage/
│
├── packages/                    # 69 core packages
│   ├── Core Framework
│   │   ├── backend-plugin-api/     # Backend plugin contracts
│   │   ├── backend-app-api/        # Backend bootstrap
│   │   ├── backend-defaults/       # Default service implementations
│   │   ├── frontend-plugin-api/    # Frontend plugin contracts
│   │   ├── frontend-app-api/       # Frontend bootstrap
│   │   ├── frontend-defaults/      # Default frontend config
│   │   ├── core-plugin-api/        # Legacy plugin API
│   │   ├── core-app-api/           # Legacy app API
│   │   ├── core-compat-api/        # Legacy compatibility layer
│   │   └── core-components/        # Shared UI components
│   │
│   ├── Applications
│   │   ├── app/                    # Example frontend app
│   │   ├── backend/                # Example backend app
│   │   └── app-legacy/             # Legacy frontend app
│   │
│   ├── Tooling
│   │   ├── cli/                    # Backstage CLI
│   │   ├── cli-*/                  # CLI modules
│   │   ├── repo-tools/             # Repository tools
│   │   ├── create-app/             # App scaffolding
│   │   └── codemods/               # Migration tools
│   │
│   ├── Libraries
│   │   ├── config/                 # Configuration system
│   │   ├── config-loader/          # Config file loading
│   │   ├── errors/                 # Error types
│   │   ├── types/                  # Shared TypeScript types
│   │   ├── integration/            # SCM integration library
│   │   ├── catalog-model/          # Catalog entity model
│   │   ├── catalog-client/         # Catalog REST client
│   │   └── filter-predicates/      # Filter predicate utilities
│   │
│   └── Testing
│       ├── test-utils/             # Test utilities
│       ├── backend-test-utils/     # Backend test utilities
│       ├── frontend-test-utils/    # Frontend test utilities
│       └── e2e-test-utils/         # E2E test utilities
│
├── plugins/                     # 155 plugin directories
│   ├── Feature Plugins
│   │   ├── catalog[-*]/            # Software Catalog (16 modules)
│   │   ├── scaffolder[-*]/         # Software Templates (18 modules)
│   │   ├── techdocs[-*]/           # TechDocs (8 packages)
│   │   ├── search[-*]/             # Search (9 modules)
│   │   ├── kubernetes[-*]/         # Kubernetes (6 packages)
│   │   └── api-docs[-*]/           # API Documentation
│   │
│   ├── Platform Plugins
│   │   ├── auth[-*]/               # Authentication (21 providers)
│   │   ├── permission[-*]/         # Permissions (4 packages)
│   │   ├── notifications[-*]/      # Notifications (5 packages)
│   │   ├── signals[-*]/            # Real-time signals (4 packages)
│   │   └── events[-*]/             # Event system (11 modules)
│   │
│   └── Utility Plugins
│       ├── proxy-backend/          # Backend proxy
│       ├── devtools[-*]/           # Developer tools
│       ├── home[-*]/               # Home page
│       ├── user-settings[-*]/      # User settings
│       └── org[-*]/                # Organization
│
└── workspaces/                  # Standalone workspaces
    └── ui/                         # UI component workspace
```

### 8.2. Package Naming Convention

| Pattern | Role | Ví dụ |
|---------|------|-------|
| `@backstage/plugin-{name}` | Frontend plugin | `@backstage/plugin-catalog` |
| `@backstage/plugin-{name}-backend` | Backend plugin | `@backstage/plugin-catalog-backend` |
| `@backstage/plugin-{name}-backend-module-{module}` | Backend module | `@backstage/plugin-catalog-backend-module-github` |
| `@backstage/plugin-{name}-react` | React utilities | `@backstage/plugin-catalog-react` |
| `@backstage/plugin-{name}-node` | Node.js utilities | `@backstage/plugin-catalog-node` |
| `@backstage/plugin-{name}-common` | Shared types | `@backstage/plugin-catalog-common` |

### 8.3. Dependency Flow

```
                    ┌──────────────┐
                    │ @backstage/  │
                    │ types        │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
      ┌──────────┐  ┌──────────┐  ┌──────────┐
      │ config   │  │ errors   │  │ cli-     │
      │          │  │          │  │ common   │
      └────┬─────┘  └────┬─────┘  └────┬─────┘
           │              │             │
      ┌────▼──────────────▼─────────────▼────┐
      │       backend-plugin-api             │
      │       frontend-plugin-api            │
      └────┬──────────────┬──────────────────┘
           │              │
    ┌──────▼──────┐  ┌────▼──────────┐
    │ backend-    │  │ frontend-     │
    │ defaults    │  │ defaults      │
    └──────┬──────┘  └────┬──────────┘
           │              │
    ┌──────▼──────┐  ┌────▼──────────┐
    │ backend     │  │ app           │
    │ (example)   │  │ (example)     │
    └─────────────┘  └───────────────┘
```

---

## 9. Security Architecture

### 9.1. Defense Layers

```
┌─────────────────────────────────────────────────┐
│ Layer 1: Network                                │
│ • CORS (origin, methods, credentials)           │
│ • CSP (Content-Security-Policy via Helmet)      │
│ • Rate Limiting (window, limit, allowlist)       │
├─────────────────────────────────────────────────┤
│ Layer 2: Authentication                         │
│ • OAuth/OIDC/SAML providers                     │
│ • JWT tokens (service-to-service)               │
│ • Cookie-based sessions                         │
│ • Auth policies per route                       │
├─────────────────────────────────────────────────┤
│ Layer 3: Authorization                          │
│ • Permission policies (ALLOW/DENY)              │
│ • Resource-based permissions                    │
│ • Conditional permissions                       │
├─────────────────────────────────────────────────┤
│ Layer 4: Input Validation                       │
│ • Path traversal protection (resolveSafeChildPath) │
│ • JSON-only responses (no .send())              │
│ • Schema validation (Zod/JSON Schema)           │
├─────────────────────────────────────────────────┤
│ Layer 5: Audit                                  │
│ • AuditorService per plugin                     │
│ • Event severity levels (low/medium/high/critical) │
│ • Success/failure tracking                      │
└─────────────────────────────────────────────────┘
```

---

## 10. Configuration Architecture

### 10.1. Configuration Loading

```
┌─────────────────────────────────────────────┐
│         Configuration Loading               │
│                                             │
│  Priority (low → high):                     │
│                                             │
│  1. app-config.yaml        (base)           │
│  2. app-config.{env}.yaml  (env-specific)   │
│  3. app-config.local.yaml  (local override) │
│  4. Environment variables  (${VAR_NAME})    │
│                                             │
│  Merge Strategy: Deep merge with override   │
│                                             │
│  Visibility:                                │
│  • backend (default)                        │
│  • frontend (must mark in schema)           │
│  • secret (never exposed)                   │
└─────────────────────────────────────────────┘
```

### 10.2. Frontend Extension Configuration

```yaml
app:
  extensions:
    # Boolean: enable/disable
    - page:catalog-unprocessed-entities: false

    # Object: configure
    - entity-card:catalog/about:
        config:
          type: info

    # Complex: nested config
    - page:catalog/entity:
        config:
          showNavItemIcons: true
          groups:
            - overview:
                title: Overview
            - documentation:
                title: Docs
                icon: docs
```

---

## 11. Cross-Cutting Concerns

### 11.1. Error Handling

```typescript
// Standard error types (@backstage/errors)
import {
  NotFoundError,        // 404
  InputError,           // 400
  AuthenticationError,  // 401
  NotAllowedError,      // 403
  ConflictError,        // 409
  ServiceUnavailableError, // 503
} from '@backstage/errors';

// Backend: throw → middleware converts to JSON
throw new NotFoundError('Entity not found');
// Response: { "error": { "name": "NotFoundError", "message": "..." }, "response": { "statusCode": 404 } }
```

### 11.2. Logging

```typescript
// Hierarchical logging
const rootLogger = getRootLogger();           // Root logger
const pluginLogger = rootLogger.child({       // Per-plugin child
  plugin: 'catalog'
});
const componentLogger = pluginLogger.child({  // Per-component child
  component: 'processor'
});
```

### 11.3. Task Scheduling

```typescript
// Scheduled tasks (global or local scope)
scheduler.scheduleTask({
  id: 'catalog-refresh',
  frequency: { minutes: 30 },
  timeout: { minutes: 3 },
  scope: 'global',      // Only one instance runs across backends
  fn: async (abortSignal) => {
    // Task logic
  },
});
```
