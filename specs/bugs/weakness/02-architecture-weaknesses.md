# Architecture & Design Weaknesses — Backstage Backend

## SEVERITY: HIGH

---

### 1. Monolithic Single-Process Architecture

**Files:**
- [`CreateBackend.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/CreateBackend.ts)
- [`index.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend/src/index.ts)

**Problem:** All plugins run in a single Node.js process. Despite having a plugin-based architecture, the runtime is monolithic:
- All 20+ plugins share the same process, memory space, event loop, and thread pool
- A crash in any plugin (unhandled rejection, OOM, infinite loop) kills the entire backend
- CPU-heavy operations in one plugin (e.g., scaffolder template execution) block all other plugins
- There is no process-level isolation, resource limiting, or sandboxing between plugins

```typescript
// All plugins share the same backend process:
backend.add(import('@backstage/plugin-catalog-backend'));
backend.add(import('@backstage/plugin-scaffolder-backend'));
backend.add(import('@backstage/plugin-techdocs-backend'));
// ... all running in one process
backend.start();
```

**Impact:** A single misbehaving plugin can take down all services. No independent scaling, deployment, or failure isolation is possible.

---

### 2. Tightly Coupled Service Discovery — No Real Service Registry

**File:** [`HostDiscovery.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/discovery/HostDiscovery.ts)

**Problem:** The discovery service is config-driven with static URL patterns rather than a true service registry:
- Plugin addresses are derived from config patterns like `http://host:port/api/{{pluginId}}`
- There is no health-check–based discovery, circuit breaking, or failover
- SRV record support exists but is limited to internal URLs only
- No support for dynamic service registration/deregistration

```typescript
// All discovery is based on URL pattern string replacement
#makeResolver(urlPattern: string, allowSrv: boolean): Resolver {
  const withPluginId = (pluginId: string, url: string) => {
    return url.replace(/\{\{\s*pluginId\s*\}\}/g, encodeURIComponent(pluginId));
  };
```

**Impact:** Cannot support dynamic scaling, blue-green deployments, or multi-region failover without significant infrastructure changes.

---

### 3. Database Coupling — All Plugins Share One Database Config

**File:** [`DatabaseManager.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/database/DatabaseManager.ts)

**Problem:** The database manager provides per-plugin "isolation" only at the schema/prefix level, not at the connection level:
- All plugins share the same database server connection config
- Plugin-specific overrides are optional but rarely used in practice
- The connection pool is shared via Knex, meaning one plugin's heavy queries can exhaust the pool for all others
- No connection-level resource limits per plugin

```typescript
// Database prefix is the only isolation mechanism
const prefix = databaseConfig.getOptionalString('prefix') || 'backstage_plugin_';
```

**Impact:** Database contention between plugins, no data sovereignty, and cascading failures from one plugin's database issues.

---

### 4. No Circuit Breaker for Service-to-Service Communication

**Files:**
- [`DefaultAuthService.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/auth/DefaultAuthService.ts#L150-L197)
- [`PluginTokenHandler.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/auth/plugin/PluginTokenHandler.ts#L179-L226)

**Problem:** Plugin-to-plugin calls (including token issuance) have no circuit breaker, retry, or timeout mechanisms:
- The `isTargetPluginSupported` check fetches JWKS via plain `fetch()` with no timeout
- Failed JWKS fetches are not cached or retried with backoff
- In-flight check deduplication (`targetPluginInflightChecks`) doesn't prevent thundering herd on recovery

```typescript
// Plain fetch with no timeout, retry, or circuit breaker
const res = await fetch(
  `${await this.discovery.getBaseUrl(targetPluginId)}/.backstage/auth/v1/jwks.json`,
);
```

**Impact:** A slow or unreachable plugin can cause cascading latency across all plugins that try to communicate with it.

---

### 5. Cache Has No Eviction Policy Control

**File:** [`CacheClient.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/cache/CacheClient.ts)

**Problem:** The `CacheService` interface exposes only basic `get/set/delete` with TTL. There is no:
- Maximum cache size / memory limit
- Eviction policy control (LRU, LFU, etc.)
- Cache warming / pre-population
- Cache statistics / monitoring
- Cache invalidation across multiple instances (no pub/sub invalidation)

**Impact:** In-memory caches can grow unbounded. In multi-instance deployments, cache inconsistency is inevitable since there is no cross-instance invalidation.

---

### 6. Express Dependency — Tight HTTP Framework Coupling

**File:** [`HttpAuthService.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-plugin-api/src/services/definitions/HttpAuthService.ts#L17)

```typescript
import type { Request, Response } from 'express';
```

**Problem:** The **public API** of core services (`HttpAuthService`, `HttpRouterService`) is tightly coupled to Express.js types:
- `Request` and `Response` from `express` are used directly in service interfaces
- This makes it impossible to swap HTTP frameworks (Fastify, Hono, Koa) without breaking the entire plugin ecosystem
- Express.js is a minimally maintained framework with known performance limitations

**Impact:** Framework lock-in. Express is the slowest major Node.js HTTP framework, and the architecture prevents migration.

---

### 7. Single-Threaded Scheduler for Background Tasks

**File:** [`SchedulerService.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-plugin-api/src/services/definitions/SchedulerService.ts)

**Problem:** The scheduler runs all tasks on the same Node.js event loop:
- Task functions run in-process and block the event loop
- No worker thread or subprocess isolation for CPU-intensive tasks
- `AbortSignal` is the only cancellation mechanism — cannot forcefully terminate a runaway task
- The `timeout` only "releases" the lock for other workers; it doesn't kill the running task

```typescript
// Task is just a function running on the main event loop
export type SchedulerServiceTaskFunction =
  | ((abortSignal: AbortSignal) => void | Promise<void>)
  | (() => void | Promise<void>);
```

**Impact:** A long-running or CPU-intensive scheduled task (e.g., full catalog refresh) blocks the entire backend's event loop.

---

### 8. No Observability Built into Core Services

**Files:** All service definitions under [`definitions/`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-plugin-api/src/services/definitions)

**Problem:** Core services (Auth, Database, Cache, Scheduler, Discovery) have no built-in observability:
- No metrics (request counts, latencies, error rates)
- No distributed tracing spans
- No health status reporting
- The `LoggerService` is the only observability tool, but logging alone is insufficient for production monitoring
- `metricsServiceFactory` and `tracingServiceFactory` are alpha-only and not integrated into core services

**Impact:** Operators have limited visibility into the health and performance of individual services, making production debugging extremely difficult.

---

### 9. Synchronous Config Loading — No Config Validation Pipeline

**File:** [`loader.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/config-loader/src/loader.ts)

**Problem:** Configuration is loaded as raw YAML/JSON and passed through with minimal type-safe validation:
- Config schema validation is optional and schema-driven, but many configuration values are validated only at runtime
- There is no startup validation that catches misconfiguration early
- Config hot-reload (`onChange`) provides no rollback on invalid config
- Secrets substitution (`experimentalEnvFunc`) uses untyped string interpolation

```typescript
// Config reload failure is just logged, not rolled back
} catch (error) {
  if (loaded) {
    console.error(`Failed to reload configuration, ${error}`);
  }
```

**Impact:** Misconfigurations are often only discovered when a request hits the affected code path, potentially in production.

---

### 10. Lifecycle Management Lacks Ordered Dependency Shutdown

**File:** [`LifecycleService.ts`](file:///Users/binhnt/Lab/dev/backstage/packages/backend-plugin-api/src/services/definitions/LifecycleService.ts)

**Problem:** The lifecycle service provides simple hooks (`addShutdownHook`, `addBeforeShutdownHook`) but has no:
- Dependency-aware shutdown ordering
- Timeout enforcement on shutdown hooks
- Health status degradation during shutdown
- Readiness/liveness probe differentiation

**Impact:** During graceful shutdown, database connections may be closed before in-flight requests complete, HTTP connections may drop ungracefully, and scheduled tasks may be interrupted mid-execution.
