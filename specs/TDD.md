# Technical Design Document (TDD)

## Backstage — Open Source Developer Portal

| Thông tin | Chi tiết |
|-----------|----------|
| **Dự án** | Backstage |
| **Phiên bản** | 1.51.0 |
| **Ngày tạo tài liệu** | 27/05/2026 |
| **Tham chiếu** | Architecture.md, PRD.md, SRS.md |

---

## 1. Giới thiệu

### 1.1. Mục đích tài liệu

Tài liệu này mô tả chi tiết thiết kế kỹ thuật (Technical Design) của hệ thống Backstage, bao gồm:

- Design patterns và design decisions
- Chi tiết triển khai các module chính
- Data models và schemas
- API contracts
- Flows và sequences
- Testing strategy

### 1.2. Phạm vi

Tài liệu bao gồm thiết kế kỹ thuật cho toàn bộ core framework và các plugins chính: Catalog, Scaffolder, TechDocs, Search, Auth, Permission, Events, Signals, Notifications.

---

## 2. Design Patterns

### 2.1. Backend Plugin System — Inversion of Control (IoC)

**Pattern**: Service Locator + Dependency Injection

Backstage backend sử dụng một hệ thống DI tự phát triển dựa trên `ServiceRef` (contract) và `ServiceFactory` (implementation). Không sử dụng decorator-based DI (như NestJS/Angular) mà dùng functional API.

```typescript
// ---- ServiceRef: Định nghĩa contract ----
// File: packages/backend-plugin-api/src/services/definitions/coreServices.ts

export namespace coreServices {
  export const database = createServiceRef<DatabaseService>({
    id: 'core.database',
    scope: 'plugin',          // Mỗi plugin nhận instance riêng
  });

  export const rootConfig = createServiceRef<RootConfigService>({
    id: 'core.rootConfig',
    scope: 'root',            // Singleton cho toàn bộ backend
  });
}

// ---- ServiceFactory: Triển khai implementation ----
// File: packages/backend-defaults/src/...

export const databaseServiceFactory = createServiceFactory({
  service: coreServices.database,
  deps: {
    config: coreServices.rootConfig,
    logger: coreServices.logger,
    lifecycle: coreServices.lifecycle,
  },
  async createRootContext({ config, logger }) {
    // Khởi tạo connection pool (shared across plugins)
    const knex = createDatabaseClient(config);
    return { knex };
  },
  async factory({ pluginMetadata }, { knex }) {
    // Mỗi plugin nhận client với schema riêng
    return new DatabaseServiceImpl(knex, pluginMetadata.getId());
  },
});
```

**Design Decision**: Sử dụng `scope: 'plugin'` vs `scope: 'root'`

| Scope | Behavior | Use Case |
|-------|----------|----------|
| `root` | Một instance duy nhất | Configuration, Logger root, HTTP server |
| `plugin` | Instance riêng cho mỗi plugin | Database, Cache, Logger child, HTTP router |

**Multiton pattern**: Một số services hỗ trợ `multiton` (nhiều instances được tạo cho cùng một plugin).

### 2.2. Backend Extension Point Pattern

**Pattern**: Open/Closed Principle implementation

Extension Points cho phép plugins mở rộng nhau mà không cần modify source code. Plugin A expose extension point, Module B (targeting plugin A) inject vào extension point đó.

```
┌─────────────────────────────────────────────────────────────┐
│ Design Flow:                                                │
│                                                             │
│ 1. Plugin đăng ký ExtensionPoint                           │
│ 2. Module đăng ký với cùng pluginId                         │
│ 3. BackendInitializer match module → plugin                 │
│ 4. Module nhận ExtensionPoint trong deps                    │
│ 5. Module gọi methods trên ExtensionPoint                   │
│                                                             │
│ Timing constraint:                                          │
│ registerExtensionPoint() PHẢI được gọi TRƯỚC registerInit() │
└─────────────────────────────────────────────────────────────┘
```

**Implementation:**

```typescript
// ---- Step 1: Plugin defines extension point ----
const catalogProcessingExtensionPoint =
  createExtensionPoint<CatalogProcessingExtensionPoint>({
    id: 'catalog.processing',
  });

// ---- Step 2: Plugin registers extension point ----
export const catalogPlugin = createBackendPlugin({
  pluginId: 'catalog',
  register(reg) {
    // Must be called BEFORE registerInit
    reg.registerExtensionPoint(
      catalogProcessingExtensionPoint,
      new CatalogProcessingExtensionPointImpl(),
    );

    reg.registerInit({
      deps: {
        database: coreServices.database,
        httpRouter: coreServices.httpRouter,
      },
      async init({ database, httpRouter }) {
        // Access registered processors/providers
      },
    });
  },
});

// ---- Step 3: Module extends plugin ----
export const catalogModuleGithub = createBackendModule({
  pluginId: 'catalog',       // Must match plugin
  moduleId: 'github',
  register(reg) {
    reg.registerInit({
      deps: {
        catalog: catalogProcessingExtensionPoint,  // Inject extension point
        config: coreServices.rootConfig,
      },
      async init({ catalog, config }) {
        catalog.addEntityProvider(
          GithubEntityProvider.fromConfig(config),
        );
      },
    });
  },
});
```

**Extension Point Factory Pattern (v1.1)**:

```typescript
// Lazy-initialized extension point with failure handling
reg.registerExtensionPoint({
  extensionPoint: catalogProcessingExtensionPoint,
  factory: (context: ExtensionPointFactoryContext) => {
    return new CatalogProcessingExtensionPointImpl({
      onModuleFailure: (error) => {
        context.reportModuleStartupFailure({ error });
      },
    });
  },
});
```

### 2.3. Frontend Extension System — Tree-based Composition

**Pattern**: Composite Pattern + Configuration-Driven Assembly

Frontend sử dụng extension tree thay vì flat routing. Mỗi extension được gắn vào (attach to) một parent extension qua input slots.

```
┌──────────────────────────────────────────────────────────────┐
│ Extension Resolution Algorithm:                              │
│                                                              │
│ 1. Collect tất cả extensions từ plugins + modules            │
│ 2. Resolve extension IDs (kind:namespace/name)               │
│ 3. Apply configuration overrides (app-config.yaml)           │
│ 4. Build extension tree (attachTo → parent.input)            │
│ 5. Resolve configs (merge schema defaults + config values)   │
│ 6. Instantiate extensions (call factory functions)           │
│ 7. Render extension tree as React component tree             │
└──────────────────────────────────────────────────────────────┘
```

**Extension Data Flow:**

```typescript
// Extension output: type-safe data refs
const coreExtensionData = {
  reactElement: createExtensionDataRef<JSX.Element>('core.reactElement'),
  routePath: createExtensionDataRef<string>('core.routePath'),
};

// Blueprint factory yields data values
*factory(params, { config, inputs }) {
  yield coreExtensionData.reactElement(
    <MyPage title={config.title} />
  );
  yield coreExtensionData.routePath('/my-path');
}

// Parent extension consumes via inputs
createExtension({
  inputs: {
    routes: createExtensionInput({
      element: coreExtensionData.reactElement,
      path: coreExtensionData.routePath,
    }),
  },
  factory({ inputs }) {
    // inputs.routes is array of { element, path }
  },
});
```

### 2.4. Feature Loader Pattern

**Pattern**: Conditional/Lazy Module Loading

Backend Feature Loaders cho phép load plugins dựa trên configuration tại runtime.

```typescript
// File: packages/backend/src/index.ts
const searchLoader = createBackendFeatureLoader({
  deps: {
    config: coreServices.rootConfig,  // Root service dependency
  },
  *loader({ config }) {
    // Always load core search
    yield import('@backstage/plugin-search-backend');
    yield import('@backstage/plugin-search-backend-module-catalog');
    yield import('@backstage/plugin-search-backend-module-explore');
    yield import('@backstage/plugin-search-backend-module-techdocs');

    // Conditionally load Elasticsearch
    if (config.has('search.elasticsearch')) {
      yield import('@backstage/plugin-search-backend-module-elasticsearch');
    }
  },
});
```

**Generator function**: Sử dụng `function*` cho lazy evaluation — plugins chỉ được import khi iterator được consumed.

### 2.5. Configuration Schema Pattern

**Pattern**: Schema-first Configuration

```typescript
// File: packages/backend-plugin-api/config.d.ts
// TypeScript declaration merging cho configuration schema

export interface Config {
  backend?: {
    startup?: {
      default?: {
        onPluginBootFailure?: 'continue' | 'abort';
        onPluginModuleBootFailure?: 'continue' | 'abort';
      };
      plugins?: {
        [pluginId: string]: {
          onPluginBootFailure?: 'continue' | 'abort';
          modules?: {
            [moduleId: string]: {
              onPluginModuleBootFailure?: 'continue' | 'abort';
            };
          };
        };
      };
    };
  };
}
```

---

## 3. Chi tiết thiết kế Module

### 3.1. Software Catalog — Technical Design

#### 3.1.1. Entity Processing Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                Entity Processing Pipeline                     │
│                                                               │
│  ┌─────────────┐     ┌──────────────┐     ┌──────────────┐  │
│  │ Entity      │     │ Processing   │     │ Stitching    │  │
│  │ Providers   │────▶│ Loop         │────▶│ Engine       │  │
│  │             │     │              │     │              │  │
│  │ emit()      │     │ ┌──────────┐ │     │ Merges       │  │
│  │ • full      │     │ │Processor │ │     │ relations    │  │
│  │ • delta     │     │ │ Chain    │ │     │ from         │  │
│  └─────────────┘     │ │          │ │     │ multiple     │  │
│                      │ │ preProc  │ │     │ processors   │  │
│                      │ │ validate │ │     │ into final   │  │
│                      │ │ postProc │ │     │ entity       │  │
│                      │ └──────────┘ │     │              │  │
│                      └──────────────┘     └──────────────┘  │
│                                                               │
│  Database Tables:                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │ entities     │  │ relations    │  │ search             │ │
│  │ • entity_id  │  │ • source_id  │  │ • entity_id        │ │
│  │ • entity_ref │  │ • target_id  │  │ • key              │ │
│  │ • etag       │  │ • type       │  │ • value            │ │
│  │ • data(JSON) │  │              │  │ • original_value   │ │
│  └──────────────┘  └──────────────┘  └────────────────────┘ │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ locations    │  │ refresh_state│                         │
│  │ • location_id│  │ • entity_ref │                         │
│  │ • type       │  │ • next_update│                         │
│  │ • target     │  │ • errors     │                         │
│  └──────────────┘  └──────────────┘                         │
└───────────────────────────────────────────────────────────────┘
```

#### 3.1.2. Entity Provider Interface

```typescript
interface EntityProvider {
  getProviderName(): string;

  connect(connection: EntityProviderConnection): Promise<void>;
}

interface EntityProviderConnection {
  // Full replacement of all entities from this provider
  applyMutation(mutation: {
    type: 'full';
    entities: DeferredEntity[];
  }): Promise<void>;

  // Incremental add/remove
  applyMutation(mutation: {
    type: 'delta';
    added: DeferredEntity[];
    removed: { entityRef: string }[];
  }): Promise<void>;
}
```

#### 3.1.3. Processor Interface

```typescript
interface CatalogProcessor {
  getProcessorName(): string;

  // Pre-process: enrich entity before validation
  preProcessEntity?(
    entity: Entity,
    location: LocationSpec,
  ): Promise<Entity>;

  // Validate: check entity correctness
  validateEntityKind?(entity: Entity): Promise<boolean>;

  // Post-process: emit relations, emit child entities
  postProcessEntity?(
    entity: Entity,
    location: LocationSpec,
    emit: CatalogProcessorEmit,
  ): Promise<Entity>;
}

type CatalogProcessorEmit = (
  processingResult:
    | { type: 'entity'; entity: Entity; location: LocationSpec }
    | { type: 'relation'; relation: EntityRelation }
    | { type: 'error'; error: Error }
    | { type: 'location'; location: LocationSpec }
    | { type: 'refresh'; key: string },
) => void;
```

#### 3.1.4. Catalog Permission Rules

```typescript
// File: plugins/catalog-backend/src/permissions/
const catalogPermissionRules = [
  createPermissionRule({
    name: 'IS_ENTITY_OWNER',
    description: 'Allow if user is entity owner',
    resourceType: 'catalog-entity',
    paramsSchema: z.object({
      claims: z.array(z.string()),
    }),
    apply: (entity, { claims }) => {
      const ownerRef = entity.spec?.owner;
      return claims.includes(ownerRef);
    },
    toQuery: ({ claims }) => ({
      key: 'spec.owner',
      values: claims,
    }),
  }),
];
```

---

### 3.2. Scaffolder — Technical Design

#### 3.2.1. Template Execution Engine

```
┌───────────────────────────────────────────────────────────┐
│                Template Execution Flow                     │
│                                                           │
│  User Input (JSON)                                        │
│       │                                                   │
│       ▼                                                   │
│  ┌──────────────────────┐                                │
│  │ Parameter Validation │  ← JSON Schema validation       │
│  │ (Zod / JSON Schema)  │                                │
│  └──────────┬───────────┘                                │
│             │                                             │
│             ▼                                             │
│  ┌──────────────────────┐                                │
│  │ Task Creation        │  → Persisted to database       │
│  │ (taskId, status)     │                                │
│  └──────────┬───────────┘                                │
│             │                                             │
│             ▼                                             │
│  ┌──────────────────────┐                                │
│  │ Action Execution     │  ← Sequential execution        │
│  │ Loop                 │                                │
│  │                      │                                │
│  │  for each step:      │                                │
│  │    1. Resolve action  │                                │
│  │    2. Template inputs │  ← Nunjucks templating        │
│  │    3. Execute action  │                                │
│  │    4. Capture output  │                                │
│  │    5. Update progress │  → Real-time streaming        │
│  └──────────┬───────────┘                                │
│             │                                             │
│             ▼                                             │
│  ┌──────────────────────┐                                │
│  │ Task Completion      │                                │
│  │ • Success → links    │                                │
│  │ • Failure → errors   │                                │
│  └──────────────────────┘                                │
│                                                           │
│  Audit:                                                   │
│  taskParameterMaxLength: 256 (truncate for security)     │
└───────────────────────────────────────────────────────────┘
```

#### 3.2.2. Action Registration Pattern

```typescript
// Built-in action definition
const createFetchPlainAction = createTemplateAction<{
  url: string;
  targetPath?: string;
}>({
  id: 'fetch:plain',
  description: 'Downloads content from a URL',
  schema: {
    input: z.object({
      url: z.string().describe('URL to fetch'),
      targetPath: z.string().optional(),
    }),
  },
  async handler(ctx) {
    const { url, targetPath } = ctx.input;
    const workspacePath = ctx.workspacePath;

    // Use urlReader to fetch content
    const response = await ctx.urlReader.readTree(url);
    const dir = await response.dir({
      targetDir: resolveSafeChildPath(workspacePath, targetPath ?? '.'),
    });

    ctx.logger.info(`Downloaded content to ${dir}`);
  },
});
```

#### 3.2.3. Template YAML Format

```yaml
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata:
  name: create-react-app
  title: Create React App
  description: Create a new React application
  tags: ['react', 'frontend']
spec:
  owner: platform-team
  type: service

  parameters:
    - title: Fill in details
      required: ['name']
      properties:
        name:
          title: Name
          type: string
          description: Unique name of the component
        owner:
          title: Owner
          type: string
          description: Owner of the component
          ui:field: OwnerPicker

  steps:
    - id: fetch
      name: Fetch Base Template
      action: fetch:template
      input:
        url: ./template
        values:
          name: ${{ parameters.name }}

    - id: publish
      name: Publish to GitHub
      action: publish:github
      input:
        allowedHosts: ['github.com']
        repoUrl: github.com?owner=${{ parameters.owner }}&repo=${{ parameters.name }}

    - id: register
      name: Register in Catalog
      action: catalog:register
      input:
        repoContentsUrl: ${{ steps.publish.output.repoContentsUrl }}
        catalogInfoPath: /catalog-info.yaml

  output:
    links:
      - title: Repository
        url: ${{ steps.publish.output.remoteUrl }}
      - title: Open in catalog
        icon: catalog
        entityRef: ${{ steps.register.output.entityRef }}
```

---

### 3.3. TechDocs — Technical Design

#### 3.3.1. Build Pipeline

```
┌──────────────────────────────────────────────────────────┐
│                 TechDocs Build Pipeline                   │
│                                                          │
│  Source (repo)              Generator              Publisher
│  ┌──────────┐         ┌──────────────┐         ┌──────────┐
│  │mkdocs.yml│         │              │         │          │
│  │docs/     │────────▶│ MkDocs Build │────────▶│ Storage  │
│  │ *.md     │         │              │         │          │
│  └──────────┘         │ Modes:       │         │ Types:   │
│                       │ • docker     │         │ • local  │
│  Config:              │ • local      │         │ • gcs    │
│  techdocs:            │              │         │ • s3     │
│    builder: local     │ Docker image:│         │ • azure  │
│    generator:         │ mkdocs-      │         │ • swift  │
│      runIn: docker    │ techdocs-core│         │          │
│    publisher:         │ v1.1.7       │         │          │
│      type: local      │              │         │          │
│                       └──────────────┘         └──────────┘
│                                                          │
│  Read Flow:                                              │
│  Browser → /api/techdocs/static/* → Publisher.fetch() →  │
│  Static HTML served                                      │
└──────────────────────────────────────────────────────────┘
```

#### 3.3.2. TechDocs Entity Annotation

```yaml
# In catalog-info.yaml
metadata:
  annotations:
    backstage.io/techdocs-ref: dir:.
    #   → TechDocs source is in same repo root
    # OR
    backstage.io/techdocs-ref: url:https://github.com/org/repo/tree/main
    #   → TechDocs source is at specific URL
```

---

### 3.4. Search — Technical Design

#### 3.4.1. Collator Architecture

```typescript
// Collator interface
interface DocumentCollatorFactory {
  getCollator(): Promise<Readable>; // Returns object-mode readable stream
}

// Catalog collator emits search documents
class CatalogCollatorFactory implements DocumentCollatorFactory {
  async getCollator() {
    const entities = await this.catalogClient.getEntities();

    return new Readable({
      objectMode: true,
      read() {
        for (const entity of entities) {
          this.push({
            title: entity.metadata.name,
            text: entity.metadata.description ?? '',
            location: `/catalog/${entity.metadata.namespace}/${entity.kind}/${entity.metadata.name}`,
            docType: 'software-catalog',
            // Additional fields for filtering
            kind: entity.kind,
            type: entity.spec?.type,
            owner: entity.spec?.owner,
            lifecycle: entity.spec?.lifecycle,
          });
        }
        this.push(null); // Signal end of stream
      },
    });
  }
}
```

#### 3.4.2. Search Engine Interface

```typescript
interface SearchEngine {
  // Set up index for a document type
  getIndexer(type: string): Promise<SearchEngineIndexer>;

  // Query the search index
  query(query: SearchQuery): Promise<SearchResultSet>;
}

interface SearchQuery {
  term: string;
  filters?: Record<string, string | string[]>;
  types?: string[];
  pageCursor?: string;
}

interface SearchResultSet {
  results: Array<{
    type: string;
    document: IndexableDocument;
    rank: number;
    highlight?: {
      preTag: string;
      postTag: string;
      fields: Record<string, string>;
    };
  }>;
  nextPageCursor?: string;
  previousPageCursor?: string;
  numberOfResults?: number;
}
```

---

### 3.5. Events System — Technical Design

#### 3.5.1. Event Bus Interface

```typescript
interface EventBroker {
  publish(params: EventParams): Promise<void>;
  subscribe(subscriber: EventSubscriber): Promise<void>;
}

interface EventParams {
  topic: string;
  eventPayload: Record<string, unknown>;
  metadata?: Record<string, string>;
}

interface EventSubscriber {
  supportsEvent(params: EventParams): boolean;
  onEvent(params: EventParams): Promise<void>;
}
```

#### 3.5.2. Event Source Modules

| Module | Source | Topic Pattern |
|--------|--------|---------------|
| `events-backend-module-github` | GitHub Webhooks | `github.*` |
| `events-backend-module-gitlab` | GitLab Webhooks | `gitlab.*` |
| `events-backend-module-bitbucket-cloud` | Bitbucket Webhooks | `bitbucket-cloud.*` |
| `events-backend-module-aws-sqs` | AWS SQS | Custom |
| `events-backend-module-google-pubsub` | Google Pub/Sub | Custom |
| `events-backend-module-kafka` | Apache Kafka | Custom |

---

### 3.6. Notifications — Technical Design

#### 3.6.1. Notification Flow

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ Source Plugin │     │ Notification    │     │  Notification    │
│              │────▶│ Service         │────▶│  Processors      │
│ scaffolder   │     │ (Backend)       │     │                  │
│ catalog      │     │                 │     │ ┌──────────────┐ │
│ events       │     │ createNotifi-   │     │ │ In-App       │ │
│ custom       │     │ cation({       │     │ │ (default)    │ │
└──────────────┘     │   recipients,   │     │ └──────────────┘ │
                     │   title,        │     │ ┌──────────────┐ │
                     │   description,  │     │ │ Email        │ │
                     │   severity,     │     │ │ Module       │ │
                     │   payload       │     │ └──────────────┘ │
                     │ })              │     │ ┌──────────────┐ │
                     └─────────────────┘     │ │ Slack        │ │
                                             │ │ Module       │ │
                                             │ └──────────────┘ │
                                             └──────────────────┘
```

---

## 4. Data Models

### 4.1. Entity Data Model

```typescript
// File: packages/catalog-model/src/entity/Entity.ts
interface Entity {
  apiVersion: string;       // e.g., "backstage.io/v1alpha1"
  kind: string;             // e.g., "Component", "API", "System"
  metadata: EntityMeta;
  spec?: JsonObject;
  relations?: EntityRelation[];
  status?: EntityStatus;
}

interface EntityMeta {
  uid?: string;
  etag?: string;
  name: string;
  namespace?: string;       // default: "default"
  title?: string;
  description?: string;
  labels?: Record<string, string>;
  annotations?: Record<string, string>;
  tags?: string[];
  links?: Array<{
    url: string;
    title?: string;
    icon?: string;
    type?: string;
  }>;
}

interface EntityRelation {
  type: string;             // e.g., "ownedBy", "dependsOn"
  targetRef: string;        // Entity reference
}

// Entity reference format: [<kind>:][<namespace>/]<name>
// Examples:
//   "component:default/my-service"
//   "user:engineering/john-doe"
//   "my-service" (kind and namespace inferred from context)
```

### 4.2. Well-Known Entity Kinds

```
┌──────────────────────────────────────────────────────────┐
│                   Entity Kind Hierarchy                   │
│                                                          │
│  ┌──────────┐                                           │
│  │  Domain  │  ← Business domain                        │
│  └────┬─────┘                                           │
│       │ hasPart                                         │
│  ┌────▼─────┐                                           │
│  │  System  │  ← Collection of components               │
│  └────┬─────┘                                           │
│       │ hasPart                                         │
│  ┌────▼──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │  Component    │  │   API    │  │    Resource      │ │
│  │ (service,    │  │ (openapi,│  │ (database,       │ │
│  │  website,    │──│  asyncapi│  │  s3-bucket,      │ │
│  │  library)    │  │  graphql,│  │  cluster)        │ │
│  └──────────────┘  │  grpc)   │  └──────────────────┘ │
│       │            └──────────┘                         │
│       │ ownedBy                                         │
│  ┌────▼─────┐  ┌──────────┐                            │
│  │  Group   │──│   User   │  ← Organization model      │
│  └──────────┘  └──────────┘                            │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐      │
│  │ Location │  │ Template │  │   AiResource     │      │
│  │ (source) │  │ (scaffold│  │   (ML models)    │      │
│  └──────────┘  │  -ing)   │  └──────────────────┘      │
│                └──────────┘                              │
└──────────────────────────────────────────────────────────┘
```

### 4.3. Well-Known Relations

| Relation Type | Source Kind | Target Kind | Mô tả |
|--------------|------------|-------------|--------|
| `ownedBy` | Component/API/System | User/Group | Ownership |
| `ownerOf` | User/Group | Component/API/System | Inverse of ownedBy |
| `dependsOn` | Component | Component/Resource | Dependency |
| `dependencyOf` | Component/Resource | Component | Inverse |
| `providesApi` | Component | API | API provider |
| `apiProvidedBy` | API | Component | Inverse |
| `consumesApi` | Component | API | API consumer |
| `apiConsumedBy` | API | Component | Inverse |
| `hasPart` | System/Domain | Component/System | Contains |
| `partOf` | Component/System | System/Domain | Inverse |
| `memberOf` | User | Group | Group membership |
| `hasMember` | Group | User | Inverse |
| `parentOf` | Group | Group | Group hierarchy |
| `childOf` | Group | Group | Inverse |

### 4.4. Backstage Credentials Model

```typescript
// Principal hierarchy
type BackstagePrincipalTypes = {
  user: {
    type: 'user';
    userEntityRef: string;      // "user:default/john-doe"
    actor?: BackstageServicePrincipal; // Originating service
  };
  service: {
    type: 'service';
    subject: string;            // Plugin ID
    accessRestrictions?: {
      permissionNames?: string[];
      permissionAttributes?: {
        action?: ('create' | 'read' | 'update' | 'delete')[];
      };
    };
  };
  none: {
    type: 'none';               // No identity
  };
};

// Credentials wrapper
type BackstageCredentials<TPrincipal = unknown> = {
  $$type: '@backstage/BackstageCredentials';
  expiresAt?: Date;
  principal: TPrincipal;
};
```

---

## 5. API Design

### 5.1. Backend API Patterns

#### 5.1.1. Plugin HTTP Route Registration

```typescript
// Plugin registers routes via httpRouter service
createBackendPlugin({
  pluginId: 'catalog',
  register(reg) {
    reg.registerInit({
      deps: {
        httpRouter: coreServices.httpRouter,
        httpAuth: coreServices.httpAuth,
      },
      async init({ httpRouter, httpAuth }) {
        // Auth policy: this specific path is public
        httpRouter.addAuthPolicy({
          path: '/health',
          allow: 'unauthenticated',
        });

        // Register Express handler
        httpRouter.use(router);
      },
    });
  },
});
```

URL pattern: `http://localhost:7007/api/{pluginId}/{path}`

#### 5.1.2. Error Response Format

```typescript
// All errors are returned as JSON
// HTTP Status → Error Type mapping

// 400 Bad Request
throw new InputError('Invalid entity reference format');

// 401 Unauthorized
throw new AuthenticationError('Missing or invalid token');

// 403 Forbidden
throw new NotAllowedError('Insufficient permissions');

// 404 Not Found
throw new NotFoundError(`Entity '${entityRef}' not found`);

// 409 Conflict
throw new ConflictError('Entity already exists');

// 503 Service Unavailable
throw new ServiceUnavailableError('Database connection failed');
```

**Response format:**

```json
{
  "error": {
    "name": "NotFoundError",
    "message": "Entity 'component:default/my-service' not found"
  },
  "response": {
    "statusCode": 404
  }
}
```

### 5.2. Configuration API

```yaml
# Core configuration sections
app:                    # Frontend app configuration
  title: string
  baseUrl: string
  routes: object        # Route bindings
  extensions: array     # Extension configuration
  packages: string      # 'all' | include/exclude

backend:                # Backend configuration
  baseUrl: string
  listen:
    port: number
  database:
    client: string      # 'better-sqlite3' | 'pg'
    connection: string | object
  cache:
    store: string       # 'memory' | 'redis'
    connection: string
  cors: object          # CORS settings
  csp: object           # CSP headers
  auth: object          # Auth settings
  startup: object       # Startup resilience

integrations:           # SCM integrations
  github: array
  gitlab: array
  azure: array
  awsS3: array

catalog:                # Catalog configuration
  rules: array          # Import rules
  locations: array      # Static locations
  providers: object     # Dynamic providers

auth:                   # Authentication providers
  providers: object
  environment: string

permission:             # Permission system
  enabled: boolean

proxy:                  # Backend proxy
  endpoints: object
```

---

## 6. Flows & Sequences

### 6.1. Backend Startup Sequence

```
┌─────────┐   ┌────────────┐   ┌──────────────┐   ┌──────────┐
│createBa- │   │BackendIni- │   │ServiceReg-   │   │Plugins   │
│ckend()   │   │tializer    │   │istry         │   │& Modules │
└────┬─────┘   └─────┬──────┘   └──────┬───────┘   └────┬─────┘
     │               │                │                  │
     │ add(feature)  │                │                  │
     │──────────────▶│                │                  │
     │               │                │                  │
     │ start()       │                │                  │
     │──────────────▶│                │                  │
     │               │ loadConfig()   │                  │
     │               │───────────────▶│                  │
     │               │                │                  │
     │               │ registerRoot   │                  │
     │               │ Services()     │                  │
     │               │───────────────▶│                  │
     │               │                │                  │
     │               │ resolveFeature │                  │
     │               │ Loaders()      │                  │
     │               │────────────────────────────────▶│
     │               │                │                │
     │               │ matchModules   │                │
     │               │ ToPlugins()    │                │
     │               │────────────────────────────────▶│
     │               │                │                │
     │               │ initExtension  │                │
     │               │ Points()       │                │
     │               │────────────────────────────────▶│
     │               │                │                │
     │               │ resolveDeps()  │                │
     │               │───────────────▶│                │
     │               │                │  createService │
     │               │                │───────────────▶│
     │               │                │                │
     │               │ runInit()      │                │
     │               │────────────────────────────────▶│
     │               │                │                │
     │               │ startHttp()    │                │
     │               │───────────────▶│                │
     │               │                │                │
     │               │ lifecycleStart │                │
     │               │────────────────────────────────▶│
     │               │                │                │
     │◀──────────────│ ready          │                │
     │               │                │                │
```

### 6.2. Entity Registration Sequence

```
┌──────────┐  ┌────────────┐  ┌───────────┐  ┌──────────┐  ┌─────────┐
│ User     │  │ Catalog UI │  │ Catalog   │  │Processing│  │Database │
│ Browser  │  │ (Frontend) │  │ Backend   │  │ Engine   │  │         │
└────┬─────┘  └─────┬──────┘  └─────┬─────┘  └────┬─────┘  └────┬────┘
     │              │               │              │             │
     │ Register     │               │              │             │
     │ Component    │               │              │             │
     │─────────────▶│               │              │             │
     │              │ POST /api/    │              │             │
     │              │ catalog/      │              │             │
     │              │ locations     │              │             │
     │              │──────────────▶│              │             │
     │              │               │ insert       │             │
     │              │               │ location     │             │
     │              │               │─────────────────────────▶│
     │              │               │              │             │
     │              │               │ schedule     │             │
     │              │               │ processing   │             │
     │              │               │─────────────▶│             │
     │              │               │              │             │
     │              │               │              │ fetch YAML  │
     │              │               │              │────────────▶│
     │              │               │              │ (urlReader) │
     │              │               │              │             │
     │              │               │              │ run         │
     │              │               │              │ processors  │
     │              │               │              │             │
     │              │               │              │ stitch      │
     │              │               │              │ relations   │
     │              │               │              │             │
     │              │               │              │ save entity │
     │              │               │              │────────────▶│
     │              │               │              │             │
     │              │ 201 Created   │              │             │
     │              │◀──────────────│              │             │
     │ Entity       │               │              │             │
     │ registered   │               │              │             │
     │◀─────────────│               │              │             │
```

### 6.3. Authentication Sequence (OAuth)

```
┌──────────┐  ┌────────────┐  ┌───────────┐  ┌──────────┐
│ User     │  │ Frontend   │  │ Auth      │  │ IdP      │
│ Browser  │  │ Auth UI    │  │ Backend   │  │ (GitHub)  │
└────┬─────┘  └─────┬──────┘  └─────┬─────┘  └────┬─────┘
     │              │               │              │
     │ Click Login  │               │              │
     │─────────────▶│               │              │
     │              │ GET /api/auth │              │
     │              │ /github/start │              │
     │              │──────────────▶│              │
     │              │               │ 302 Redirect │
     │              │               │─────────────▶│
     │              │               │              │
     │ OAuth Consent│               │              │
     │─────────────────────────────────────────────▶│
     │              │               │              │
     │ Callback     │               │              │
     │◀────────────────────────────────────────────│
     │              │               │              │
     │ /api/auth/   │               │              │
     │ github/      │               │              │
     │ handler/frame│               │              │
     │─────────────────────────────▶│              │
     │              │               │ Exchange code│
     │              │               │ for token    │
     │              │               │─────────────▶│
     │              │               │◀─────────────│
     │              │               │              │
     │              │               │ Sign-in      │
     │              │               │ Resolver     │
     │              │               │ (map to      │
     │              │               │  entity)     │
     │              │               │              │
     │              │               │ Issue        │
     │              │               │ Backstage    │
     │              │               │ Token (JWT)  │
     │              │               │              │
     │ Set cookie   │               │              │
     │ + token      │               │              │
     │◀────────────────────────────│              │
     │              │               │              │
     │ Authenticated│               │              │
     │─────────────▶│               │              │
```

---

## 7. Testing Strategy

### 7.1. Test Pyramid

```
        ┌───────────┐
        │   E2E     │  Playwright
        │   Tests   │  (packages/e2e-test)
        │  (少数)    │
        ├───────────┤
        │ Integration│  Jest + backend-test-utils
        │   Tests    │  (plugin integration)
        │  (中程度)   │
        ├───────────┤
        │   Unit     │  Jest + MSW
        │   Tests    │  (per-package)
        │  (大量)     │
        └───────────┘
```

### 7.2. Test Utilities

```typescript
// Backend test setup
import { startTestBackend } from '@backstage/backend-test-utils';

const { server } = await startTestBackend({
  features: [
    catalogPlugin,
    mockServices.rootConfig.factory({
      data: { /* test config */ },
    }),
  ],
});

// Frontend test setup
import { renderInTestApp } from '@backstage/frontend-test-utils';

const rendered = await renderInTestApp(<CatalogPage />);
expect(rendered.getByText('My Component')).toBeInTheDocument();
```

### 7.3. Network Mocking (ADR007)

```typescript
// Jest config: block real network requests
// package.json root:
{
  "jest": {
    "rejectFrontendNetworkRequests": true
  }
}

// Use MSW for mocking
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.get('/api/catalog/entities', (req, res, ctx) => {
    return res(ctx.json({ items: [/* mock entities */] }));
  }),
);
```

### 7.4. Visual Testing

```typescript
// Storybook stories for component testing
// storybook build: yarn storybook

// Accessibility addon: @storybook/addon-a11y
// Chromatic for visual regression: build-storybook:chromatic
```

### 7.5. API Contract Testing

```bash
# Generate API reports
yarn build:api-reports

# Validate release tags
yarn build:api-reports --validate-release-tags

# Output: report.api.md per package
# Changes to API surface require explicit approval
```

---

## 8. Build System Design

### 8.1. Build Tools

| Tool | Mục đích | Configuration |
|------|----------|---------------|
| **Backstage CLI** | Package build, start, lint, test | Wraps underlying tools |
| **TypeScript** | Type checking, compilation | `tsconfig.json` |
| **Vite 7** | Frontend bundling | Via Backstage CLI |
| **Webpack** | Backend bundling (skeleton + bundle) | Via Backstage CLI |
| **ESLint** | Code linting | `.eslintrc.js` |
| **Prettier** | Code formatting | Via `@backstage/cli/config/prettier` |
| **Storybook 10** | Component development | `.storybook/` |
| **Changesets** | Version management | `.changeset/` |
| **API Extractor** | API surface tracking | `report.api.md` per package |
| **Vale** | Documentation linting | `.vale.ini` |
| **Madge** | Circular dependency detection | `madge` config in package.json |
| **Husky** | Git hooks | `.husky/` |
| **lint-staged** | Pre-commit linting | Config in package.json |

### 8.2. Package Build Output

```
package/
├── src/           # TypeScript source
├── dist/          # Build output
│   ├── index.cjs.js    # CommonJS build (backend)
│   ├── index.esm.js    # ESM build (frontend)
│   └── index.d.ts      # Type declarations
├── report.api.md  # API surface report
└── package.json
```

### 8.3. Backend Docker Build

```dockerfile
# Optimized build with layer caching

# 1. System dependencies (cached layer)
RUN apt-get install libsqlite3-dev python3 ...

# 2. Package skeleton (cached unless deps change)
COPY skeleton.tar.gz ./
RUN tar xzf skeleton.tar.gz
RUN yarn workspaces focus --all --production

# 3. Application bundle (changes per deploy)
COPY bundle.tar.gz ./
RUN tar xzf bundle.tar.gz

CMD ["node", "packages/backend", "--config", "app-config.yaml"]
```

---

## 9. Coding Standards & Conventions

### 9.1. Architecture Decision Records (ADRs)

| ADR | Decision | Rationale |
|-----|----------|-----------|
| ADR003 | Named exports only | Tree-shaking, explicit imports |
| ADR006 | No React.FC/React.SFC | TypeScript inference, explicit children |
| ADR007 | MSW for mocking | Intercepts at network level, consistent |
| ADR010 | Luxon for dates | Immutable, timezone support |
| ADR013→014 | node-fetch → native fetch | Standardization |

### 9.2. Naming Patterns

| Pattern | Convention | Ví dụ |
|---------|-----------|-------|
| **Plugin ID** | lowercase, dashes | `catalog`, `tech-docs` |
| **Module ID** | lowercase, dashes | `github`, `elasticsearch` |
| **Package name** | `@backstage/plugin-{id}[-{role}][-module-{module}]` | `@backstage/plugin-catalog-backend-module-github` |
| **Extension ID** | `{kind}:{namespace}[/{name}]` | `page:catalog/entity` |
| **ServiceRef ID** | `core.{name}` or `plugin.{name}` | `core.database` |
| **Config keys** | camelCase | `pluginId`, `baseUrl` |
| **Entity ref** | `[kind:][namespace/]name` | `component:default/my-app` |

### 9.3. Express Response Rules

```typescript
// ✅ CORRECT: Always use .json() for data
res.json({ data: result });
res.json({ message: 'Created' });

// ✅ CORRECT: Use .end() for empty responses
res.status(204).end();

// ❌ WRONG: Never use .send() with user input
res.send(`Error: ${userInput}`);  // XSS risk

// ✅ CORRECT: Throw errors, middleware handles them
throw new InputError(`Invalid id: '${req.params.id}'`);
```

### 9.4. File Path Security

```typescript
// ✅ CORRECT: Use resolveSafeChildPath
import { resolveSafeChildPath } from '@backstage/backend-plugin-api';

const filePath = resolveSafeChildPath(tmpDir, userProvidedName);
await fs.writeFile(filePath, content);

// ❌ WRONG: Vulnerable to path traversal
const filePath = path.join(tmpDir, userProvidedName);
// userProvidedName = "../../../../etc/passwd" → ATTACK!
```

---

## 10. Evolution & Migration

### 10.1. Legacy → New Backend System

```
Legacy (packages/backend-legacy)     New (packages/backend)
─────────────────────────────────    ────────────────────────
createRouter({...})                  createBackendPlugin({...})
plugins/catalog.ts                   backend.add(import('...'))
Manual wiring in index.ts            Automatic DI via services
Custom env object                    coreServices.* injection
```

### 10.2. Legacy → New Frontend System

```
Legacy                               New
──────                               ────
createPlugin()                       createFrontendPlugin()
createRouteRef()                     RouteRef (same)
React component exports              Extension Blueprints
<Route> in App.tsx                   Extension tree + config
EntityPage component tree            Entity cards/contents via config
```

### 10.3. Material UI 4 → Backstage UI

```
MUI4 (@material-ui/core)            BUI (@backstage/ui)
─────────────────────────            ────────────────────
Migration tool: yarn mui-to-bui
Automated analytics: backstage-migration-analytics.js
Storybook: visual comparison during migration
```
