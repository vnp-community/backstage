# AI Issue #012: Runtime Plugin Discovery via require() and Package Scanning

## Severity: High
## Category: Static Analysis Gap

## Problem

Backstage backend sử dụng **runtime `require()` và filesystem scanning** để phát hiện và load plugins. Toàn bộ plugin graph chỉ tồn tại tại runtime, không thể phân tích statically.

### Evidence

1. **`PackageDiscoveryService.getBackendFeatures()`** — scan runtime dependencies:
   ```typescript
   async getBackendFeatures(): Promise<{ features: Array<BackendFeature> }> {
     const packageDir = await findClosestPackageDir(process.argv[1]);
     const dependencyNames = this.getDependencyNames(
       resolvePath(packageDir, 'package.json'),
     );
     
     for (const name of dependencyNames) {
       // Dynamic require to read package.json
       depPkg = require(packageJsonPath) as BackstagePackageJson;
       
       // Check backstage.role metadata
       if (!DETECTED_PACKAGE_ROLES.includes(depPkg.backstage.role)) {
         continue;
       }
       
       // Dynamic require to load the module
       const mod = require(modulePath);
       
       // Runtime type check via $$type marker
       if (isBackendFeature(mod.default)) {
         features.push(mod.default);
       }
     }
   }
   ```

2. **Runtime type checks** — duck typing via `$$type`:
   ```typescript
   function isBackendFeature(value: unknown): value is BackendFeature {
     return (
       !!value &&
       ['object', 'function'].includes(typeof value) &&
       (value as BackendFeature).$$type === '@backstage/BackendFeature'
     );
   }
   
   function isBackendFeatureFactory(value: unknown): value is () => BackendFeature {
     return (
       !!value &&
       typeof value === 'function' &&
       (value as any).$$type === '@backstage/BackendFeatureFactory'
     );
   }
   ```

3. **Config-driven plugin filtering**:
   ```typescript
   // backend.packages can be 'all', or { include: [...], exclude: [...] }
   const packagesConfig = this.config.getOptional('backend.packages');
   ```
   Plugin list depends on runtime config.

4. **`BackendInitializer`** — processes features asynchronously:
   ```typescript
   // Features are promises that resolve at runtime
   #registeredFeatures = new Array<Promise<BackendFeature>>();
   
   // Feature loaders can return MORE features recursively
   async #applyBackendFeatureLoaders(loaders: InternalBackendFeatureLoader[]) {
     for (const loader of loaders) {
       const result = await loader.loader(Object.fromEntries(deps));
       for await (const feature of result) {
         if (isBackendFeatureLoader(feature)) {
           newLoaders.push(feature);  // recursive!
         } else {
           this.#addFeature(feature);
         }
       }
       // Apply loaders recursively, depth-first
       if (newLoaders.length > 0) {
         await this.#applyBackendFeatureLoaders(newLoaders);
       }
     }
   }
   ```

5. **Dynamic feature loading (frontend)**:
   - `packages/frontend-dynamic-feature-loader/` — loads frontend features from network at runtime
   - `packages/backend-dynamic-feature-service/` — full dynamic feature management with scanner, loader, schemas

6. **Lazy `require()` for optional dependencies** — 15+ instances in `backend-defaults`:
   ```typescript
   // Only loaded if config says "redis"
   const KeyvRedis = require('@keyv/redis').default;
   
   // Only loaded if config says "postgres"
   const { AuthTypes } = require('@google-cloud/cloud-sql-connector');
   ```

## Impact on AI

- **Impossible to build full dependency graph statically**: AI must run the application to know which plugins are loaded
- **`require()` bypasses TypeScript**: No type information for dynamically loaded modules — AI sees `any`
- **Recursive feature loaders**: Feature loaders can load more loaders — the plugin graph is infinitely expandable at runtime
- **Config-dependent**: The same codebase loads different plugins based on `app-config.yaml` — AI analyzing code without config context will miss plugins
- **`process.argv[1]` dependency**: Discovery starts from the runtime entry point, which varies between `yarn start`, `yarn build`, Docker, etc.
- **Optional deps invisible**: Packages like `@keyv/redis`, `@aws-sdk/rds-signer` are loaded via `require()` only when needed — not in `import` statements

## Specific AI Failure Scenarios

1. **"What plugins does this backend run?"** → Cannot answer without reading `app-config.yaml` AND `package.json` AND running the discovery service
2. **"What services are available?"** → Depends on which ServiceFactory implementations are loaded by feature loaders at runtime
3. **"Add a new backend plugin"** → AI might suggest code imports, but the plugin must also be added to package.json and potentially to config
4. **Code navigation**: AI cannot find where `@keyv/redis` is used because it's loaded via `require()` inside a conditional branch
