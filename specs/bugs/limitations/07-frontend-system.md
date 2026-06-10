# Limitation: Frontend System & Core Components

## Package
`@backstage/frontend-plugin-api`, `@backstage/frontend-app-api`, `@backstage/core-components`, `@backstage/core-plugin-api`

## Source Files
- `packages/frontend-app-api/src/tree/*.ts`
- `packages/frontend-app-api/src/wiring/*.ts`
- `packages/frontend-plugin-api/src/wiring/*.ts`
- `packages/core-components/src/layout/SignInPage/UserIdentity.ts`
- `packages/core-app-api/src/apis/implementations/AppThemeApi/*.ts`
- `packages/core-compat-api/src/convertLegacyApp.ts`

---

## L-FE-001: Two Parallel Frontend Systems

**Severity**: High  
**Type**: Architecture Complexity

Backstage maintains two frontend systems simultaneously:
- **Old system**: `core-*` packages (`core-plugin-api`, `core-app-api`, `core-components`)
- **New system**: `frontend-*` packages (`frontend-plugin-api`, `frontend-app-api`)

A compatibility layer (`core-compat-api`) bridges them, with deprecated conversion functions.

**Impact**:
- Double maintenance burden
- Confusion for plugin authors about which system to target
- Larger bundle sizes when both systems are loaded
- The compat layer adds runtime overhead

---

## L-FE-002: Extension Tree Resolution Has Incomplete Config Merge

**Severity**: Medium  
**Type**: Incomplete Implementation

In `resolveAppNodeSpecs.ts`:

```typescript
// TODO: merge config?
```

**Impact**: When extension instances have overlapping config, the merge behavior is undefined. Later config silently overwrites earlier config without deep merging.

---

## L-FE-003: Root Node `attachTo` Spec is Ignored

**Severity**: Low  
**Type**: Design Workaround

In `resolveAppTree.ts`:

```typescript
// TODO: For now we simply ignore the attachTo spec of the root node,
// but it'd be cleaner if we could avoid defining it
```

**Impact**: The root node must still define an `attachTo` spec even though it's never used, creating confusion in the API.

---

## L-FE-004: Limited Extension Variant Support

**Severity**: Medium  
**Type**: Incomplete Feature

In `createPluginInfoAttacher.ts`:

```typescript
// TODO(Rugvip): Support more variants
```

**Impact**: The plugin info attacher only supports a limited set of extension variants, restricting what metadata can be automatically attached to extensions.

---

## L-FE-005: `AppThemeSelector` / `AppLanguageSelector` Require Manual Cleanup

**Severity**: Medium  
**Type**: Resource Management

Both selectors explicitly document cleanup requirements:

```typescript
/**
 * Call this method when the selector is no longer needed to prevent memory leaks.
 */
```

**Impact**: 
- No automatic cleanup via React lifecycle or disposable patterns
- Forgetting to call cleanup causes memory leaks in long-running SPAs
- No integration with React's `useEffect` cleanup pattern

---

## L-FE-006: Deprecated `GuestUserIdentity` Still in Core

**Severity**: Low  
**Type**: Technical Debt

```typescript
/**
 * @deprecated Use `@backstage/plugin-auth-backend-module-guest-provider` instead.
 */
```

The guest user identity remains in `core-components` despite being deprecated in favor of a backend module. This pattern appears across many deprecated APIs in `frontend-test-utils`.

**Impact**: Large deprecated API surface creates confusion and bloats bundle size.

---

## L-FE-007: `convertLegacyApp` is Deprecated with No Clear Timeline

**Severity**: Medium  
**Type**: Migration Risk

The legacy app conversion functions in `core-compat-api` are deprecated but provide no migration timeline:

```typescript
/** @deprecated */
export function collectLegacyRoutes(/* ... */): void { /* ... */ }
```

**Impact**: Organizations with large plugin ecosystems have no clear timeline for when legacy support will be removed, making migration planning difficult.

---

## L-FE-008: CSP Configuration Workarounds

**Severity**: Medium  
**Type**: Security

Multiple CSP-related workarounds exist in the HTTP configuration:

```typescript
// TODO(Rugvip): We currently use non-precompiled AJV for validation in the frontend, which uses eval.
// TODO(Rugvip): This is removed so that we maintained backwards compatibility
```

**Impact**:
- Content Security Policy must allow `eval` for AJV schema validation in the frontend
- The default CSP is more permissive than necessary for security
- Backwards compatibility prevents tightening CSP settings

---

## L-FE-009: Helmet Configuration Not Consumer-Controlled

**Severity**: Medium  
**Type**: Customization

In `readHelmetOptions.ts`:

```typescript
// TODO(Rugvip): We should give control of this setup to consumers
```

**Impact**: The HTTP security headers (via Helmet) are hardcoded with limited configurability. Consumers who need custom security header policies must work around the defaults.
