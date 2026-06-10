# AI Issue #006: Dynamic Dependency Injection via ServiceRef Pattern

## Severity: High
## Category: Runtime vs Static Analysis Gap

## Problem

Backend system sử dụng **ServiceRef-based dependency injection** hoàn toàn dynamic. Các service dependencies được khai báo qua runtime objects, không phải qua constructor parameters hay module imports — khiến AI không thể trace dependency graph bằng static analysis.

### Evidence

1. **ServiceRef pattern** — dependencies là objects, không phải types:
   ```typescript
   // Service reference = runtime object, type info is in generic parameter
   export const auth = createServiceRef<import('./AuthService').AuthService>({
     id: 'core.auth',
   });
   ```

2. **Plugin registration — deps là Record<string, ServiceRef>**:
   ```typescript
   createBackendPlugin({
     pluginId: 'catalog',
     register(reg) {
       reg.registerInit({
         deps: {
           httpRouter: coreServices.httpRouter,
           database: coreServices.database,
           logger: coreServices.logger,
           // ... what services are used? must read this object
         },
         init(deps) {
           // deps.httpRouter — type is inferred from ServiceRef.T
           // but AI sees Record<string, unknown> in internal types
         },
       });
     },
   });
   ```

3. **`DepsToInstances` type mapping** — complex conditional:
   ```typescript
   type DepsToInstances<TDeps extends {
     [key in string]: ServiceRef<unknown> | ExtensionPoint<unknown>;
   }> = {
     [key in keyof TDeps]: TDeps[key] extends ServiceRef<unknown, 'root'|'plugin', 'multiton'>
       ? Array<TDeps[key]['T']>
       : TDeps[key]['T'];
   };
   ```

4. **Service factory — another layer of indirection**:
   ```typescript
   createServiceFactory({
     service: coreServices.database,
     deps: { rootConfig: coreServices.rootConfig },
     factory: async (deps) => {
       // deps.rootConfig — inferred type, not explicit
       return new DatabaseServiceImpl(deps.rootConfig);
     },
   });
   ```

5. **`InternalServiceFactory` hides actual factory signature**:
   ```typescript
   export interface InternalServiceFactory {
     deps: { [key in string]: ServiceRef<unknown> };
     factory(deps: { [key in string]: unknown }, context: unknown): Promise<TService>;
   }
   // All type info is erased to `unknown` in internal representation
   ```

### Dependency Resolution Challenge

```
Q: "What dependencies does the catalog plugin use?"
→ Must find the createBackendPlugin() call for 'catalog'
→ Must read the `deps` object literal
→ Must resolve each ServiceRef to its actual interface
→ Must check if there's a custom ServiceFactory overriding the default
→ Must check if any BackendModule adds more deps via extension points
```

## Impact on AI

- **No static import graph**: Dependencies are runtime ServiceRef objects, not `import` statements. AI grep for `import` finds nothing useful
- **`unknown` erasure**: Internal types erase all service types to `unknown`, requiring AI to re-infer from ServiceRef generics
- **Service factory chain**: Finding the actual implementation of a service requires tracing: ServiceRef → ServiceFactory → factory function → actual class
- **Extension point injection**: Modules can inject into plugins via ExtensionPoints, adding dependencies that don't appear in the plugin's own code
- **Multiton pattern**: Some services can have multiple implementations (multiton). AI must check `multiton?: true` flag to know if result is `T` or `Array<T>`

## Affected Packages

- `packages/backend-plugin-api/src/services/` — Service definitions
- `packages/backend-defaults/src/` — Default service implementations
- `packages/backend-app-api/src/wiring/` — DI container/initializer
- All `plugins/*-backend/` packages — Plugin registrations
