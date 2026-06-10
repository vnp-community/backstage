# Limitation: Backend Plugin System

## Package
`@backstage/backend-plugin-api`

## Source Files
- `packages/backend-plugin-api/src/services/definitions/*.ts`
- `packages/backend-plugin-api/src/services/system/types.ts`
- `packages/backend-plugin-api/src/wiring/types.ts`
- `packages/backend-plugin-api/src/wiring/createBackendPlugin.ts`

---

## L-BPS-001: Monolithic Single-Process Architecture

**Severity**: Critical  
**Type**: Architecture Limitation

All backend plugins run within a single Node.js process. The `createBackendPlugin()` and service injection system is designed around in-process dependency resolution:

```typescript
export function createBackendPlugin(options: CreateBackendPluginOptions): BackendFeature {
  // All registrations happen in the same process
  options.register({
    registerInit(regInit) {
      init = { deps: regInit.deps, func: regInit.init };
    },
  });
}
```

**Impact**:
- A single plugin crash or OOM can take down the entire backend
- No independent scaling of individual plugins
- Memory is shared across all plugins with no isolation
- No ability to deploy plugins as separate microservices without significant rearchitecture

---

## L-BPS-002: Service Discovery is URL-Based Only

**Severity**: Medium  
**Type**: Design Limitation

The `DiscoveryService` only resolves plugin endpoints to URLs:

```typescript
export interface DiscoveryService {
  getBaseUrl(pluginId: string): Promise<string>;
  getExternalBaseUrl(pluginId: string): Promise<string>;
}
```

**Impact**:
- No support for gRPC, WebSocket, or other non-HTTP protocols for inter-plugin communication
- No service mesh integration (Istio, Envoy)
- No load balancing or circuit breaking at the discovery layer
- Discovery always goes through URL → no direct in-process optimization when plugins are co-located

---

## L-BPS-003: Database Service Returns Raw Knex Client

**Severity**: High  
**Type**: Abstraction Leak

The `DatabaseService` directly exposes a Knex client:

```typescript
export interface DatabaseService {
  getClient(): Promise<Knex>;
}
```

**Impact**:
- Tight coupling between plugins and Knex ORM — changing the database abstraction is a breaking change across the entire ecosystem
- No connection pooling controls per-plugin
- No query timeout enforcement at the service level
- No built-in query logging or performance monitoring
- The `skip` migration option exists only as a boolean — no versioning or rollback support

---

## L-BPS-004: Cache Service Has Minimal API Surface

**Severity**: Medium  
**Type**: Missing Feature

The `CacheService` provides only basic `get/set/delete`:

```typescript
export interface CacheService {
  get<TValue extends JsonValue>(key: string): Promise<TValue | undefined>;
  set(key: string, value: JsonValue, options?: CacheServiceSetOptions): Promise<void>;
  delete(key: string): Promise<void>;
  withOptions(options: CacheServiceOptions): CacheService;
}
```

**Impact**:
- No batch operations (`mget`, `mset`, `mdelete`)
- No cache invalidation patterns (tags, namespaces, wildcard delete)
- No `getOrSet` / cache-aside helper
- No cache statistics or hit/miss metrics
- No distributed cache locking
- Values are limited to `JsonValue` — cannot cache binary data

---

## L-BPS-005: Scheduler Service Lacks Robust Task Management

**Severity**: Medium  
**Type**: Design Limitation

The `SchedulerService` has limitations:

1. **Best-effort frequency** — documented as approximate:
   > "This is the best effort value; under some circumstances there can be deviations."

2. **No task priority** — all tasks are equal
3. **No retry policy** — failed tasks have no configurable retry with backoff
4. **No task observability** — no events/metrics for task execution
5. **`initialDelay` is per-worker only** — cannot globally delay a task after deployment

```typescript
scope?: 'global' | 'local';  // Only two scope options
```

**Impact**: Complex scheduling requirements (priority queues, dead letter queues, dependency chains between tasks) require external infrastructure.

---

## L-BPS-006: AuthService Token Must Be Fetched Per-Request

**Severity**: Medium  
**Type**: Performance

The `AuthService.getPluginRequestToken()` documentation explicitly states:

```typescript
// This method should be called before each request. Do not hold on to the
// issued token and reuse it for future calls.
```

**Impact**: Every inter-plugin HTTP call requires a new token generation, adding latency and CPU overhead. For high-throughput scenarios (e.g., catalog ingestion), this creates significant overhead.

---

## L-BPS-007: LoggerService Has Minimal Interface

**Severity**: Low  
**Type**: Design Limitation

The `LoggerService` has only four log levels and `child`:

```typescript
export interface LoggerService {
  error(message: string, meta?: Error | JsonObject): void;
  warn(message: string, meta?: Error | JsonObject): void;
  info(message: string, meta?: Error | JsonObject): void;
  debug(message: string, meta?: Error | JsonObject): void;
  child(meta: JsonObject): LoggerService;
}
```

**Impact**:
- No `trace` or `fatal` log levels
- No structured logging helpers (e.g., `withField`, `withError`)
- No log level configuration per-plugin
- No log sampling or rate limiting
- No async logging support

---

## L-BPS-008: HttpRouterService Bound to Express

**Severity**: High  
**Type**: Vendor Lock-in

The HTTP router directly depends on Express.js types:

```typescript
import type { Handler } from 'express';

export interface HttpRouterService {
  use(handler: Handler): void;
}
```

**Impact**:
- Cannot use Fastify, Koa, Hono, or other HTTP frameworks
- Express.js performance limitations apply to all plugins
- Express's synchronous middleware model limits advanced patterns (e.g., streaming, HTTP/2 push)

---

## L-BPS-009: Extension Point Registration Order Matters

**Severity**: Medium  
**Type**: Design Constraint

Extension points must be registered **before** `registerInit`:

```typescript
if (init) {
  throw new Error('registerExtensionPoint called after registerInit');
}
```

And `registerInit` can only be called once:

```typescript
if (init) {
  throw new Error('registerInit must only be called once');
}
```

**Impact**: Plugins cannot dynamically add extension points during initialization, limiting patterns where extension points depend on runtime conditions.

---

## L-BPS-010: UrlReaderService `stream()` Is Optional

**Severity**: Low  
**Type**: Incomplete API

The `stream()` method on `UrlReaderServiceReadUrlResponse` is optional:

```typescript
export type UrlReaderServiceReadUrlResponse = {
  buffer(): Promise<Buffer>;
  stream?(): Readable;  // Optional
  etag?: string;
  lastModifiedAt?: Date;
};
```

The comment says: "This method will be required in a future release."

**Impact**: Consumers cannot rely on streaming for large files. The `buffer()` method loads entire files into memory, which is problematic for large artifacts (e.g., multi-GB repository archives).

---

## L-BPS-011: LifecycleService Has No Health Check Integration

**Severity**: Medium  
**Type**: Missing Feature

The `LifecycleService` provides `addStartupHook` and `addShutdownHook` but has no readiness/liveness probe integration:

```typescript
export interface LifecycleService {
  addStartupHook(hook, options?): void;
  addShutdownHook(hook, options?): void;
}
```

**Impact**:
- No standard way for plugins to signal "ready" or "degraded"
- Cannot implement Kubernetes-style readiness/liveness probes per-plugin
- Health checks can only be provided at the global level

---

## L-BPS-012: Plugin ID Validation is Lenient with Legacy Pattern

**Severity**: Low  
**Type**: Technical Debt

`createBackendPlugin` uses two patterns — one for warnings and one for hard errors:

```typescript
if (!ID_PATTERN.test(options.pluginId)) {
  console.warn(`WARNING: The pluginId '${options.pluginId}' will be invalid soon...`);
}
if (!ID_PATTERN_OLD.test(options.pluginId)) {
  throw new Error(`Invalid pluginId...`);
}
```

**Impact**: Legacy plugin IDs that don't match the new pattern will eventually break, but there's no migration path or tooling to automatically rename them.

---

## L-BPS-013: No Service Versioning or API Contracts

**Severity**: High  
**Type**: Design Limitation

Service interfaces have no version information. A `ServiceRef` is identified only by `id`:

```typescript
export type ServiceRef<TService, TScope, TInstances> = {
  id: string;
  scope: TScope;
  // No version field
};
```

**Impact**:
- No way to have multiple versions of a service coexist
- Breaking changes to a service interface require coordinated updates across all consumers
- No gradual migration path for service API evolution
