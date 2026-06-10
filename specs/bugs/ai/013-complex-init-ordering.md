# AI Issue #013: Complex Initialization Ordering with Topological Sort

## Severity: Medium
## Category: Control Flow Comprehension

## Problem

Backend initialization sử dụng **topological sort trên dependency graph** để quyết định thứ tự init. Modules init TRƯỚC plugins, nhưng thứ tự giữa modules phụ thuộc vào extension point dependencies. AI không thể determine execution order bằng code reading.

### Evidence

1. **`BackendInitializer` (784 lines)** — Initialization orchestrator:
   ```typescript
   // All plugins are initialized in parallel
   await Promise.all(
     [...pluginInits.keys()].map(async pluginId => {
       // Initialize all eager services FIRST
       await this.#serviceRegistry.initializeEagerServicesWithScope('plugin', pluginId);
       
       // Modules are initialized before plugins
       const modules = moduleInits.get(pluginId);
       if (modules) {
         const tree = DependencyGraph.fromIterable(
           Array.from(modules).map(([moduleId, moduleInit]) => ({
             value: { moduleId, moduleInit },
             // NOTE: Relationships are REVERSED!
             consumes: Array.from(moduleInit.provides).map(p => p.id),
             provides: Array.from(moduleInit.consumes).map(c => c.id),
           })),
         );
         
         // Parallel topological traversal with circular dependency detection
         await tree.parallelTopologicalTraversal(async ({ moduleId, moduleInit }) => {
           // ...init module
         });
       }
       
       // THEN initialize the plugin itself
       const pluginInit = pluginInits.get(pluginId);
       if (pluginInit) {
         await pluginInit.init.func(pluginDeps);
       }
       
       // THEN signal lifecycle startup
       await lifecycleService.startup();
     }),
   );
   ```

2. **Reversed dependency relationships** — critically confusing comment:
   ```typescript
   // Relationships are reversed at this point since we're only interested in the extension points.
   // If a modules provides extension point A we want it to be initialized AFTER all modules
   // that depend on extension point A, so that they can provide their extensions.
   consumes: Array.from(moduleInit.provides).map(p => p.id),  // REVERSED!
   provides: Array.from(moduleInit.consumes).map(c => c.id),  // REVERSED!
   ```

3. **Service initialization ordering**:
   - Root services: initialized FIRST, `always` by default (eager)
   - Plugin services: initialized per-plugin, `lazy` by default
   - Services can depend on other services → recursive resolution in `ServiceRegistry.get()`

4. **Frontend extension tree** — similarly complex ordering:
   ```
   resolveAppNodeSpecs() → build node spec list with overrides
   resolveAppTree()      → attach nodes to parents based on attachTo specs
   instantiateAppNodeTree() → create instances with dependency resolution
   ```
   - 664 lines in `instantiateAppNodeTree.ts`
   - 297 lines in `resolveAppNodeSpecs.ts`
   - 233 lines in `resolveAppTree.ts`

5. **Lifecycle hooks compound the complexity**:
   ```
   Boot sequence:
   1. Root services init (eager)
   2. Plugin services init (per-plugin, eager ones)
   3. Modules init (topologically sorted, per-plugin)
   4. Plugin init
   5. Plugin lifecycle.startup()
   6. Root lifecycle.startup()
   
   Shutdown sequence (reverse):
   1. Root lifecycle.beforeShutdown()
   2. Plugin lifecycle.shutdown() (all in parallel)
   3. Root lifecycle.shutdown()
   ```

6. **Error handling during init** — partial failure support:
   ```typescript
   // Modules can fail without killing the whole plugin
   resultCollector.onPluginModuleResult(pluginId, moduleId, err);
   // configurable via backend.packages.allowBootFailures
   ```

## Impact on AI

- **Cannot determine execution order**: AI reading `createBackendPlugin` and `createBackendModule` code cannot know which runs first without understanding the topological sort
- **Reversed relationships mislead**: The `consumes/provides` reversal is counter-intuitive and will confuse AI models trying to understand dependency direction
- **Parallel execution**: All plugins init in parallel — AI might assume sequential execution
- **Lifecycle hooks timing**: AI generating lifecycle-dependent code might get the order wrong (e.g., using a service before it's initialized)
- **Partial failure opacity**: Some modules can fail during boot — AI may not account for this when generating error handling code
- **Frontend tree resolution**: 3-phase process (specs → tree → instances) with different rules at each phase

## Key Files (ranked by AI difficulty)

| File | Lines | Complexity |
|------|-------|-----------|
| `backend-app-api/src/wiring/BackendInitializer.ts` | 784 | Topological sort, reversed deps, parallel init, error recovery |
| `frontend-app-api/src/tree/instantiateAppNodeTree.ts` | 664 | Extension tree instantiation with input resolution |
| `backend-app-api/src/wiring/ServiceRegistry.ts` | 359 | Recursive service resolution, root context, scoping |
| `frontend-app-api/src/tree/resolveAppNodeSpecs.ts` | 297 | Plugin/module merge, override resolution |
| `frontend-app-api/src/tree/resolveAppTree.ts` | 233 | Tree construction with redirects and clones |
