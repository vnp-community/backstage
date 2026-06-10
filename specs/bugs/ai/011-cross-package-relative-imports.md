# AI Issue #011: Cross-Package Relative Imports Breaking Module Boundaries

## Severity: High
## Category: Code Navigation / Module Boundaries

## Problem

Backstage core packages sử dụng **relative imports xuyên packages** (với eslint-disable) thay vì qua published API. Điều này phá vỡ module boundaries và khiến AI không thể xác định actual dependency graph.

### Evidence

1. **31 files trong `packages/` sử dụng `no-relative-monorepo-imports` disable**

2. **`BackendInitializer.ts`** — file quan trọng nhất của backend system — import trực tiếp internal types từ package khác:
   ```typescript
   // eslint-disable-next-line @backstage/no-relative-monorepo-imports
   import type {
     InternalBackendFeature,
     InternalBackendFeatureLoader,
     InternalBackendRegistrations,
   } from '../../../backend-plugin-api/src/wiring/types';
   
   // eslint-disable-next-line @backstage/no-relative-monorepo-imports
   import type { InternalServiceFactory } from '../../../backend-plugin-api/src/services/system/types';
   ```

3. **`ServiceRegistry.ts`** — DI container cũng import trực tiếp:
   ```typescript
   // eslint-disable-next-line @backstage/no-relative-monorepo-imports
   import { InternalServiceFactory } from '../../../backend-plugin-api/src/services/system/types';
   ```

4. **Frontend app API** — tương tự:
   ```typescript
   // frontend-app-api/src/tree/resolveAppTree.ts
   import { toInternalExtension } from '../../../frontend-plugin-api/src/wiring/resolveExtensionDefinition';
   
   // frontend-app-api/src/tree/instantiateAppNodeTree.ts
   import { ResolvedExtensionInputs } from '../../../frontend-plugin-api/src/wiring/createExtension';
   
   // frontend-app-api/src/wiring/InternalAppContext.ts
   import { AppIdentityProxy } from '../../../core-app-api/src/apis/implementations/IdentityApi/AppIdentityProxy';
   ```

5. **Cross-domain imports**:
   ```typescript
   // frontend-app-api/src/wiring/createPluginInfoAttacher.ts
   import { ... } from '../../../catalog-model/src/entity/ref';
   ```

### Why These Imports Exist

Comment in code: `"Direct internal import to avoid duplication"` — These are `@internal` marked types that are NOT part of the public API but ARE needed by implementation packages.

### Import Path Patterns

```
packages/backend-app-api/src/wiring/BackendInitializer.ts
  → ../../../backend-plugin-api/src/wiring/types    (3 levels up, into sibling package)
  → ../../../backend-plugin-api/src/services/system/types

packages/frontend-app-api/src/tree/resolveAppTree.ts  
  → ../../../frontend-plugin-api/src/wiring/resolveExtensionDefinition

packages/frontend-app-api/src/wiring/InternalAppContext.ts
  → ../../../core-app-api/src/apis/implementations/IdentityApi/AppIdentityProxy
```

## Impact on AI

- **False dependency graph**: `package.json` says `backend-app-api` depends on `backend-plugin-api`, but the actual import goes to an INTERNAL type not in the public API
- **Cannot resolve via package exports**: AI tools using standard module resolution will follow `@backstage/backend-plugin-api` → `src/index.ts` → public exports. These internal types are NOT exported there
- **Path-based coupling**: `../../../` relative paths are fragile and depend on exact directory structure — AI auto-complete and rename tools will break them
- **Circular type dependency risk**: `backend-app-api` imports internal types from `backend-plugin-api` while `backend-plugin-api` is the public API package — this creates an inversion that confuses dependency analysis
- **`ServiceRegistry` comment reveals fragility**: `"Keep in sync with @backstage/backend-plugin-api/src/services/system/types.ts"` — manual synchronization requirement

## File Impact Map

| Consumer Package | Imports From | Internal Types Used |
|-----------------|-------------|-------------------|
| `backend-app-api` | `backend-plugin-api/src/wiring/types` | `InternalBackendFeature`, `InternalBackendRegistrations`, `InternalBackendFeatureLoader` |
| `backend-app-api` | `backend-plugin-api/src/services/system/types` | `InternalServiceFactory` |
| `frontend-app-api` | `frontend-plugin-api/src/wiring/resolveExtensionDefinition` | `toInternalExtension` |
| `frontend-app-api` | `frontend-plugin-api/src/wiring/createExtension` | `ResolvedExtensionInputs` |
| `frontend-app-api` | `frontend-plugin-api/src/wiring/createFrontendModule` | `isFrontendModule`, etc. |
| `frontend-app-api` | `core-app-api/src/apis/.../AppIdentityProxy` | `AppIdentityProxy` |
| `frontend-app-api` | `catalog-model/src/entity/ref` | Entity ref utilities |
| `frontend-defaults` | `frontend-plugin-api/src/wiring/...` | Internal resolution |
