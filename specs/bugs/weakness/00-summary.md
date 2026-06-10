# Weakness Summary — Backstage Backend

## Overview

This document provides a consolidated summary of all weaknesses identified in the Backstage backend codebase, organized by category and severity. The analysis covers **core packages** and **critical plugins** (proxy, scaffolder, catalog, permission).

---

## Statistics

| Category | HIGH | MEDIUM | Total |
|----------|------|--------|-------|
| [01 — Security](file:///Users/binhnt/Lab/dev/backstage/specs/bugs/weakness/01-security-weaknesses.md) | 10 | 0 | 10 |
| [02 — Architecture & Design](file:///Users/binhnt/Lab/dev/backstage/specs/bugs/weakness/02-architecture-weaknesses.md) | 10 | 0 | 10 |
| [03 — Performance & Reliability](file:///Users/binhnt/Lab/dev/backstage/specs/bugs/weakness/03-performance-reliability-weaknesses.md) | 4 | 6 | 10 |
| [04 — Code Quality & Maintainability](file:///Users/binhnt/Lab/dev/backstage/specs/bugs/weakness/04-code-quality-weaknesses.md) | 0 | 10 | 10 |
| [05 — Plugin-Level](file:///Users/binhnt/Lab/dev/backstage/specs/bugs/weakness/05-plugin-weaknesses.md) | 7 | 5 | 12 |
| **TOTAL** | **31** | **21** | **52** |

---

## Critical Findings

### Top 10 Most Impactful Weaknesses

| # | Weakness | Category | Severity |
|---|----------|----------|----------|
| 1 | `unsafe-eval` in CSP | Security | HIGH |
| 2 | Monolithic single-process architecture | Architecture | HIGH |
| 3 | Proxy backend SSRF via configurable target URL | Plugin | HIGH |
| 4 | `disableDefaultAuthPolicy` produces empty token | Security | HIGH |
| 5 | Scaffolder credentials serialized as JSON in database | Plugin | HIGH |
| 6 | No token revocation mechanism | Security | HIGH |
| 7 | Rate limiting disabled by default | Security | HIGH |
| 8 | No circuit breaker for service-to-service calls | Architecture | HIGH |
| 9 | Proxy auth policy leak on config hot-reload | Plugin | HIGH |
| 10 | Default allow-all permission policy | Plugin | HIGH |

---

## Weakness Map by Package

| Package | Weaknesses | Files |
|---------|------------|-------|
| `backend-defaults/auth` | Empty token bypass, token revocation, JWKS cache leak, credential caching, `uip` re-signature | 4 |
| `backend-defaults/rootHttpRouter` | `unsafe-eval`, CSP gaps, disabled security headers, no body size limits, rate limiting | 5 |
| `backend-defaults/httpAuth` | Cookie security flags, credential memoization, `as any` type assertions | 1 |
| `backend-defaults/database` | Connection cache race condition, keepalive issues, SQLite shutdown, config confusion | 1 |
| `backend-defaults/cache` | No eviction policy, no size limits, no cross-instance invalidation | 1 |
| `backend-defaults/discovery` | Static URL patterns, no circuit breaker, no health-based routing | 1 |
| `backend-plugin-api` | Express coupling, single-threaded scheduler, no observability | 6 |
| `errors` | Silent error swallowing, string-based error matching | 2 |
| `config-loader` | `console.error` usage, no config validation pipeline | 1 |
| `proxy-backend` | SSRF, no response size limit, auth policy leak, config race condition | 1 |
| `scaffolder-backend` | Credential serialization, workspace path traversal, secret redaction bypass, polling loops | 4 |
| `catalog-backend` | No adaptive backoff, fire-and-forget error callbacks | 1 |
| `permission-backend` | Default allow-all policy | 1 |

---

## Files Analyzed

### Core Packages

| File | Lines | Weaknesses |
|------|-------|------------|
| [DefaultAuthService.ts](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/auth/DefaultAuthService.ts) | 227 | 3 |
| [httpAuthServiceFactory.ts](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/httpAuth/httpAuthServiceFactory.ts) | 328 | 3 |
| [PluginTokenHandler.ts](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/auth/plugin/PluginTokenHandler.ts) | 254 | 3 |
| [UserTokenHandler.ts](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/auth/user/UserTokenHandler.ts) | 169 | 2 |
| [MiddlewareFactory.ts](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/rootHttpRouter/http/MiddlewareFactory.ts) | 372 | 4 |
| [readHelmetOptions.ts](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/rootHttpRouter/http/readHelmetOptions.ts) | 144 | 3 |
| [DatabaseManager.ts](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/database/DatabaseManager.ts) | 296 | 4 |
| [HostDiscovery.ts](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/discovery/HostDiscovery.ts) | 331 | 2 |
| [CacheClient.ts](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/cache/CacheClient.ts) | 97 | 1 |
| [helpers.ts (auth)](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/auth/helpers.ts) | 198 | 2 |
| [response.ts](file:///Users/binhnt/Lab/dev/backstage/packages/errors/src/serialization/response.ts) | 99 | 1 |
| [applyInternalErrorFilter.ts](file:///Users/binhnt/Lab/dev/backstage/packages/backend-defaults/src/entrypoints/rootHttpRouter/http/applyInternalErrorFilter.ts) | 53 | 1 |
| [loader.ts](file:///Users/binhnt/Lab/dev/backstage/packages/config-loader/src/loader.ts) | 153 | 1 |

### Critical Plugins

| File | Lines | Weaknesses |
|------|-------|------------|
| [router.ts (proxy)](file:///Users/binhnt/Lab/dev/backstage/plugins/proxy-backend/src/service/router.ts) | 369 | 4 |
| [NunjucksWorkflowRunner.ts](file:///Users/binhnt/Lab/dev/backstage/plugins/scaffolder-backend/src/scaffolder/tasks/NunjucksWorkflowRunner.ts) | 1026 | 4 |
| [StorageTaskBroker.ts](file:///Users/binhnt/Lab/dev/backstage/plugins/scaffolder-backend/src/scaffolder/tasks/StorageTaskBroker.ts) | 525 | 3 |
| [DefaultCatalogProcessingEngine.ts](file:///Users/binhnt/Lab/dev/backstage/plugins/catalog-backend/src/processing/DefaultCatalogProcessingEngine.ts) | 513 | 2 |

---

## Migration Implications (Node.js → Golang)

These weaknesses provide strong evidence for migration to a Golang microservices architecture:

| Weakness Category | Go Solution |
|-------------------|-------------|
| **Monolithic process** | Separate binaries per service with independent deployment |
| **Express lock-in** | Go `net/http` is framework-agnostic and high-performance |
| **No circuit breaker** | `gobreaker`, `resilience4g-go` provide production-grade patterns |
| **Polling loops** | Go channels + goroutines enable true event-driven architecture |
| **`as any` type abuse** | Go's strong static typing prevents type safety holes |
| **Single-threaded scheduler** | Go's goroutine scheduler handles millions of concurrent tasks |
| **No SSRF protection** | Go `net/http` transport with custom dialers enables IP blocklists |
| **Database connection leaks** | Go's `database/sql` pool with context cancellation is more robust |
| **No body size limits** | `http.MaxBytesReader` built into standard library |
| **Credential serialization** | Go's interface types prevent accidental serialization of sensitive data |
