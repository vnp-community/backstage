# Backstage — Limitations Index

**Date**: 2026-05-28  
**Scope**: `/packages` (69 packages) + `/plugins` (selected key plugins)  
**Total Limitations Found**: 108

---

## Quick Reference Table

| ID | Severity | Package(s) | Summary |
|---|---|---|---|
| L-CFG-001 | Medium | `config` | No config subscription guarantee |
| L-CFG-002 | **High** | `config` | Deep clone on every read — performance overhead |
| L-CFG-003 | Low | `config` | Config key pattern restricts valid characters |
| L-CFG-004 | Low | `config-loader` | Deprecated `loadConfig` API still present |
| L-CFG-005 | Medium | `config-loader` | `experimentalEnvFunc` is unstable |
| L-CFG-006 | Medium | `config` | Array merge strategy replaces instead of merges |
| L-CFG-007 | Medium | `config` | No config validation at load time |
| L-CFG-008 | Low | `config` | `null` value used as delete marker |
| L-ERR-001 | Medium | `errors` | No error code in business errors |
| L-ERR-002 | Medium | `errors` | `ResponseError.fromResponse` assumes body not consumed |
| L-ERR-003 | Low | `errors` | Error serialization depends on third-party library |
| L-ERR-004 | Low | `errors` | Stack traces stripped by default |
| L-ERR-005 | Medium | `errors` | `parseErrorResponseBody` swallows parsing failures silently |
| L-ERR-006 | Low | `errors` | `CustomErrorBase.cause` coerces non-Error causes |
| L-ERR-007 | Low | `errors` | `ConsumedResponse` type includes mutable methods |
| L-ERR-008 | Medium | `errors` | No Retry/Rate-Limit error types |
| L-BPS-001 | **Critical** | `backend-plugin-api` | Monolithic single-process architecture |
| L-BPS-002 | Medium | `backend-plugin-api` | Service discovery is URL-based only |
| L-BPS-003 | **High** | `backend-plugin-api` | Database service returns raw Knex client (abstraction leak) |
| L-BPS-004 | Medium | `backend-plugin-api` | Cache service has minimal API surface |
| L-BPS-005 | Medium | `backend-plugin-api` | Scheduler service lacks robust task management |
| L-BPS-006 | Medium | `backend-plugin-api` | Auth token must be fetched per-request |
| L-BPS-007 | Low | `backend-plugin-api` | Logger service has minimal interface |
| L-BPS-008 | **High** | `backend-plugin-api` | HttpRouterService bound to Express.js |
| L-BPS-009 | Medium | `backend-plugin-api` | Extension point registration order matters |
| L-BPS-010 | Low | `backend-plugin-api` | `UrlReaderService.stream()` is optional |
| L-BPS-011 | Medium | `backend-plugin-api` | LifecycleService has no health check integration |
| L-BPS-012 | Low | `backend-plugin-api` | Plugin ID validation lenient with legacy pattern |
| L-BPS-013 | **High** | `backend-plugin-api` | No service versioning or API contracts |
| L-CAT-001 | Medium | `catalog-model` | Entity name hard limited to 63 characters |
| L-CAT-002 | Low | `catalog-model` | Entity ref always lowercased |
| L-CAT-003 | Medium | `catalog-model` | Entity `spec` is untyped `JsonObject` |
| L-CAT-004 | Low | `catalog-model` | Entity kind type guards use string comparison |
| L-CAT-005 | Low | `catalog-model` | Tag validation is restrictive |
| L-CAT-006 | Medium | `catalog-model` | `EntityMeta` extends `JsonObject` (duck typing risk) |
| L-CAT-007 | **High** | `catalog-client` | `getLocationByRef` loads all locations (O(N)) |
| L-CAT-008 | Medium | `catalog-client` | Entity ref chunking is sequential (not parallel) |
| L-CAT-009 | Low | `catalog-client` | Deprecated `getEntityByName` overdue for removal |
| L-CAT-010 | Medium | `catalog-client` | No cursor opacity for query pagination |
| L-CAT-011 | Medium | `catalog-model` | No namespace enforcement |
| L-CAT-012 | Medium | `catalog-model` | Entity relations are unidirectional in model |
| L-URL-001 | Medium | `backend-defaults` | Azure URL reader missing ETag support |
| L-URL-002 | Medium | `backend-defaults` | Google GCS URL reader missing ETag support |
| L-URL-003 | Medium | `backend-defaults` | Azure URL reader lacks filepath-based tree reading |
| L-URL-004 | **High** | `backend-defaults` | BitbucketServer/Azure/Cloud search reads entire repo into memory |
| L-URL-005 | Medium | `backend-defaults` | AbortSignal support is inconsistent across readers |
| L-URL-006 | Medium | `backend-plugin-api` | `readTree.dir()` caller must manually clean up temp dirs |
| L-URL-007 | Low | `backend-defaults` | Signal casting workaround for node-fetch (7 files) |
| L-URL-008 | Medium | `integration` | Limited SCM provider support |
| L-PRM-001 | **High** | `backend-plugin-api` | No fine-grained field-level permissions |
| L-PRM-002 | Medium | `backend-plugin-api` | Permission evaluation requires round-trip |
| L-PRM-003 | Medium | `backend-plugin-api` | `getResources` is optional — silently degrades enforcement |
| L-PRM-004 | Medium | `backend-plugin-api` | Access restrictions limited to permission names/actions |
| L-PRM-005 | Medium | `backend-plugin-api` | HttpAuthPolicy only supports two allow modes |
| L-PRM-006 | Low | `backend-plugin-api` | Service principal `subject` has no defined semantics |
| L-PRM-007 | **High** | `backend-plugin-api` | No permission inheritance or hierarchy |
| L-PRM-008 | Low | `backend-defaults` | Principal self-check is incomplete (TODO in code) |
| L-FE-001 | **High** | `core-*`, `frontend-*` | Two parallel frontend systems maintained simultaneously |
| L-FE-002 | Medium | `frontend-app-api` | Extension tree config merge incomplete |
| L-FE-003 | Low | `frontend-app-api` | Root node `attachTo` spec is ignored |
| L-FE-004 | Medium | `frontend-app-api` | Limited extension variant support |
| L-FE-005 | Medium | `core-app-api` | AppThemeSelector/AppLanguageSelector require manual cleanup |
| L-FE-006 | Low | `core-components` | Deprecated `GuestUserIdentity` still in core |
| L-FE-007 | Medium | `core-compat-api` | `convertLegacyApp` deprecated with no clear timeline |
| L-FE-008 | Medium | `backend-defaults` | CSP configuration requires `eval` for AJV frontend validation |
| L-FE-009 | Medium | `backend-defaults` | Helmet configuration not consumer-controlled |
| L-INF-001 | Medium | `cli-module-test-jest` | Jest worker memory leaks require workaround |
| L-INF-002 | Low | `backend-app-api`, `cli` | Default export transpilation workaround |
| L-INF-003 | Low | `backend-defaults` | SQLite driver warning suppression |
| L-INF-004 | Medium | `backend-app-api` | Process event listener cleanup required |
| L-INF-005 | Low | `cli-module-build` | Rspack compatibility issue (FIXME) |
| L-INF-006 | **High** | All backend packages | No native OpenTelemetry/tracing in service interfaces |
| L-INF-007 | **High** | `backend-plugin-api` | No rate limiting at service layer |
| L-INF-008 | **High** | `backend-plugin-api` | No built-in event/message bus |
| L-INF-009 | Medium | `backend-plugin-api` | Single-database backend assumption |
| L-INF-010 | Low | `backend-defaults` | Gerrit test flakiness acknowledged |
| L-INF-011 | **High** | All backend packages | No graceful degradation framework |
| L-INF-012 | Low | Multiple | `HumanDuration` type used inconsistently |
| **SCAFFOLDER** | | | |
| L-SCF-001 | **High** | `scaffolder-backend` | Task recovery is fully experimental |  
| L-SCF-002 | Medium | `scaffolder-backend` | Task events polled every second (N DB queries/sec) |
| L-SCF-003 | **High** | `scaffolder-backend` | Workspace stored as binary BLOB in database |
| L-SCF-004 | Low | `scaffolder-backend` | Heartbeat hardcoded to 1 second |
| L-SCF-005 | Medium | `scaffolder-backend` | No task queue priority |
| L-SCF-006 | Medium | `scaffolder-backend` | Nunjucks rendering in main Node.js thread |
| L-SCF-007 | **High** | `scaffolder-backend` | Task secrets stored as plain JSON in database |
| L-SCF-008 | Medium | `scaffolder-backend` | Task log events grow unboundedly — no TTL |
| L-SCF-009 | Low | `scaffolder-backend` | Cancel scans all events to find current step |
| **CATALOG BACKEND** | | | |
| L-CPE-001 | **High** | `catalog-backend` | Polling-based processing loop (1s interval) |
| L-CPE-002 | Medium | `catalog-backend` | Fixed batch size (max 10 concurrent entities) |
| L-CPE-003 | Low | `catalog-backend` | Deprecated Prometheus metrics alongside OTel |
| L-CPE-004 | Medium | `catalog-backend` | Full entity serialization for hash comparison |
| L-CPE-005 | Low | `catalog-backend` | Orphan cleanup race condition with processing |
| L-CPE-006 | Low | `catalog-backend` | Error events published without await |
| L-CPE-007 | Low | `catalog-backend` | Processing cache TTL hardcoded to magic constant |
| L-CPE-008 | Medium | `catalog-backend` | No back-pressure on processing queue |
| **SIGNALS** | | | |
| L-SIG-001 | **Critical** | `signals-backend` | All WebSocket connections stored in-memory |
| L-SIG-002 | Medium | `signals-backend` | Multi-replica fan-out requires external event broker |
| L-SIG-003 | Low | `signals-backend` | Ping interval never stops when no connections |
| L-SIG-004 | Medium | `signals-backend` | Event unsubscription not implemented on shutdown |
| L-SIG-005 | Low | `signals-backend` | Binary messages silently ignored |
| L-SIG-006 | **High** | `signals-backend` | No message delivery guarantee |
| L-SIG-007 | Medium | `signals-backend` | Recipient filtering limited to ownership entity refs |
| L-SIG-008 | Medium | `signals-backend` | No WebSocket payload size limit |
| **PROXY** | | | |
| L-PRX-001 | Medium | `proxy-backend` | Header allowlist only — no header value validation |
| L-PRX-002 | Low | `proxy-backend` | Config reload uses unstable JSON stringify comparison |
| L-PRX-003 | Medium | `proxy-backend` | No request body size limit |
| L-PRX-004 | Medium | `proxy-backend` | `dangerously-allow-unauthenticated` is a string policy |
| L-PRX-005 | Low | `proxy-backend` | Request and response headers share same allowlist |
| L-PRX-006 | Low | `proxy-backend` | `host` header security nuance with `changeOrigin: false` |
| L-PRX-007 | Low | `proxy-backend` | `reviveConsumedRequestBodies` non-obvious footgun |
| L-PRX-008 | Medium | `proxy-backend` | No timeout configuration per proxy route |

---

## Severity Summary

| Severity | Count |
|---|---|
| 🔴 Critical | 3 |
| 🟠 High | 17 |
| 🟡 Medium | 53 |
| 🟢 Low | 35 |

---

## Top Priorities for Golang Migration

If migrating to Golang, the following limitations are **most relevant** as architectural constraints:

### Critical / High Priority Blockers

1. **L-BPS-001** — Monolithic single-process Node.js architecture is the primary motivation for migration. Go enables true microservice isolation.

2. **L-BPS-003** — Raw Knex exposure prevents database abstraction. A Go migration can introduce proper repository patterns.

3. **L-BPS-008** — Express.js lock-in prevents using efficient Go HTTP servers (e.g., Chi, Gin, Echo, net/http).

4. **L-BPS-013** — Lack of service versioning is an opportunity to introduce proper API contract management in Go.

5. **L-INF-006** — Native OpenTelemetry integration can be first-class in Go services.

6. **L-INF-007** — Rate limiting middleware can be built-in to the Go gateway layer.

7. **L-INF-008** — A Go event bus (NATS, Kafka integration) can replace the current HTTP-only inter-plugin communication.

8. **L-INF-011** — Go's goroutine-based concurrency enables proper circuit breaker patterns.

9. **L-PRM-007** — Permission hierarchy/RBAC can be properly implemented in Go using Casbin or Open Policy Agent.

10. **L-URL-004** — Go's streaming capabilities can replace the memory-hungry full-repo-download pattern.

---

## File Map

| File | Content |
|---|---|
| [01-config-system.md](file:///Users/binhnt/Lab/dev/backstage/specs/bugs/limitations/01-config-system.md) | Config reader, merge, validation limitations |
| [02-error-handling.md](file:///Users/binhnt/Lab/dev/backstage/specs/bugs/limitations/02-error-handling.md) | Error types, serialization, response error handling |
| [03-backend-plugin-system.md](file:///Users/binhnt/Lab/dev/backstage/specs/bugs/limitations/03-backend-plugin-system.md) | Core backend services: DB, cache, auth, scheduler, HTTP, lifecycle |
| [04-catalog-model.md](file:///Users/binhnt/Lab/dev/backstage/specs/bugs/limitations/04-catalog-model.md) | Entity model, validation, catalog client |
| [05-url-reader-integration.md](file:///Users/binhnt/Lab/dev/backstage/specs/bugs/limitations/05-url-reader-integration.md) | SCM integrations, URL readers, ETag gaps |
| [06-permission-system.md](file:///Users/binhnt/Lab/dev/backstage/specs/bugs/limitations/06-permission-system.md) | Auth, permissions, access control |
| [07-frontend-system.md](file:///Users/binhnt/Lab/dev/backstage/specs/bugs/limitations/07-frontend-system.md) | Dual frontend systems, CSP, extension tree |
| [08-cross-cutting-infrastructure.md](file:///Users/binhnt/Lab/dev/backstage/specs/bugs/limitations/08-cross-cutting-infrastructure.md) | Observability, rate limiting, event bus, resilience |
| [09-scaffolder-backend.md](file:///Users/binhnt/Lab/dev/backstage/specs/bugs/limitations/09-scaffolder-backend.md) | Task broker, workflow runner, workspace BLOB storage, secrets |
| [10-catalog-backend.md](file:///Users/binhnt/Lab/dev/backstage/specs/bugs/limitations/10-catalog-backend.md) | Catalog processing engine: polling, batching, hashing |
| [11-signals-realtime.md](file:///Users/binhnt/Lab/dev/backstage/specs/bugs/limitations/11-signals-realtime.md) | WebSocket signals: in-memory state, no delivery guarantee |
| [12-proxy-backend.md](file:///Users/binhnt/Lab/dev/backstage/specs/bugs/limitations/12-proxy-backend.md) | Proxy: header allowlist, timeouts, body size, credential policy |
