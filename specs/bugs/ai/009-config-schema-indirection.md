# AI Issue #009: Config-Driven Behavior with YAML Schema Indirection

## Severity: Medium
## Category: Configuration Comprehension

## Problem

Backstage sử dụng **YAML configuration** (`app-config.yaml`) kết hợp với **typed config interfaces** và **config schema declarations** phân tán khắp các packages. AI khó xác định config nào ảnh hưởng đến behavior nào.

### Evidence

1. **Central config file** (`app-config.yaml`, ~14KB):
   - Contains configuration for ALL plugins, services, and features
   - No schema validation inline — schema lives in separate packages

2. **Config schema per plugin** (via `config.d.ts` files):
   ```
   tsconfig.json includes:
     "packages/*/config.d.ts"
     "plugins/*/config.d.ts"
   ```
   Config schemas are TypeScript declaration files, not the config itself.

3. **Config access pattern** — runtime resolution:
   ```typescript
   // Config is accessed via RootConfigService
   const config = coreServices.rootConfig;
   // Then read at runtime:
   const baseUrl = config.getString('backend.baseUrl');
   ```

4. **Dual config schema systems** (new system coexisting with deprecated):
   ```typescript
   // New: StandardSchemaV1 (from @standard-schema/spec)
   configSchema?: { [key: string]: StandardSchemaV1 }
   
   // Deprecated: Zod via callback
   config?: { schema: { [key: string]: (zImpl: typeof z) => z.ZodType } }
   ```

5. **Config aggregation** via `@backstage/config-loader`:
   - Merges multiple config files
   - Environment variable substitution
   - Secret resolution
   - Conditional config

### Config Resolution Chain

```
app-config.yaml
  → @backstage/config-loader (reads, merges, resolves env vars)
    → @backstage/config (Config interface)
      → coreServices.rootConfig (ServiceRef)
        → config.getString('some.deep.path') (runtime access)
          → plugin-specific config.d.ts (type definition, separate file)
```

## Impact on AI

- **Cannot statically determine configuration effects**: AI must trace from YAML → config loader → service → plugin to understand what a config change does
- **Schema lives far from usage**: Plugin reads `config.getString('catalog.providers.github.org')` but the schema for this lives in a different package's `config.d.ts`
- **String-based config paths**: `config.getString('backend.baseUrl')` — AI must parse string paths to understand structure
- **Two schema systems**: AI might suggest deprecated Zod config schema instead of new StandardSchemaV1
- **Environment-dependent**: Config values can come from env vars (`${MY_ENV_VAR}`), making static analysis of config values impossible
