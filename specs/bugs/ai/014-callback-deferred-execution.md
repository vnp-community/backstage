# AI Issue #014: Callback-Heavy Registration Pattern with Deferred Execution

## Severity: Medium
## Category: Control Flow Comprehension

## Problem

Backstage plugin/module/extension registration dựa trên **callback pattern** — code không chạy khi khai báo mà được deferred execution. AI đọc code top-to-bottom sẽ hiểu sai thứ tự và context thực thi.

### Evidence

1. **Backend plugin registration — 3-level callback nesting**:
   ```typescript
   const plugin = createBackendPlugin({
     pluginId: 'catalog',
     register(reg) {                           // callback 1: registration phase
       reg.registerExtensionPoint(catalogExtPoint, impl);
       reg.registerInit({
         deps: { httpRouter, database, logger },
         init(deps) {                           // callback 2: init phase (runs MUCH later)
           deps.httpRouter.use(createRouter());
         },
       });
     },
   });
   ```

   The `register()` callback runs immediately during `createBackendPlugin()`, but `init()` is stored and executed later during `BackendInitializer.start()`.

2. **Frontend extension — factory pattern**:
   ```typescript
   const extension = createExtension({
     kind: 'page',
     name: 'catalog',
     attachTo: { id: 'app/routes', input: 'routes' },
     output: [coreExtensionData.reactElement],
     factory({ config, inputs, apis }) {        // callback: runs during tree instantiation
       return [coreExtensionData.reactElement(<CatalogPage />)];
     },
   });
   ```

3. **Blueprint make → factory → originalFactory chain**:
   ```typescript
   const ext = PageBlueprint.make({
     params: { ... },
   });
   
   // override with nested callbacks
   ext.override({
     factory(originalFactory, context) {           // callback 1: override factory
       const result = originalFactory({            // callback 2: calls original
         params: { ... },                          // params for original
         config: context.config,
       });
       return [...result, extraData(...)];
     },
   });
   ```

4. **ServiceFactory — createRootContext + factory chain**:
   ```typescript
   createServiceFactory({
     service: coreServices.database,
     deps: { config: coreServices.rootConfig },
     createRootContext(deps) {                     // callback 1: runs ONCE for all plugins
       return new DatabaseManager(deps.config);
     },
     factory(deps, context) {                      // callback 2: runs PER PLUGIN
       return context.forPlugin(deps.pluginMetadata.getId());
     },
   });
   ```

5. **Feature loader — async callback returning features**:
   ```typescript
   createBackendFeatureLoader({
     deps: { config: coreServices.rootConfig },
     async loader({ config }) {                    // callback: runs during bootstrap
       const service = new PackageDiscoveryService(config);
       const { features } = await service.getBackendFeatures();
       return features;                            // returns more features to register
     },
   });
   ```

### Execution Timeline

```
Declaration Phase (top of file):
  createBackendPlugin()
    └─ register() runs immediately
       └─ registerExtensionPoint() → stores extension point
       └─ registerInit() → stores {deps, init} for later

Startup Phase (BackendInitializer.start()):
  1. Feature loaders execute → discover more features
  2. Service factories → createRootContext() runs
  3. Module init() callbacks → run in topological order
  4. Plugin init() callbacks → run after modules
  5. Service factories → factory() runs per plugin (on demand)
```

## Impact on AI

- **Declaration ≠ Execution**: AI reading `createBackendPlugin()` sees `register()` and `init()` in sequence, but they run at completely different times
- **Scope confusion**: `register()` runs in the `createBackendPlugin` scope, `init()` runs in `BackendInitializer` scope — different `this`, different available services
- **`deps` mapping is runtime**: AI cannot statically verify that `deps.httpRouter` will be available — it depends on ServiceRegistry resolution
- **Override chains**: `originalFactory` callback within `factory` creates closure chains that are 3+ levels deep
- **`createRootContext` vs `factory`**: Two-phase factory is non-obvious — `createRootContext` runs once, `factory` runs per-plugin with shared context
- **AI code generation risk**: AI may generate code that accesses services in `register()` instead of `init()`, which would fail at runtime

## Callback Depth Matrix

| Pattern | Callbacks | Deferred? | Per-Plugin? |
|---------|-----------|-----------|-------------|
| `createBackendPlugin.register()` | 1 | No (immediate) | No |
| `registerInit.init()` | 2 | Yes (startup) | Yes |
| `createServiceFactory.createRootContext()` | 1 | Yes (first use) | No |
| `createServiceFactory.factory()` | 2 | Yes (per plugin) | Yes |
| `createExtension.factory()` | 1 | Yes (tree build) | N/A |
| `blueprint.override.factory()` | 2 | Yes (tree build) | N/A |
| `createBackendFeatureLoader.loader()` | 1 | Yes (bootstrap) | No |
