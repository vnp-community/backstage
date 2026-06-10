# Backstage Architecture Weaknesses Analysis

> **Date**: 2026-05-28
> **Scope**: Core packages (`packages/`), plugin architecture (`plugins/`), backend & frontend systems
> **Method**: Static code analysis and architectural pattern review

---

## Table of Contents

1. [Dual Frontend System — Migration Tax](#1-dual-frontend-system--migration-tax)
2. [Cross-Package Boundary Violations](#2-cross-package-boundary-violations)
3. [Service Registry — Runtime DI Without Compile-Time Safety](#3-service-registry--runtime-di-without-compile-time-safety)
4. [Lifecycle Management — Hacky Internal Casts](#4-lifecycle-management--hacky-internal-casts)
5. [Monolithic Backend Process Model](#5-monolithic-backend-process-model)
6. [Database Coupling via Knex](#6-database-coupling-via-knex)
7. [Global Singleton Anti-Pattern](#7-global-singleton-anti-pattern)
8. [Plugin Discovery via HTTP — Single Point of Failure](#8-plugin-discovery-via-http--single-point-of-failure)
9. [Config System — Runtime Type Unsafety](#9-config-system--runtime-type-unsafety)
10. [Scheduler — Database-Bound Distributed Locking](#10-scheduler--database-bound-distributed-locking)
11. [Massive Plugin Surface Area — Maintainability Debt](#11-massive-plugin-surface-area--maintainability-debt)
12. [Frontend Extension Tree — Complexity Cliff](#12-frontend-extension-tree--complexity-cliff)
13. [Backward Compatibility Layers — Accumulated Cruft](#13-backward-compatibility-layers--accumulated-cruft)
14. [Process-Level Error Handling](#14-process-level-error-handling)
15. [Auth Architecture — Late-Binding Token Design](#15-auth-architecture--late-binding-token-design)
16. [CSP Weakened by Design — `unsafe-eval` Default](#16-csp-weakened-by-design--unsafe-eval-default)
17. [CommonJS/ESM Dual-Module Tax](#17-commonjsesm-dual-module-tax)
18. [Events System — HTTP Polling Anti-Pattern](#18-events-system--http-polling-anti-pattern)
19. [Scheduler — SQL Dialect Branching in Application Code](#19-scheduler--sql-dialect-branching-in-application-code)
20. [Cache Service — Missing Bulk & Observability APIs](#20-cache-service--missing-bulk--observability-apis)

---

## 1. Dual Frontend System — Migration Tax

### Location
- `packages/core-plugin-api` (old system, `core-` prefix)
- `packages/frontend-plugin-api` (new system, `frontend-` prefix)
- `packages/core-compat-api` (bridge layer)
- `packages/app-legacy` vs `packages/app`

### Problem
Backstage maintains **two complete frontend systems** simultaneously:
- The **old frontend system** (`core-plugin-api`, `core-app-api`, `core-components`)
- The **new frontend system** (`frontend-plugin-api`, `frontend-app-api`, `frontend-internal`)
- A **compatibility bridge** (`core-compat-api`) with 20+ files of conversion logic

This creates a tripled surface area for any frontend-touching change and forces every plugin author to understand both systems. The `core-compat-api` package contains complex converters like `convertLegacyRouteRef.ts` (8,939 bytes), `collectLegacyRoutes.tsx` (9,686 bytes), and `convertLegacyApp.ts` (5,520 bytes) — all of which are pure migration ceremony.

### Impact
- **Developer cognitive load**: Contributors must learn both systems
- **Bug surface**: Changes can break in one system but not the other
- **Maintenance cost**: Every core feature needs to work across both systems
- **Testing burden**: Two test suites for similar functionality

### Severity: HIGH

---

## 2. Cross-Package Boundary Violations

### Location
- `packages/backend-app-api/src/wiring/BackendInitializer.ts` (lines 34-41)
- `packages/backend-app-api/src/wiring/ServiceRegistry.ts` (lines 25-26)
- `packages/frontend-app-api/src/wiring/prepareSpecializedApp.tsx` (line 39-43)
- `packages/frontend-test-utils/src/app/createExtensionTester.tsx` (6 violations)
- 50+ total occurrences across the monorepo

### Problem
Critical infrastructure packages bypass their own module boundaries using relative path imports that cross package boundaries, each one suppressing the `@backstage/no-relative-monorepo-imports` eslint rule:

```typescript
// BackendInitializer.ts
// eslint-disable-next-line @backstage/no-relative-monorepo-imports
import type {
  InternalBackendFeature,
  InternalBackendFeatureLoader,
  InternalBackendRegistrations,
} from '../../../backend-plugin-api/src/wiring/types';
```

These imports create **hidden coupling** between packages that the package system should prevent. They bypass the public API surface, meaning internal refactors in one package can silently break another.

### Impact
- **Fragile builds**: Internal refactors in `backend-plugin-api` can break `backend-app-api`
- **API surface lie**: The published API reports don't reflect actual dependencies
- **Versioning impossible**: Packages can't be independently versioned without risk
- **Testing gaps**: Unit tests for one package don't cover the cross-boundary contract

### Severity: HIGH

---

## 3. Service Registry — Runtime DI Without Compile-Time Safety

### Location
- `packages/backend-app-api/src/wiring/ServiceRegistry.ts`
- `packages/backend-plugin-api/src/services/system/types.ts`

### Problem
The `ServiceRegistry` implements a **runtime-only dependency injection** system. Service dependencies are resolved by string ID at runtime, with no compile-time verification that all dependencies are satisfied:

```typescript
// ServiceRegistry.ts — Type safety is lost through string-keyed maps
readonly #providedFactories: Map<string, InternalServiceFactory[]>;
readonly #implementations: Map<InternalServiceFactory, {
  context: Promise<unknown>;  // <-- All type info lost
  byPlugin: Map<string, Promise<unknown>>;  // <-- Generic unknown
}>;
```

The `InternalServiceRef` type uses a duck-typing pattern for default factories:

```typescript
export type InternalServiceRef = ServiceRef<unknown> & {
  __defaultFactory?: (
    service: ServiceRef<unknown>,
  ) => Promise<ServiceFactory | (() => ServiceFactory)>;
};
```

This means missing service implementations are only discovered at startup time, not at compile time.

### Impact
- **Late failure**: Missing services cause runtime crashes instead of compile errors
- **Debugging difficulty**: Error messages like "service X is missing for plugin Y" require stack trace analysis
- **Circular dependency detection**: Only happens at runtime via `DependencyGraph`, not statically

### Severity: MEDIUM

---

## 4. Lifecycle Management — Hacky Internal Casts

### Location
- `packages/backend-app-api/src/wiring/BackendInitializer.ts` (lines 602-647)

### Problem
The `BackendInitializer` relies on **unsafe type casts** to access internal lifecycle methods. The code has a self-aware comment acknowledging this:

```typescript
// Bit of a hacky way to grab the lifecycle services, potentially find a nicer way to do this
async #getRootLifecycleImpl(): Promise<
  RootLifecycleService & {
    startup(): Promise<void>;
    beforeShutdown(): Promise<void>;
    shutdown(): Promise<void>;
  }
> {
  const lifecycleService = await this.#serviceRegistry.get(
    coreServices.rootLifecycle,
    'root',
  );
  const service = lifecycleService as any;  // <-- unsafe cast
  if (
    service &&
    typeof service.startup === 'function' &&
    typeof service.shutdown === 'function'
  ) {
    return service;
  }
  throw new Error('Unexpected root lifecycle service implementation');
}
```

The same pattern repeats for `#getPluginLifecycleImpl`. This means the backend's critical startup/shutdown coordination depends on runtime duck-typing of service implementations rather than compile-time interface contracts.

### Impact
- **Silent breakage**: A custom lifecycle service that doesn't implement `startup()`/`shutdown()` crashes at runtime
- **Violation of service abstraction**: The initializer assumes internal details of the lifecycle service
- **No contract enforcement**: Custom implementations have no way to know they need these extra methods

### Severity: MEDIUM

---

## 5. Monolithic Backend Process Model

### Location
- `packages/backend-app-api/src/wiring/BackendInitializer.ts`
- `packages/backend-defaults/src/CreateBackend.ts`

### Problem
All backend plugins run in a **single Node.js process**. The `BackendInitializer` initializes all plugins in parallel within the same event loop:

```typescript
// All plugins are initialized in parallel
await Promise.all(
  [...pluginInits.keys()].map(async pluginId => {
    // ... initialize all plugins in the same process
  }),
);
```

There is no plugin isolation — a CPU-heavy or memory-leaking plugin degrades all other plugins. The `InstanceRegistry` (line 64-106) manages process signals globally, meaning all backend instances share the same signal handlers.

Furthermore, the `unhandledRejection` and `uncaughtException` handlers are shared:
```typescript
process.on('unhandledRejection', this.#unhandledRejectionHandler);
process.on('uncaughtException', this.#uncaughtExceptionHandler);
```

### Impact
- **No fault isolation**: One plugin's OOM kills all plugins
- **Scaling bottleneck**: Cannot scale individual plugins independently
- **Deployment inflexibility**: Must redeploy everything for any plugin change
- **Resource contention**: CPU/memory/event-loop shared across all plugins

### Severity: MEDIUM (mitigated by BEP-0005 split backend discovery proposal, but not yet fully implemented)

---

## 6. Database Coupling via Knex

### Location
- `packages/backend-plugin-api/src/services/definitions/DatabaseService.ts`

### Problem
The `DatabaseService` interface is tightly coupled to `Knex`:

```typescript
import { Knex } from 'knex';

export interface DatabaseService {
  getClient(): Promise<Knex>;
  migrations?: {
    skip?: boolean;
  };
}
```

This means:
1. Every plugin that needs a database must use Knex
2. There's no abstraction for different storage backends (e.g., document stores, key-value stores)
3. Migration management is baked into the service interface with a minimal `skip` flag
4. Plugin authors can't use Prisma, TypeORM, or any other ORM without wrapping Knex

### Impact
- **Vendor lock-in**: All storage must go through Knex/SQL
- **Performance ceiling**: No native support for specialized databases (Redis, MongoDB, etc.)
- **Migration complexity**: Each plugin manages its own migrations with no centralized coordination
- **Testing overhead**: Tests must set up full database instances

### Severity: MEDIUM

---

## 7. Global Singleton Anti-Pattern

### Location
- `packages/version-bridge/src/lib/globalObject.ts`

### Problem
The `version-bridge` package uses **global mutable state** attached directly to the global object (window/self) for cross-version communication:

```typescript
function getGlobalObject() {
  if (typeof window !== 'undefined' && window.Math === Math) return window;
  if (typeof self !== 'undefined' && self.Math === Math) return self;
  return Function('return this')();  // <-- eval equivalent
}

const globalObject = getGlobalObject();
const makeKey = (id: string) => `__@backstage/${id}__`;

export function getOrCreateGlobalSingleton<T>(id: string, supplier: () => T): T {
  const key = makeKey(id);
  let value = globalObject[key];
  if (value) return value;
  value = supplier();
  globalObject[key] = value;
  return value;
}
```

Issues:
1. Uses `Function('return this')()` — an eval equivalent that may be blocked by CSP
2. Stores state on the global object with predictable key names (`__@backstage/xxx__`)
3. First-writer-wins semantics with no versioning or conflict detection
4. No cleanup mechanism — singletons persist for the lifetime of the process

### Impact
- **CSP violations**: `Function('return this')()` may be blocked by Content Security Policy
- **Memory leaks**: Singletons never get garbage collected
- **Collision risk**: Predictable keys can collide with other libraries
- **Testing pollution**: Global state leaks between test suites

### Severity: LOW-MEDIUM

---

## 8. Plugin Discovery via HTTP — Single Point of Failure

### Location
- `packages/backend-plugin-api/src/services/definitions/DiscoveryService.ts`

### Problem
Inter-plugin communication relies on the `DiscoveryService` which resolves plugin endpoints via URL:

```typescript
export interface DiscoveryService {
  getBaseUrl(pluginId: string): Promise<string>;
  getExternalBaseUrl(pluginId: string): Promise<string>;
}
```

The docstring explicitly states: "This method must always be called just before making each request." This means:
1. Every inter-plugin call requires a discovery lookup + HTTP request
2. If the discovery service is slow or down, all inter-plugin communication fails
3. There's no in-process communication path even when plugins are co-located

### Impact
- **Latency overhead**: Every plugin-to-plugin call goes through HTTP even when co-located
- **Availability dependency**: Discovery service is a SPOF for all internal communication
- **No gRPC/binary protocol**: Forces JSON/HTTP for all inter-plugin calls
- **Network partition sensitivity**: Co-located plugins can't communicate if the network stack is impaired

### Severity: MEDIUM

---

## 9. Config System — Runtime Type Unsafety

### Location
- `packages/config/src/types.ts`

### Problem
The `Config` interface uses runtime string-key lookups with no compile-time schema validation:

```typescript
export type Config = {
  get<T = JsonValue>(key?: string): T;
  getOptional<T = JsonValue>(key?: string): T | undefined;
  getString(key: string): string;
  getOptionalString(key: string): string | undefined;
  getNumber(key: string): number;
  // ... etc
};
```

Key weaknesses:
1. `get<T>()` accepts any type `T` with no runtime validation — the generic is a lie
2. Config keys are untyped strings, so typos are only caught at runtime
3. The `subscribe()` method is **optional** (`subscribe?(onChange: ...)`), meaning consumers must feature-detect it
4. No schema-driven code generation for type-safe config access
5. `filteredKeys` and `deprecatedKeys` are informational only — no enforcement

### Impact
- **Runtime config errors**: Typos in config keys cause runtime crashes
- **No IDE autocompletion**: Config keys are opaque strings
- **Silent type mismatches**: `get<number>('port')` will happily return a string
- **Deprecation ignorable**: Deprecated keys have no enforcement mechanism

### Severity: MEDIUM

---

## 10. Scheduler — Database-Bound Distributed Locking

### Location
- `packages/backend-plugin-api/src/services/definitions/SchedulerService.ts`

### Problem
The `SchedulerService` uses database-backed locking for distributed task coordination. The `scope: 'global'` setting relies on the database to prevent concurrent execution across workers:

```typescript
export interface SchedulerServiceTaskScheduleDefinition {
  frequency: { cron: string } | Duration | HumanDuration | { trigger: 'manual' };
  timeout: Duration | HumanDuration;
  scope?: 'global' | 'local';
}
```

Issues:
1. Global lock coordination requires all workers to share the same database
2. Lock acquisition/release adds latency to every scheduled task
3. No support for Redis-based or external locking mechanisms via the interface
4. The `timeout` is the only mechanism for recovering stuck locks — no heartbeat

Additionally, the `readFrequency` function (line 365-381) uses unsafe type assertions:
```typescript
if (typeof value === 'object' && (value as { cron?: string }).cron) {
  return value as { cron: string };
}
```

### Impact
- **Database bottleneck**: All workers compete for database locks
- **Clock skew sensitivity**: Timeout-based lock recovery is sensitive to clock drift
- **No horizontal scalability**: Can't use external lock managers like Redis/Zookeeper
- **Stuck task risk**: If a worker dies without releasing a lock, tasks are blocked until timeout

### Severity: LOW-MEDIUM

---

## 11. Massive Plugin Surface Area — Maintainability Debt

### Location
- `plugins/` directory (155+ plugin packages)

### Problem
The monorepo contains **155+ plugin packages**, many of which follow a proliferating pattern:
- `plugin-X` (frontend)
- `plugin-X-backend` (backend)
- `plugin-X-common` (shared types)
- `plugin-X-node` (backend utilities)
- `plugin-X-react` (frontend utilities)
- `plugin-X-backend-module-Y` (per-provider modules, e.g., 21 auth provider modules)

For example, the auth system alone has:
- `auth`, `auth-backend`, `auth-node`, `auth-react`
- Plus **21 separate provider modules** (GitHub, Google, Okta, etc.)

The `yarn.lock` is **1.83MB**, indicating a massive dependency tree.

### Impact
- **Dependency hell**: 1.83MB yarn.lock with complex resolution rules and 18+ `resolutions` patches
- **Release complexity**: Each non-private package needs changesets, API reports, and independent versioning
- **CI/CD time**: Building and testing 155+ packages is slow
- **Contributor confusion**: Hard to find where functionality lives across 5+ related packages

### Severity: MEDIUM

---

## 12. Frontend Extension Tree — Complexity Cliff

### Location
- `packages/frontend-app-api/src/wiring/prepareSpecializedApp.tsx` (931 lines)
- `packages/frontend-app-api/src/tree/`

### Problem
The new frontend system's extension tree has enormous complexity:

1. `prepareSpecializedApp.tsx` is **931 lines** of deeply nested initialization logic with multiple lifecycle phases (bootstrap → finalization)
2. The file manages:
   - Feature deduplication
   - Sign-in flow orchestration
   - Identity API proxying
   - Predicate context loading
   - API factory collection and synchronization
   - Bootstrap classification
   - Error collection
   - Finalization callbacks
3. Uses complex internal state machines with terms like "FinalizationController", "BootstrapClassification", "PredicateContextLoader"
4. Multiple async lifecycle transitions with subtle ordering requirements

### Impact
- **Onboarding barrier**: New contributors cannot understand the frontend initialization
- **Debugging nightmare**: Multiple async phases make bugs hard to reproduce
- **Testing difficulty**: The 58KB test file (`createSpecializedApp.test.tsx`) indicates the complexity
- **Extension overhead**: Simple UI extensions require understanding the full tree lifecycle

### Severity: MEDIUM

---

## 13. Backward Compatibility Layers — Accumulated Cruft

### Location
- `packages/backend-app-api/src/wiring/BackendInitializer.ts` (lines 757-783)
- `packages/backend-plugin-api/src/wiring/types.ts` (4 registration types: plugin, module, plugin-v1.1, module-v1.1)

### Problem
The codebase maintains multiple versioned internal types side by side:

```typescript
export interface InternalBackendPluginRegistration { type: 'plugin'; ... }
export interface InternalBackendModuleRegistration { type: 'module'; ... }
export interface InternalBackendPluginRegistrationV1_1 { type: 'plugin-v1.1'; ... }
export interface InternalBackendModuleRegistrationV1_1 { type: 'module-v1.1'; ... }
```

The `BackendInitializer.#enumerateRegistrations` must handle all 4 types:
```typescript
if (r.type === 'plugin' || r.type === 'module') {
  // Handle v1 format
} else if (r.type === 'plugin-v1.1' || r.type === 'module-v1.1') {
  // Handle v1.1 format
}
```

Additionally, the feature type detection uses duck-typing as a fallback:
```typescript
function isServiceFactory(feature: BackendFeature): feature is InternalServiceFactory {
  const internal = toInternalBackendFeature(feature);
  if (internal.featureType === 'service') return true;
  // Backwards compatibility for v1 registrations that use duck typing
  return 'service' in internal;
}
```

### Impact
- **Code duplication**: Every registration handler has two paths
- **Subtle bugs**: Behavior differences between v1 and v1.1 are hard to spot
- **Growing tech debt**: Each new version adds another branch without removing old ones
- **Duck-typing fragility**: `'service' in internal` can false-positive on unrelated objects

### Severity: LOW-MEDIUM

---

## 14. Process-Level Error Handling

### Location
- `packages/backend-app-api/src/wiring/BackendInitializer.ts` (lines 294-318)

### Problem
The backend registers global process event handlers that swallow critical errors:

```typescript
if (process.env.NODE_ENV !== 'test') {
  process.on('unhandledRejection', this.#unhandledRejectionHandler);
  process.on('uncaughtException', this.#uncaughtExceptionHandler);
}
```

These handlers only **log** errors — they don't crash the process. While this prevents unexpected termination, it means:
1. Memory corruption from uncaught exceptions is masked
2. Broken invariants continue to operate in an undefined state
3. No crash-and-restart recovery loop (process stays up in broken state)

The instance registry's exit handler also has a potential race condition:
```typescript
#exitHandler = async () => {
  try {
    const results = await Promise.allSettled(
      Array.from(this.#instances).map(b => b.stop()),
    );
    // ... process.exit() after all promises settle
  } catch (error) {
    process.exit(1);
  }
};
```

Signal handlers are async, but `process.exit()` may be called before all async cleanup completes if another signal arrives.

### Impact
- **Zombie processes**: Process stays up after critical failures
- **State corruption**: Uncaught exceptions don't trigger recovery
- **Signal race**: Multiple SIGTERM signals can cause double-exit
- **Test interference**: `NODE_ENV !== 'test'` check means different behavior in tests vs production

### Severity: MEDIUM

---

## 15. Auth Architecture — Late-Binding Token Design

### Location
- `packages/backend-plugin-api/src/services/definitions/AuthService.ts`
- `beps/0003-auth-architecture-evolution/README.md`

### Problem
The auth system has several design weaknesses acknowledged in the BEP itself:

1. **Service principal subject is informational-only**:
```typescript
export type BackstageServicePrincipal = {
  type: 'service';
  subject: string; // Exact format TBD, possibly 'plugin:<pluginId>'
  // "This string is only informational, has no well defined semantics,
  //  and should never be used to drive actual logic in code."
};
```

The comment explicitly warns against using `subject` for logic, yet it's the only identifier for service principals.

2. **Access restrictions are optional and additive**:
```typescript
export type BackstagePrincipalAccessRestrictions = {
  permissionNames?: string[];   // optional
  permissionAttributes?: { ... }; // optional
};
```

If no restrictions are set, "the principal is assumed to have unlimited access."

3. **Token per-request mandate with no caching**:
The `getPluginRequestToken` docstring says "This method should be called before each request. Do not hold on to the issued token." This means every inter-plugin HTTP call requires a token generation step, adding latency.

4. **Legacy symmetric key usage**: The BEP acknowledges still using `HS256` symmetric keys for service-to-service auth, while the user tokens use `ES256` asymmetric keys.

### Impact
- **Confused authorization model**: `subject` exists but shouldn't be used for authorization
- **Default-open security**: Missing restrictions = unlimited access
- **Performance overhead**: Token generation per request
- **Mixed crypto model**: Symmetric and asymmetric keys in the same system

### Severity: MEDIUM

---

## 16. CSP Weakened by Design — `unsafe-eval` Default

### Location
- `packages/backend-defaults/src/entrypoints/rootHttpRouter/http/readHelmetOptions.ts` (lines 95-102)

### Problem
The default Content Security Policy (CSP) configuration **explicitly includes `unsafe-eval`** in the `script-src` directive:

```typescript
// TODO(Rugvip): We currently use non-precompiled AJV for validation in the frontend, which uses eval.
//               It should be replaced by any other solution that doesn't require unsafe-eval.
result['script-src'] = ["'self'", "'unsafe-eval'"];

// TODO(Rugvip): This is removed so that we maintained backwards compatibility
//               when bumping to helmet v5, we could remove this as well as
//               skip setting `useDefaults: false` in the future.
delete result['form-action'];
```

Additionally, four Helmet security headers are explicitly disabled for "backwards compatibility":
```typescript
crossOriginEmbedderPolicy: false,
crossOriginOpenerPolicy: false,
crossOriginResourcePolicy: false,
originAgentCluster: false,
```

These are accompanied by a TODO acknowledging the problem. The `form-action` directive is also deleted entirely.

### Impact
- **XSS vulnerability surface**: `unsafe-eval` allows `eval()`, `Function()`, and `setTimeout(string)` — the most common XSS exploitation vectors
- **CSP bypass**: Attackers who achieve any code injection can execute arbitrary JavaScript
- **CORS weakened**: Disabled cross-origin policies remove browser-level isolation
- **Stale debt**: TODOs from the helmet v5 bump remain unresolved

### Severity: HIGH

---

## 17. CommonJS/ESM Dual-Module Tax

### Location
- `packages/backend-app-api/src/wiring/helpers.ts` (lines 20-36)
- Pervasive across the monorepo's build pipeline

### Problem
The codebase must handle **CommonJS/ESM interop** at runtime because the build output is CommonJS while modern packages use ESM:

```typescript
export function unwrapFeature(
  feature: BackendFeature | { default: BackendFeature },
): BackendFeature {
  if ('$$type' in feature) {
    return feature;
  }

  // This is a workaround where default exports get transpiled to `exports['default'] = ...`
  // in CommonJS modules, which in turn results in a double `{ default: { default: ... } }` nesting
  // when importing using a dynamic import.
  // TODO: This is a broader issue than just this piece of code, and should move away from CommonJS.
  if ('default' in feature) {
    return feature.default;
  }

  return feature;
}
```

The `deepFreeze` function in the same file also uses `@ts-expect-error` to suppress TypeScript errors caused by this interop:
```typescript
export function deepFreeze<T>(obj: T) {
  // Can cause: "Type instantiation is excessively deep and possibly infinite."
  // @ts-expect-error
  Object.values(obj).forEach(
    value => Object.isFrozen(value) || deepFreeze(value),
  );
  return Object.freeze(obj) as DeepReadonly<T>;
}
```

### Impact
- **Runtime fragility**: Double-default-wrapping (`{ default: { default: ... } }`) is a common source of mysterious failures
- **Plugin loading bugs**: Third-party plugins may encounter unexpected module format issues
- **Build complexity**: Must support both module systems throughout the toolchain
- **Type suppression**: `@ts-expect-error` hides potentially real type issues

### Severity: MEDIUM

---

## 18. Events System — HTTP Polling Anti-Pattern

### Location
- `plugins/events-node/src/api/DefaultEventsService.ts` (lines 198-330)

### Problem
The events system uses **HTTP long-polling** for cross-instance event delivery instead of WebSockets or a proper message queue:

```typescript
#startPolling(
  subscriptionId: string,
  topics: string[],
  onEvent: EventsServiceSubscribeOptions['onEvent'],
) {
  let backoffMs = POLL_BACKOFF_START_MS;  // 1 second
  const poll = async () => {
    // ... HTTP GET to events backend
    const res = await client.getSubscriptionEvents({ ... });
    if (res.status === 202) {
      // 202 = no events, response blocks until timeout or new events
      await Promise.race([res.text(), timeout]);
    }
    // ...
    process.nextTick(poll);  // immediately re-poll
  };
  poll();
}
```

Issues:
1. **HTTP overhead per event**: Each poll cycle involves full HTTP request/response lifecycle
2. **`process.nextTick(poll)`**: Recursive polling without any delay on success creates tight loops
3. **Error handling via string matching**: Auth failures are detected by string comparison (`String(error).includes('Unable to generate legacy token')`) — extremely fragile
4. **No event ordering guarantees**: Events from multiple polls can arrive out of order
5. **Graceful degradation via `delete this.client`**: When the events backend returns 404, the client reference is deleted, silently switching to local-only mode

### Impact
- **Resource waste**: Constant HTTP polling consumes bandwidth and CPU
- **Latency**: Up to 1-second delay for event delivery (backoff start)
- **Scalability limit**: Each subscriber creates an independent polling loop
- **Silent mode switches**: `delete this.client` silently degrades to local-only without explicit user notification beyond a log warning

### Severity: MEDIUM

---

## 19. Scheduler — SQL Dialect Branching in Application Code

### Location
- `packages/backend-defaults/src/entrypoints/scheduler/lib/TaskWorker.ts` (lines 479-514)

### Problem
The `TaskWorker` contains **raw SQL dialect-specific branching** directly in application logic instead of using a proper database abstraction:

```typescript
private static computeNextRunStartAt(knex: Knex, settings: TaskSettingsV2): Knex.Raw {
  // ...
  if (knex.client.config.client.includes('sqlite3')) {
    return knex.raw(`max(datetime(next_run_start_at, ?), datetime('now'))`, [
      `+${dt} seconds`,
    ]);
  }

  if (knex.client.config.client.includes('mysql')) {
    return knex.raw(
      `greatest(next_run_start_at + interval ${dt} second, now())`,
    );
  }

  return knex.raw(
    `greatest(next_run_start_at + interval '${dt} seconds', now())`,
  );
}
```

This pattern repeats in `nextRunAtRaw()`, `persistTask()` (MySQL vs Postgres `onConflict` handling), and the `findReadyTask()` method. The dialect-sniffing uses string matching (`knex.client.config.client.includes('sqlite3')`) which is fragile.

### Impact
- **Database vendor lock-in**: Adding a new database requires touching application code in multiple places
- **SQL injection risk**: `${dt}` in the MySQL raw query is string-interpolated rather than parameterized
- **Testing complexity**: Each database dialect needs separate test paths
- **Maintenance burden**: SQL dialect branches are scattered across 5+ methods in the file

### Severity: LOW-MEDIUM

---

## 20. Cache Service — Missing Bulk & Observability APIs

### Location
- `packages/backend-plugin-api/src/services/definitions/CacheService.ts`

### Problem
The `CacheService` interface is minimalistic to the point of being incomplete for production use:

```typescript
export interface CacheService {
  get<TValue extends JsonValue>(key: string): Promise<TValue | undefined>;
  set(key: string, value: JsonValue, options?: CacheServiceSetOptions): Promise<void>;
  delete(key: string): Promise<void>;
  withOptions(options: CacheServiceOptions): CacheService;
}
```

Missing capabilities:
1. **No bulk operations**: `getMany(keys[])`, `setMany(entries[])`, `deleteMany(keys[])` — required for efficient batch operations
2. **No `has()` method**: Must do `get()` + null check, which may deserialize large values unnecessarily
3. **No enumeration**: Cannot list keys, check cache size, or iterate over entries
4. **No observability**: No cache hit/miss statistics, no eviction callbacks, no size metrics
5. **No invalidation patterns**: No `clear()`, `invalidateByPattern()`, or tag-based invalidation
6. **Forced `JsonValue` serialization**: Cannot cache non-JSON-serializable objects (Buffers, Streams, etc.)
7. **Silent failure model**: No way to distinguish "key doesn't exist" from "cache backend is down"

### Impact
- **N+1 cache calls**: Plugins doing batch lookups must issue N individual `get()` calls
- **No operational visibility**: Operators cannot monitor cache health or hit rates
- **Limited adoption**: Plugins avoid the cache service for non-trivial use cases
- **No graceful degradation**: Cache failures and cache misses are indistinguishable

### Severity: LOW-MEDIUM

---

## Summary by Severity

| Severity | Count | Key Issues |
|----------|-------|------------|
| **HIGH** | 3 | Dual frontend system, cross-package violations, CSP `unsafe-eval` default |
| **MEDIUM** | 11 | Service registry type safety, monolithic process, database coupling, config unsafety, auth design, error handling, plugin surface area, frontend complexity, discovery SPOF, CommonJS/ESM tax, events polling |
| **LOW-MEDIUM** | 6 | Global singletons, scheduler locking, backward compat cruft, scheduler SQL branching, cache service gaps |

---

## Recommendations

### Short-term (tactical)
1. **Eliminate `unsafe-eval` from CSP** by switching to precompiled AJV or alternative JSON schema validation
2. **Eliminate cross-package relative imports** by extracting shared internal types into a dedicated `@internal/*` package (partially done with `@internal/backend` and `@internal/frontend`)
3. **Add compile-time service dependency validation** in the CLI or build step
4. **Replace `as any` casts** in lifecycle management with proper internal interfaces
5. **Re-enable Helmet security headers** (`crossOriginEmbedderPolicy`, `crossOriginOpenerPolicy`, etc.)

### Medium-term (strategic)
6. **Sunset the old frontend system** and remove `core-compat-api`
7. **Abstract the database service** to support non-Knex storage backends
8. **Replace global singletons** with a proper module-scoped context
9. **Add crash-on-uncaught-exception** mode as default, with opt-in suppression
10. **Migrate to ESM-first** build pipeline to eliminate CommonJS interop workarounds
11. **Replace HTTP polling** in events system with WebSocket or SSE for cross-instance events
12. **Extend cache service** with bulk operations, observability hooks, and pattern-based invalidation

### Long-term (architectural)
13. **Support process isolation** for plugins (via worker threads or separate processes)
14. **Replace HTTP-based inter-plugin communication** with in-process calls when co-located
15. **Implement schema-driven config** with code generation for type-safe access
16. **Migrate to asymmetric service-to-service auth** throughout
17. **Abstract SQL dialect logic** into a proper database abstraction layer for the scheduler
