# AI Issue #008: Naming Collision Between Backend and Frontend Concepts

## Severity: Medium
## Category: Naming Ambiguity

## Problem

Backstage sử dụng **cùng tên cho các concepts khác nhau** giữa backend và frontend systems, khiến AI không biết đang nói về concept nào khi thiếu context.

### Evidence

1. **"Extension Point"** — 2 hệ thống hoàn toàn khác:
   - **Backend**: `ExtensionPoint<T>` — DI pattern, modules register implementations
     ```typescript
     // packages/backend-plugin-api/src/wiring/types.ts
     export type ExtensionPoint<T> = {
       id: string; T: T;
       $$type: '@backstage/ExtensionPoint';
     };
     ```
   - **Frontend**: `ExtensionInput` — Tree-based attachment system
     ```typescript  
     // packages/frontend-plugin-api/src/wiring/createExtensionInput.ts
     export type ExtensionInput<...> = {
       $$type: '@backstage/ExtensionInput';
     };
     ```

2. **"Extension"** — overloaded term:
   - Backend: Module registrations via `registerExtensionPoint()`
   - Frontend: `ExtensionDefinition`, `createExtension()` — UI components in extension tree

3. **"Plugin"** — different APIs:
   - Backend: `createBackendPlugin()` → `BackendFeature`
   - Frontend (new): `createFrontendPlugin()` → `FrontendPlugin`
   - Frontend (old): `createPlugin()` → `BackstagePlugin`

4. **"Module"**:
   - Backend: `createBackendModule()` — extends a backend plugin
   - Frontend: `createFrontendModule()` — modifies/extends frontend plugins

5. **"Feature"**:
   - Backend: `BackendFeature` — union of plugin/module/service factory/loader
   - Frontend: `FrontendFeature` — union of plugin/module/loader

6. **"Factory"**:
   - `ServiceFactory` — backend service DI
   - `BackendFeatureFactory` — creates BackendFeatures with options
   - Extension `factory()` — frontend extension factory function

7. **"Blueprint"**: Only exists in frontend (`ExtensionBlueprint`), no backend equivalent — but backend has similar concept via `register()` callback pattern

### Naming Collision Matrix

| Term | Backend | Frontend (New) | Frontend (Old) |
|------|---------|----------------|----------------|
| Plugin | `createBackendPlugin()` | `createFrontendPlugin()` | `createPlugin()` |
| Module | `createBackendModule()` | `createFrontendModule()` | N/A |
| Extension | `ExtensionPoint` | `ExtensionDefinition` | `Extension` (deprecated) |
| Feature | `BackendFeature` | `FrontendFeature` | N/A |
| Route | N/A | `RouteRef` (new) | `createRouteRef()` (old) |

## Impact on AI

- **Ambiguous search results**: Searching for "ExtensionPoint" returns results from both backend and frontend — AI may confuse them
- **Wrong API suggestions**: AI asked "how to create an extension" may suggest backend's `registerExtensionPoint` for a frontend context
- **Cross-system confusion**: AI may suggest `BackendFeature` patterns in frontend code or vice versa
- **Training data pollution**: Documentation and Stack Overflow answers use terms interchangeably
- **Cannot infer context**: Without knowing the file path or package name, AI cannot determine which "Plugin" or "Extension" is relevant
