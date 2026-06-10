# Limitation: Catalog Model

## Package
`@backstage/catalog-model`, `@backstage/catalog-client`

## Source Files
- `packages/catalog-model/src/entity/Entity.ts`
- `packages/catalog-model/src/entity/ref.ts`
- `packages/catalog-model/src/entity/conditions.ts`
- `packages/catalog-model/src/validation/CommonValidatorFunctions.ts`
- `packages/catalog-model/src/validation/KubernetesValidatorFunctions.ts`
- `packages/catalog-client/src/CatalogClient.ts`

---

## L-CAT-001: Entity Name Length Hard Limited to 63 Characters

**Severity**: Medium  
**Type**: Design Constraint

Entity names follow Kubernetes naming conventions, restricting them to 63 characters:

```typescript
static isValidObjectName(value: unknown): boolean {
  return (
    typeof value === 'string' &&
    value.length >= 1 &&
    value.length <= 63 &&
    /^([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9]$/.test(value)
  );
}
```

**Impact**: 
- Auto-generated entity names from long repository paths, URLs, or composite identifiers may be truncated or rejected
- Collision risk increases when long names must be shortened to fit

---

## L-CAT-002: Entity Ref Always Lowercased

**Severity**: Low  
**Type**: Design Decision

`stringifyEntityRef()` converts all parts to lowercase:

```typescript
export function stringifyEntityRef(ref): string {
  return `${kind.toLocaleLowerCase('en-US')}:${namespace.toLocaleLowerCase('en-US')}/${name.toLocaleLowerCase('en-US')}`;
}
```

**Impact**:
- Case-sensitive entity names from source systems (e.g., GitHub repos with mixed case) lose their original casing
- Entities that differ only by case collide (e.g., `MyService` and `myservice` are the same entity)
- Locale-specific lowercase rules (`toLocaleLowerCase('en-US')`) may produce unexpected results for non-ASCII characters

---

## L-CAT-003: Entity `spec` Is Untyped `JsonObject`

**Severity**: Medium  
**Type**: Type Safety

The `spec` field on `Entity` is a loose `JsonObject`:

```typescript
export type Entity = {
  apiVersion: string;
  kind: string;
  metadata: EntityMeta;
  spec?: JsonObject;  // No type safety
};
```

**Impact**:
- No compile-time validation of spec structure
- Custom entity kinds must use runtime validation
- Type narrowing requires explicit type guards for each entity kind
- No IDE autocompletion for spec fields

---

## L-CAT-004: Entity Kind Type Guards Use String Comparison

**Severity**: Low  
**Type**: Code Quality

Entity type guards compare uppercase string values:

```typescript
export function isApiEntity(entity: Entity): entity is ApiEntity {
  return entity.kind.toLocaleUpperCase('en-US') === 'API';
}
```

**Impact**:
- Performance overhead of `toLocaleUpperCase` on every check
- New entity kinds cannot be added without modifying the core package
- No extensible type guard registry for custom kinds

---

## L-CAT-005: Tag Validation is Restrictive

**Severity**: Low  
**Type**: Design Constraint

Tags are limited to lowercase alphanumeric with restricted special chars:

```typescript
static isValidTag(value: unknown): boolean {
  return (
    typeof value === 'string' &&
    value.length >= 1 &&
    value.length <= 63 &&
    /^[a-z0-9+#]+(\-[a-z0-9+#]+)*$/.test(value)
  );
}
```

**Impact**:
- Cannot use common tag formats like `team:backend`, `env=production`, or `cost-center/engineering`
- Tags from external systems may need transformation to fit Backstage's constraints
- Note: This method is already `@deprecated` but no replacement is documented

---

## L-CAT-006: `EntityMeta` Extends `JsonObject` (Duck Typing Risk)

**Severity**: Medium  
**Type**: Type Safety

`EntityMeta` extends `JsonObject`:

```typescript
export type EntityMeta = JsonObject & {
  uid?: string;
  etag?: string;
  name: string;
  // ...
};
```

**Impact**:
- Any `JsonObject` can be assigned to `EntityMeta` without error
- Extra properties are implicitly allowed, meaning typos (e.g., `nam` instead of `name`) won't produce compile errors
- No strict mode for entity metadata validation

---

## L-CAT-007: CatalogClient `getLocationByRef` Loads All Locations

**Severity**: High  
**Type**: Performance

The `getLocationByRef()` method fetches **all locations** and filters client-side:

```typescript
async getLocationByRef(locationRef: string, options?): Promise<Location | undefined> {
  const all = await this.requestRequired(
    await this.apiClient.getLocations({}, options),
  );
  return all.map(r => r.data).find(l => locationRef === stringifyLocationRef(l));
}
```

**Impact**: 
- O(N) performance for location lookups
- Significant network and memory overhead for catalogs with thousands of locations
- No server-side filtering

---

## L-CAT-008: Entity Ref Chunking for `getEntitiesByRefs`

**Severity**: Medium  
**Type**: Design Limitation

The `getEntitiesByRefs()` method splits large ref lists into chunks (via `splitRefsIntoChunks()`) to avoid URL length limits, then reassembles results:

```typescript
for (const refs of splitRefsIntoChunks(request.entityRefs)) {
  const entities = await getOneChunk(refs);
  if (!result) {
    result = entities;
  } else {
    result.push(...entities);
  }
}
```

**Impact**:
- Sequential HTTP calls for large ref lists (not parallelized)
- No single transaction guarantee — partial failures can return inconsistent results
- Chunking logic is split between client and server concerns

---

## L-CAT-009: Deprecated `getEntityByName` Still Active

**Severity**: Low  
**Type**: Technical Debt

`getEntityByName` is deprecated but still implemented:

```typescript
// NOTE(freben): When we deprecate getEntityByName from the interface, we may
// still want to leave this implementation in place for quite some time
// longer, to minimize the risk for breakages. Suggested date for removal: August 2022
```

**Impact**: Deprecated method intended for removal in August 2022 is still present years later, indicating reluctance to make breaking changes.

---

## L-CAT-010: No Cursor Opacity for Query Pagination

**Severity**: Medium  
**Type**: Design Issue

The `queryEntities()` method must inspect cursor contents to determine routing:

```typescript
// TODO(freben): It's costly and non-opaque to have to introspect the cursor
// like this. It should be refactored in the future to not need this.
if (!isInitialRequest && cursorContainsQuery(request.cursor)) {
  return this.queryEntitiesByPredicate(request, options);
}
```

**Impact**:
- Cursors are not truly opaque — the client must understand cursor internals
- Prevents cursor format changes without breaking clients
- Performance cost of cursor inspection on every paginated request

---

## L-CAT-011: No Namespace Enforcement

**Severity**: Medium  
**Type**: Design Limitation

`namespace` defaults silently to `'default'` everywhere:

```typescript
namespace: entity.metadata.namespace || DEFAULT_NAMESPACE,
```

**Impact**:
- Multi-tenant deployments cannot enforce namespace isolation at the model level
- Missing namespace always falls back to "default" rather than producing an error
- No namespace validation against a predefined set

---

## L-CAT-012: Entity Relations Are Unidirectional in Model

**Severity**: Medium  
**Type**: Design Limitation

`EntityRelation` only captures one direction:

```typescript
export type EntityRelation = {
  type: string;
  targetRef: string;  // Only the target, not the source
};
```

**Impact**:
- Reverse lookups ("who depends on me?") require catalog queries rather than direct traversal
- Relationship integrity is not enforced — a relation can point to a non-existent entity
- No relationship metadata (e.g., "since when", "why", "with what configuration")
