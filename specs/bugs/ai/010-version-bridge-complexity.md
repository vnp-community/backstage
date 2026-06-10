# AI Issue #010: Version Bridge and Concurrent Version Support

## Severity: Medium
## Category: Runtime Complexity

## Problem

Backstage có package `@backstage/version-bridge` cho phép **nhiều versions của cùng một package** chạy đồng thời trong runtime. Pattern này tạo ra complexity mà AI không thể model bằng static analysis.

### Evidence

1. **`packages/version-bridge/`** — dedicated package for cross-version communication:
   - Provides utilities for packages to work across multiple concurrent versions
   - Uses global symbols/registry to share state between versions

2. **`OpaqueType` versioning** — built-in version support:
   ```typescript
   class OpaqueType<T extends {
     public: { $$type: string };
     versions: { version: string | undefined };
   }> {
     static create(options: {
       type: T['public']['$$type'];
       versions: Array<T['versions']['version']>;  // multiple versions supported
     })
   }
   ```

3. **Version checks in opaque types**:
   ```typescript
   toInternal = (value: unknown) => {
     if (!this.#versions.has(value.version)) {
       // Throws error about unsupported version
       throw new TypeError(`Invalid opaque type instance, got version ...`);
     }
     return value;
   };
   ```

4. **`InternalBackendRegistrations`** has both old and new registration types:
   ```typescript
   getRegistrations(): Array<
     | InternalBackendPluginRegistration    // old format
     | InternalBackendModuleRegistration    // old format
     | InternalBackendPluginRegistrationV1_1  // new format
     | InternalBackendModuleRegistrationV1_1  // new format
   >;
   ```

5. **Version-specific behavior branches**:
   ```typescript
   // Runtime check: type === 'plugin' || type === 'plugin-v1.1'
   ```

## Impact on AI

- **Multiple valid implementations**: Same opaque type can have different internal structures depending on version
- **Runtime type branching**: AI static analysis assumes one code path; runtime may take different paths based on version
- **Global state**: Version bridge uses global state that isn't visible in import graph
- **Cannot determine active version**: AI reading source code can't know which version is active at runtime
- **V1/V1.1 parallel types**: Duplicate type definitions (e.g., `InternalBackendPluginRegistration` vs `InternalBackendPluginRegistrationV1_1`) with subtle differences

## Affected Packages

- `packages/version-bridge/` — Core version bridge utilities
- `packages/opaque-internal/` — OpaqueType with version support
- `packages/backend-plugin-api/src/wiring/types.ts` — V1/V1.1 registration types
- `packages/frontend-internal/` — Versioned extension definitions
