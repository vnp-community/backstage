# Limitation: Cross-Cutting & Infrastructure Concerns

## Packages
`@backstage/backend-defaults`, `@backstage/backend-app-api`, `@backstage/cli`, `@backstage/types`

---

## L-INF-001: Jest Worker Memory Leaks Require Workaround

**Severity**: Medium  
**Type**: Testing Infrastructure

In `cli-module-test-jest`:

```typescript
// This is because Jest workers leak a lot of memory, and the workaround is to limit worker memory.
```

**Impact**: Test suites for large Backstage deployments consume excessive memory. The CLI must apply memory limits to Jest workers as a workaround.

---

## L-INF-002: Default Export Transpilation Workaround

**Severity**: Low  
**Type**: Build System

Multiple packages contain the same workaround:

```typescript
// This is a workaround where default exports get transpiled to `exports['default'] = ...`
```

Found in `backend-app-api/src/wiring/helpers.ts` and `cli/src/wiring/CliInitializer.ts`.

**Impact**: Dynamic plugin loading may fail if default exports are not handled correctly. The workaround adds fragile runtime checks.

---

## L-INF-003: SQLite Driver Warning Suppression

**Severity**: Low  
**Type**: Workaround

In `backend-defaults/src/entrypoints/database/connectors/sqlite3.ts`:

```typescript
// This is a workaround for the knex SQLite driver always warning when using a config loader
```

**Impact**: Warning messages from the Knex SQLite driver are suppressed, potentially hiding legitimate configuration issues.

---

## L-INF-004: Process Event Listener Cleanup for Memory Leaks

**Severity**: Medium  
**Type**: Resource Management

In `BackendInitializer.ts`:

```typescript
// Clean up process event listeners to prevent memory leaks and duplicate logging
```

**Impact**: The backend must explicitly clean up Node.js process-level event listeners. Without this, hot reloading or test environments may see duplicate log entries and growing event listener counts.

---

## L-INF-005: Rspack Compatibility Issue

**Severity**: Low  
**Type**: Build Tooling

In `cli-module-build`:

```typescript
// FIXME: see also https://github.com/web-infra-dev/rspack/issues/3408
```

**Impact**: Known compatibility issue with Rspack bundler that requires a workaround in the build configuration.

---

## L-INF-006: No Native OpenTelemetry/Tracing in Service Interfaces

**Severity**: High  
**Type**: Observability Gap

None of the core service interfaces (`LoggerService`, `CacheService`, `DatabaseService`, etc.) include built-in tracing or metrics interfaces.

**Impact**:
- Distributed tracing requires manual instrumentation in each plugin
- No request correlation IDs propagated through service boundaries
- No standard metrics collection interface (Prometheus, StatsD, etc.)
- Observability is an afterthought rather than a first-class concern

---

## L-INF-007: No Rate Limiting at Service Layer

**Severity**: High  
**Type**: Missing Feature

Neither `HttpRouterService` nor `HttpAuthService` provides rate limiting:

```typescript
export interface HttpRouterService {
  use(handler: Handler): void;
  addAuthPolicy(policy: HttpRouterServiceAuthPolicy): void;
  // No rate limiting
}
```

**Impact**:
- Plugins are individually responsible for implementing rate limiting
- No protection against abuse or accidental DDoS from misconfigured clients
- The catalog and scaffolder are particularly vulnerable to high-volume requests

---

## L-INF-008: No Built-in Event/Message Bus

**Severity**: High  
**Type**: Architecture Gap

There is no standard event bus or pub/sub mechanism for inter-plugin communication beyond direct HTTP calls via `DiscoveryService`.

**Impact**:
- Plugins cannot react to events from other plugins (e.g., "entity created", "build completed")
- Implementing webhooks or event-driven workflows requires custom infrastructure
- No support for eventual consistency patterns between plugins

---

## L-INF-009: Single-Database Backend Assumption

**Severity**: Medium  
**Type**: Architecture Limitation

The `DatabaseService` assumes a single database engine for all plugins (configured globally):

```typescript
export interface DatabaseService {
  getClient(): Promise<Knex>;
}
```

**Impact**:
- Cannot use different database engines per-plugin (e.g., PostgreSQL for catalog, Redis for search)
- Read replicas are not a native concept
- Connection pool sharing between plugins may lead to resource contention

---

## L-INF-010: Gerrit Test Flakiness Acknowledged

**Severity**: Low  
**Type**: Test Quality

```typescript
// TODO(Rugvip): These tests seem to be a direct or indirect cause of the TaskWorker test flakiness
```

**Impact**: Known test instability in the Gerrit URL reader tests that affects CI reliability.

---

## L-INF-011: No Graceful Degradation Framework

**Severity**: High  
**Type**: Resilience

The lifecycle service provides only startup/shutdown hooks. There is no:
- Circuit breaker pattern
- Bulkhead isolation
- Fallback mechanism
- Degraded mode support

**Impact**: A single slow or failing dependency (e.g., a Git provider being down) can degrade the entire Backstage experience. Individual plugins cannot signal "degraded but available" status.

---

## L-INF-012: `HumanDuration` Type Used Inconsistently

**Severity**: Low  
**Type**: API Inconsistency

Duration fields accept multiple formats inconsistently across the codebase:

```typescript
// SchedulerService uses:
frequency: { cron: string } | Duration | HumanDuration | { trigger: 'manual' };

// Config version uses:
frequency: { cron: string } | string | HumanDuration | { trigger: 'manual' };

// CacheService uses:
ttl?: number | HumanDuration;
```

**Impact**: No single canonical way to express durations. Some accept ISO 8601 strings, some accept Luxon `Duration`, some accept `HumanDuration` objects, and some accept raw milliseconds.
