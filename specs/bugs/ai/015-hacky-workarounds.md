# AI Issue #015: Hacky Workarounds with Explicit "Hacky" Comments

## Severity: Low-Medium
## Category: Code Quality / Stability

## Problem

Backstage core code chứa **explicit "hacky" comments và workarounds** mà developers tự acknowledge là không clean. Điều này tạo ra patterns không ổn định cho AI to learn from.

### Evidence

1. **`BackendInitializer.ts` line 602** — lifecycle service retrieval:
   ```typescript
   // Bit of a hacky way to grab the lifecycle services, potentially find a nicer way to do this
   async #getRootLifecycleImpl(): Promise<
     RootLifecycleService & {
       startup(): Promise<void>;
       beforeShutdown(): Promise<void>;
       shutdown(): Promise<void>;
     }
   > {
     const lifecycleService = await this.#serviceRegistry.get(...);
     const service = lifecycleService as any;  // cast to any!
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
   
   Pattern: Get service → cast to `any` → runtime duck-type check → hope it works.

2. **`ServiceRegistry.ts` line 29-36** — manual type sync requirement:
   ```typescript
   /**
    * Keep in sync with @backstage/backend-plugin-api/src/services/system/types.ts
    * @internal
    */
   export type InternalServiceRef = ServiceRef<unknown> & {
     __defaultFactory?: (...) => Promise<ServiceFactory | (() => ServiceFactory)>;
   };
   ```
   
   This type must MANUALLY be kept in sync with another file. No compile-time guarantee.

3. **`BackendInitializer.ts`** — backwards compatibility via duck typing:
   ```typescript
   function isServiceFactory(feature: BackendFeature): feature is InternalServiceFactory {
     const internal = toInternalBackendFeature(feature);
     if (internal.featureType === 'service') {
       return true;
     }
     // Backwards compatibility for v1 registrations that use duck typing
     return 'service' in internal;
   }
   ```

4. **`resolveAppTree.ts` line 164** — TODO acknowledging non-ideal code:
   ```typescript
   // TODO: For now we simply ignore the attachTo spec of the root node,
   // but it'd be cleaner if we could avoid defining it
   ```

5. **`createExtension.ts`** — TODO comments about desired type checks:
   ```typescript
   // TODO(Rugvip): Making this a type check would be optimal, but it seems
   //               like it's tricky to add that and still have the type
   //               inference work correctly for the factory output.
   if (overrideOptions.output && !overrideOptions.factory) {
     throw new Error('Refused to override output without also overriding factory');
   }
   ```

6. **Singleton IIFE pattern** for instance registry:
   ```typescript
   const instanceRegistry = new (class InstanceRegistry {
     #registered = false;
     #instances = new Set<BackendInitializer>();
     // ...
   })();
   ```
   Anonymous class instantiated immediately — non-standard pattern.

7. **`OpaqueType.ts` line 17-23** — author acknowledges temporal placement:
   ```typescript
   // TODO(Rugvip): This lives here temporarily, but should be moved to a more
   // central location. It's useful for backend packages too so we'll need to have
   // it in a common package, but it might also be that we want to make it
   // available publicly too...
   ```

## Impact on AI

- **AI learns unstable patterns**: If AI uses these files as reference for code generation, it will reproduce hacky patterns (e.g., `as any` + duck typing instead of proper interfaces)
- **"Keep in sync" = no compiler safety**: AI may modify one type definition without updating the other, creating subtle runtime bugs
- **Backwards compat branches**: AI may not know which code path is "current" vs "legacy compat" — both paths are valid code
- **TODO = uncommitted design**: AI may build upon designs that the authors explicitly plan to change
- **`as any` undermines type safety**: 20+ `as any` casts in core wiring files mean TypeScript compiler provides no safety — errors are only caught at runtime

## Affected Files

| File | Hack Type | Lines |
|------|----------|-------|
| `backend-app-api/src/wiring/BackendInitializer.ts` | `as any` duck typing, IIFE class | 784 |
| `backend-app-api/src/wiring/ServiceRegistry.ts` | Manual type sync, `__defaultFactory` | 359 |
| `frontend-app-api/src/tree/resolveAppTree.ts` | TODO workarounds | 233 |
| `frontend-plugin-api/src/wiring/createExtension.ts` | TODO type checks, `as any` | 812 |
| `opaque-internal/src/OpaqueType.ts` | Temporary placement TODO | 168 |
