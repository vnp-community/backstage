# AI Issue #001: Opaque Type System Obfuscates Actual Data Structures

## Severity: Critical
## Category: Type Comprehension

## Problem

Backstage sử dụng hệ thống **Opaque Types** tự phát triển (`@internal/opaque` → `OpaqueType` class) để che giấu cấu trúc thực của objects khỏi public API. Điều này tạo ra barrier lớn cho AI khi phân tích code.

### Evidence

1. **`OpaqueType` class** tại `packages/opaque-internal/src/OpaqueType.ts`:
   - Sử dụng `$$type` string markers để identify types tại runtime
   - `T: null as TService` — phantom type parameters không có runtime value
   - Private fields (`#type`, `#versions`) khiến AI không thể inspect actual state

2. **`$$type` markers** xuất hiện trong ~50+ files trên toàn frontend/backend API:
   - `@backstage/BackendFeature`, `@backstage/ServiceRef`, `@backstage/ExtensionPoint`
   - `@backstage/ExtensionDefinition`, `@backstage/FrontendPlugin`, `@backstage/FrontendModule`
   - `@backstage/RouteRef`, `@backstage/SubRouteRef`, `@backstage/ExternalRouteRef`
   - `@backstage/BlueprintParams`, `@backstage/ExtensionDataRef`, etc.

3. **Type mismatch giữa public và internal**:
   ```typescript
   // Public type - AI thấy cái này
   export interface BackendFeature {
     $$type: '@backstage/BackendFeature';
   }
   
   // Internal type - AI phải tìm ra cái này mới hiểu được
   export interface InternalBackendRegistrations extends BackendFeature {
     version: 'v1';
     featureType: 'registrations';
     getRegistrations(): Array<...>;
   }
   ```

## Impact on AI

- **Không thể resolve type thực**: AI đọc `BackendFeature` chỉ thấy `{ $$type: string }`, không biết bên trong có `getRegistrations()`, `version`, `featureType`
- **Phải trace qua `toInternal()` calls**: Mỗi lần cần biết actual properties phải tìm `OpaqueType.toInternal()` call tương ứng
- **Type assertions che giấu thông tin**: `as InternalBackendRegistrations` trong runtime code khiến static analysis fail
- **Phantom types**: `T: null as TService` — thuộc tính chỉ tồn tại ở type-level, runtime trả về `null`

## Affected Packages

- `packages/opaque-internal/` — Core OpaqueType implementation
- `packages/backend-plugin-api/` — BackendFeature, ServiceRef, ExtensionPoint
- `packages/frontend-plugin-api/` — ExtensionDefinition, FrontendPlugin, RouteRef, etc.
- `packages/frontend-internal/` — InternalExtensionDefinition, InternalExtensionInput
- `packages/backend-internal/` — OpaqueExtensionPointFactoryMiddleware
