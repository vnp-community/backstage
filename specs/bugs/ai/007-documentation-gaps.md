# AI Issue #007: Inconsistent Documentation — @ignore, @internal, TODO

## Severity: Medium
## Category: Documentation Quality

## Problem

Backstage sử dụng các JSDoc annotations `@ignore`, `@internal`, và có `TODO` comments trong type definitions quan trọng — khiến AI bị thiếu context hoặc hiểu sai API surface.

### Evidence

1. **`@ignore` trên type helpers quan trọng** (13 instances trong wiring/):
   ```typescript
   /** @ignore */
   type ResolvedExtensionInput<...> = ...
   
   /** @ignore */
   export type ResolvedExtensionInputs<...> = ...
   
   /** @ignore */
   type JoinStringUnion<...> = ...
   
   /** @ignore */
   export type RequiredExtensionIds<...> = ...
   
   /** @ignore */
   export type VerifyExtensionFactoryOutput<...> = ...
   ```
   Các types này bị ẩn khỏi API docs nhưng **rất quan trọng** để hiểu cách extension system hoạt động.

2. **`TODO` trong type definition** — chỉ là placeholder:
   ```typescript
   /**
    * TODO       ← no description at all!
    *
    * @public
    */
   export type ExtensionPoint<T> = {
     id: string;
     T: T;
     $$type: '@backstage/ExtensionPoint';
   };
   ```
   `ExtensionPoint` là concept cốt lõi nhưng không có mô tả.

3. **`@internal` annotation inconsistency**:
   - Some `@internal` types are exported publicly (e.g., `InternalBackendFeatureLoader` marked `@public` but all its sibling types are `@internal`)
   - AI tools may filter out `@internal` marked types, missing critical implementation details

4. **TODO comments in implementation**:
   ```typescript
   // TODO(Rugvip): This lives here temporarily, but should be moved...
   // TODO(Rugvip): Making this a type check would be optimal...
   // TODO(Rugvip): Similar to above...
   ```
   These TODOs indicate unstable/temporary code that AI should not treat as stable patterns.

5. **Missing descriptions on some public interfaces**:
   ```typescript
   /** @public */
   export interface BackendFeature {
     // NOTE: This type is opaque in order to simplify future API evolution.
     $$type: '@backstage/BackendFeature';
   }
   ```
   No actual description — just a comment about why it's opaque.

## Impact on AI

- **Hidden type information**: `@ignore` types are excluded from generated API docs, so AI trained on docs won't know about `ResolvedExtensionInputs` or `VerifyExtensionFactoryOutput`
- **TODO = unstable API**: AI may generate code using patterns that are temporary, leading to breakage
- **Inconsistent `@internal` vs `@public`**: AI cannot reliably determine which types are safe to depend on
- **Empty descriptions**: AI needs semantic descriptions to suggest correct usage — `TODO` doesn't help
- **`@public` type with no members**: `BackendFeature` has only `$$type` in its public type — AI can't suggest what to do with it

## Recommendation

For AI-friendly documentation:
1. Replace all `@ignore` with `@remarks` on helper types — they're important for understanding
2. Complete all `TODO` descriptions on public types
3. Add `@see` links from opaque public types to their internal counterparts
4. Consistently use `@alpha`, `@beta`, `@public` instead of mixing with `@internal`
