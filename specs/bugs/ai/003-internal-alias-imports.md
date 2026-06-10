# AI Issue #003: Private Internal Packages with Alias Imports

## Severity: High
## Category: Code Navigation / Dependency Resolution

## Problem

Backstage sử dụng **private internal packages** với **alias imports** (`@internal/*`) mà không xuất hiện trong node_modules chuẩn, khiến AI không thể resolve import paths và trace dependencies.

### Evidence

1. **`@internal/frontend` (packages/frontend-internal)**:
   - `package.json` name: `"@internal/frontend"`, `"private": true`, `"inline": true`
   - Exports: `OpaqueExtensionDefinition`, `OpaqueExtensionInput`, `createExtensionDataContainer`, etc.
   - Được import bởi 20+ files trong `packages/frontend-plugin-api/src/`

2. **`@internal/opaque` (packages/opaque-internal)**:
   - Exports: `OpaqueType` class
   - Được import bởi blueprint/wiring code

3. **Import chain example**:
   ```
   createExtension.ts
     → import { OpaqueExtensionDefinition } from '@internal/frontend'
       → packages/frontend-internal/src/wiring/InternalExtensionDefinition.ts
         → import { OpaqueType } from '@internal/opaque'
           → packages/opaque-internal/src/OpaqueType.ts
   ```

4. **`@internal/backend` (packages/backend-internal)**:
   - Used by `packages/backend-app-api/` for internal wiring
   - Contains `OpaqueExtensionPointFactoryMiddleware`

5. **Resolution requires workspace configuration**:
   - Yarn workspace resolution via `package.json` `"workspaces"` field
   - `"backstage": { "role": "...", "inline": true }` — custom Backstage CLI metadata
   - Not standard npm aliasing — requires Backstage CLI knowledge

### Affected Import Patterns

```typescript
// These imports CAN'T be resolved by standard tooling
import { createExtensionDataContainer, OpaqueExtensionInput } from '@internal/frontend';
import { OpaqueExtensionDefinition } from '@internal/frontend';
import { OpaqueType } from '@internal/opaque';
```

## Impact on AI

- **Import resolution fails**: AI tools (LSP, static analysis) cannot find `@internal/frontend` as it's a workspace alias, not a published package
- **Cannot "go to definition"**: AI clicking on `OpaqueExtensionDefinition` from `createExtension.ts` won't find the actual source
- **Breaks dependency graph**: AI building a dependency tree of packages won't discover these private internal links
- **`"inline": true` flag is custom**: Only Backstage CLI understands this — standard build tools and AI don't know it means "bundle this inline"
- **3-layer indirection**: Import alias → workspace package → re-exports → actual implementation

## Workaround for AI

To resolve these imports, AI must:
1. Read root `package.json` `workspaces` field
2. Scan all `packages/*/package.json` for matching `name` field
3. Follow `main` or `exports` field to find actual source
4. This is non-trivial and most AI models won't do it automatically

## Affected Packages

| Internal Package | Alias | Used By |
|-----------------|-------|---------|
| `packages/frontend-internal` | `@internal/frontend` | 20+ files in frontend-plugin-api |
| `packages/opaque-internal` | `@internal/opaque` | frontend-plugin-api, core-compat-api |
| `packages/backend-internal` | `@internal/backend` | backend-app-api |
| `packages/cli-internal` | `@internal/cli` | cli-module-* packages |
