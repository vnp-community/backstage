# AI Issue #005: Dual Frontend System (Old + New) with Compatibility Layer

## Severity: High
## Category: Architectural Ambiguity

## Problem

Backstage duy trì đồng thời **2 hệ thống frontend** cùng tồn tại:
- **Old system**: `core-plugin-api`, `core-app-api`, `core-components` (prefix `core-`)
- **New system**: `frontend-plugin-api`, `frontend-app-api` (prefix `frontend-`)

Kèm theo **compatibility layer** (`core-compat-api`) để bridge giữa 2 systems.

### Evidence

1. **Parallel package naming**:

   | Old System | New System | Purpose |
   |-----------|------------|---------|
   | `@backstage/core-plugin-api` | `@backstage/frontend-plugin-api` | Plugin API definitions |
   | `@backstage/core-app-api` | `@backstage/frontend-app-api` | App initialization |
   | `@backstage/core-components` | `@backstage/ui` | UI components |
   | `packages/app-legacy` | `packages/app` | Example app |

2. **Compatibility layer** (`packages/core-compat-api/src/`):
   - `convertLegacyPlugin.ts` — converts old plugins to new system
   - `convertLegacyRouteRef.ts` (8939 lines) — converts old RouteRefs
   - `convertLegacyApp.ts` — converts entire old app
   - `convertLegacyPageExtension.tsx` — converts page extensions
   - `collectLegacyRoutes.tsx` — collects routes from old system
   - `compatWrapper/` — wrapping utilities

3. **Both systems have different concepts**:
   - **Old**: `createPlugin()`, `createRouteRef()`, React component-based
   - **New**: `createFrontendPlugin()`, `createExtension()`, `ExtensionBlueprint`, declarative

4. **Example apps** — 2 separate apps:
   - `packages/app/` — new frontend system
   - `packages/app-legacy/` — old frontend system

5. **Plugins support both**:
   - Most plugins in `plugins/` still export old-system components
   - Some are migrated to new system
   - Some support both simultaneously

### Confusion Matrix

```
Q: "How do I create a plugin?"
A1 (old): createPlugin() from @backstage/core-plugin-api
A2 (new): createFrontendPlugin() from @backstage/frontend-plugin-api

Q: "How do I define a route?"
A1 (old): createRouteRef() from @backstage/core-plugin-api
A2 (new): RouteRef from @backstage/frontend-plugin-api (different API)

Q: "How do I register an extension?"
A1 (old): Plugin provides() extensions 
A2 (new): ExtensionBlueprint.make() + attachTo tree
```

## Impact on AI

- **Ambiguous answers**: Khi được hỏi "how to create a plugin?", AI sẽ đưa ra câu trả lời từ hệ thống cũ hoặc mới — cả 2 đều "đúng" nhưng không compatible
- **Mixed imports**: AI có thể suggest imports từ cả 2 systems trong cùng 1 file
- **118+ `@deprecated` annotations**: AI phải xử lý deprecated APIs nhưng nhiều code vẫn dùng chúng
- **Compat layer adds indirection**: `convertLegacyRouteRef.ts` alone is ~9000 lines of complex conversion logic
- **Cannot determine which system a plugin uses**: Must read each plugin's package.json `backstage.role` and actual imports to determine

## Specific AI Failure Scenarios

1. AI generates code using `createPlugin()` (old) khi user đang dùng new system
2. AI mixes `@backstage/core-plugin-api` và `@backstage/frontend-plugin-api` imports
3. AI doesn't know whether to use `<Route>` component (old) or `PageBlueprint.make()` (new)
4. AI suggests deprecated APIs that still compile but will break in future versions
