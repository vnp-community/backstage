# Limitation: Config System

## Package
`@backstage/config`, `@backstage/config-loader`

## Source Files
- `packages/config/src/reader.ts`
- `packages/config/src/types.ts`
- `packages/config-loader/src/loader.ts`

---

## L-CFG-001: No Config Subscription Guarantee

**Severity**: Medium  
**Type**: Design Limitation

The `Config.subscribe()` method is declared as **optional** in the interface:

```typescript
subscribe?(onChange: () => void): {
  unsubscribe: () => void;
};
```

Consumers must check whether `subscribe` is implemented before calling it, creating fragile code paths. There is no compile-time guarantee that hot-reloading is supported, and plugins cannot safely rely on config change notifications.

**Impact**: Plugins that depend on dynamic configuration updates may silently fail if the `Config` implementation does not support `subscribe`.

---

## L-CFG-002: Deep Clone on Every Read

**Severity**: High  
**Type**: Performance

`ConfigReader.getOptional()` calls `cloneDeep()` on every read operation (line 191 in `reader.ts`):

```typescript
const value = cloneDeep(this.readValue(key));
```

The `cloneDeep` implementation recursively copies all nested objects and arrays. For large configuration objects accessed frequently (e.g., in hot paths during request handling), this adds unnecessary memory allocation and GC pressure.

**Impact**: Performance degradation at scale with large configs or frequent reads.

---

## L-CFG-003: Config Key Pattern Restricts Valid Characters

**Severity**: Low  
**Type**: Design Limitation

The config key pattern is restricted to:

```typescript
const CONFIG_KEY_PART_PATTERN = /^[a-z][a-z0-9]*(?:[-_:][a-z0-9]+)*$/i;
```

This prevents:
- Keys starting with numbers
- Keys with consecutive special characters (e.g., `my--key`)
- Keys containing dots (dots are used as path separators)
- Keys with spaces or unicode characters

**Impact**: Configuration from external systems (e.g., Kubernetes ConfigMaps, cloud provider settings) may have keys that cannot be represented in Backstage's config system.

---

## L-CFG-004: Deprecated `loadConfig` API Still Present

**Severity**: Low  
**Type**: Deprecated API

The entire `loadConfig()` function and its associated types (`ConfigTarget`, `LoadConfigOptionsWatch`, `LoadConfigOptionsRemote`, `LoadConfigOptions`, `LoadConfigResult`) are all marked `@deprecated` in favor of `ConfigSources.default`. However, they remain in the public API surface.

**Impact**: Consumer confusion and maintenance burden maintaining two parallel config loading paths.

---

## L-CFG-005: `experimentalEnvFunc` is Unstable

**Severity**: Medium  
**Type**: Stability

The environment variable substitution function in config loading is explicitly marked as experimental:

```typescript
experimentalEnvFunc?: (name: string) => Promise<string | undefined>;
```

**Impact**: Any custom environment variable resolution logic may break without notice in future releases.

---

## L-CFG-006: Config Merge Strategy is Shallow for Arrays

**Severity**: Medium  
**Type**: Design Limitation

The `merge()` function in `reader.ts` performs recursive object merging, but arrays are **not merged** — they are replaced entirely by the higher-priority config:

```typescript
if (typeof into !== 'object' || Array.isArray(into)) {
  return into;
}
```

**Impact**: When layering config files (e.g., `app-config.yaml` + `app-config.local.yaml`), array values in the local file completely override the base file's arrays rather than merging them. This is a common source of confusion for operators.

---

## L-CFG-007: No Config Validation at Load Time

**Severity**: Medium  
**Type**: Missing Feature

`ConfigReader.fromConfigs()` creates a merged config view but performs **no schema validation**. Invalid configurations are only detected when a plugin attempts to read a specific key and encounters a type mismatch.

**Impact**: Misconfigurations are discovered late (at runtime) rather than at startup, leading to harder debugging. Operators may deploy with invalid configs that only surface when specific code paths are hit.

---

## L-CFG-008: `null` Value Used as Delete Marker

**Severity**: Low  
**Type**: Design Quirk

Setting a config value to `null` acts as an explicit removal/override mechanism:

```typescript
if (into === null) {
  return undefined;
}
```

This is not well-documented and can cause unexpected behavior when config sources legitimately contain `null` values.

**Impact**: `null` cannot be used as a valid configuration value; it is silently treated as "remove this key."
