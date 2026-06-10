# AI Issue #004: Massive Monorepo Scale with Deep Re-export Chains

## Severity: High
## Category: Scale / Context Window

## Problem

Backstage monorepo có quy mô cực lớn với **chuỗi re-export nhiều tầng**, khiến AI phải traverse nhiều files chỉ để tìm một definition thực.

### Evidence — Scale

| Metric | Value |
|--------|-------|
| Total packages | 69 |
| Total plugins | 156 (+ 1 README) |
| Total TS/TSX source files (non-test) | 4,847 |
| Total lines of code (non-test) | ~451,264 |
| Barrel index files with `export *` | 27+ |
| yarn.lock size | 1.83 MB |

### Evidence — Re-export Chains

1. **Backend Plugin API re-export chain** (4 levels):
   ```
   @backstage/backend-plugin-api                      ← consumer imports from here
     └─ src/index.ts: export * from './services'
         └─ src/services/index.ts: export * from './definitions'
             └─ src/services/definitions/index.ts: export * from './AuthService'
                 └─ src/services/definitions/AuthService.ts  ← actual definition
   ```

2. **`coreServices` namespace** — Dynamic `import()` types:
   ```typescript
   export namespace coreServices {
     export const auth = createServiceRef<import('./AuthService').AuthService>({
       id: 'core.auth',
     });
   }
   ```
   AI phải: (1) resolve namespace, (2) resolve inline `import()`, (3) resolve `createServiceRef` return type

3. **Frontend Plugin API re-export chain** (3+ levels):
   ```
   @backstage/frontend-plugin-api
     └─ src/index.ts: export * from './wiring'
         └─ src/wiring/index.ts: export * from './createExtension'
             └─ src/wiring/createExtension.ts (812 lines)
   ```

4. **Cross-package re-exports**:
   - `@backstage/core-compat-api` re-exports and wraps types from both `core-plugin-api` and `frontend-plugin-api`
   - `@backstage/backend-defaults` re-exports from `backend-plugin-api`
   - `@backstage/frontend-defaults` re-exports from `frontend-plugin-api`

### Evidence — Barrel File Pattern

```
packages/backend-plugin-api/src/index.ts
  → export * from './services'     ← barrel
  → export * from './wiring'       ← barrel
  
packages/backend-plugin-api/src/services/index.ts
  → export * from './definitions'  ← barrel
  → export * from './system'       ← barrel
  → export * from './utilities'    ← barrel
```

## Impact on AI

- **Context window overflow**: Resolving a single type requires loading 4-5 files, each 100-300 lines. AI context fills up quickly
- **Barrel file explosion**: `export * from` means AI must load ALL exports from a directory just to find one symbol
- **224 packages total**: AI cannot hold the entire project in context — must constantly page in/out
- **Ambiguous re-exports**: Same symbol name can appear at multiple import paths (`createExtension` from `frontend-plugin-api` vs from `frontend-plugin-api/alpha`)
- **`alpha` sub-paths**: Some packages have `/alpha` exports with experimental APIs, adding another dimension of confusion

## Specific AI Failure Scenarios

1. **"Where is ServiceRef defined?"** → AI will find the re-export chain and may stop at the barrel file, not the actual implementation in `system/types.ts`
2. **"What methods does AuthService have?"** → AI must resolve `import('./AuthService').AuthService` inline type import inside `coreServices` namespace
3. **"What does createBackendPlugin return?"** → Returns `BackendFeature` (opaque), actual type is `InternalBackendRegistrations` (internal) — 2-hop resolution
