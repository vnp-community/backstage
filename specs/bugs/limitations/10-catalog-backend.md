# Limitation: Catalog Processing Engine

## Package
`@backstage/plugin-catalog-backend`

## Source Files
- `plugins/catalog-backend/src/processing/DefaultCatalogProcessingEngine.ts`
- `plugins/catalog-backend/src/processing/TaskPipeline.ts`

---

## L-CPE-001: Polling-Based Processing Loop

**Severity**: High  
**Type**: Architecture Limitation

The catalog processing engine works by polling the database every second:

```typescript
const pollingIntervalMs = options.pollingIntervalMs ?? 1_000;

const stopPipeline = startTaskPipeline<RefreshStateItem>({
  lowWatermark: 5,
  highWatermark: 10,
  pollingIntervalMs: this.pollingIntervalMs,
  // ...
});
```

**Impact**:
- Constant polling even when there are no entities to process
- Database is queried every second regardless of catalog size
- Latency from SCM change → catalog update = polling interval + processing time
- Does not scale horizontally efficiently (multiple workers all polling simultaneously)

---

## L-CPE-002: Fixed Batch Size (High Watermark = 10)

**Severity**: Medium  
**Type**: Configuration Gap

The task pipeline hardcodes batch size limits:

```typescript
startTaskPipeline<RefreshStateItem>({
  lowWatermark: 5,
  highWatermark: 10,
  // ...
```

**Impact**:
- Cannot process more than 10 entities concurrently per process
- Large catalogs (100k+ entities) take proportionally long to process
- No adaptive batch sizing based on available system resources

---

## L-CPE-003: Deprecated Prometheus Metrics Alongside OpenTelemetry

**Severity**: Low  
**Type**: Technical Debt

The processing engine emits both deprecated prom-client metrics AND new OpenTelemetry metrics simultaneously:

```typescript
// prom-client metrics are deprecated in favour of OpenTelemetry metrics.
const promProcessedEntities = createCounterMetric({
  name: 'catalog_processed_entities_count',
  help: 'Amount of entities processed, DEPRECATED, use OpenTelemetry metrics instead',
});

// New OTel metrics also emitted
const processedEntities = metrics.createCounter('catalog.processed.entities.count', ...);
```

**Impact**:
- Duplicate metrics emitted for every entity processed
- Confusion in monitoring dashboards (two versions of the same metric)
- Runtime overhead of emitting duplicate telemetry

---

## L-CPE-004: Result Hash Comparison Uses `stableStringify` on Full Entity

**Severity**: Medium  
**Type**: Performance

To detect changes, the engine serializes the entire entity and its relations to compute a hash:

```typescript
hashBuilder = hashBuilder
  .update(stableStringify({ ...result.completedEntity }))
  .update(stableStringifyArray([...result.deferredEntities]))
  .update(stableStringifyArray([...result.relations]))
  .update(stableStringifyArray([...result.refreshKeys]))
  .update(stableStringifyArray([...parents]));
```

**Impact**:
- Every processing run for every entity serializes the full entity to JSON
- Large entities or entities with many relations have significant serialization overhead
- `stableStringify` sorts all keys for canonical representation — O(n log n) for each entity

---

## L-CPE-005: Orphan Cleanup Runs Independent of Processing

**Severity**: Low  
**Type**: Race Condition Risk

The orphan cleanup job runs every 30 seconds independently from the main processing loop:

```typescript
this.scheduler.scheduleTask({
  id: 'catalog_orphan_cleanup',
  frequency: { milliseconds: this.orphanCleanupIntervalMs },  // default 30_000
  timeout: { milliseconds: this.orphanCleanupIntervalMs * 0.8 },
  fn: runOnce,
});
```

**Impact**:
- A race condition exists: an entity could be classified as "orphaned" while its provider is mid-update
- Tight timeout (80% of interval) means the cleanup may be interrupted before completing on large catalogs
- No coordination with active processing runs

---

## L-CPE-006: Error Events Published to EventsService But Not Awaited

**Severity**: Low  
**Type**: Fire-and-Forget

When processing errors occur, the error event is published without awaiting the result:

```typescript
if (result.errors.length) {
  this.events.publish({
    topic: CATALOG_ERRORS_TOPIC,
    eventPayload: { entity: entityRef, location, errors: result.errors },
  });
  // No await!
}
```

**Impact**:
- If event publishing fails (e.g., broker is down), the error is silently discarded
- Callers subscribed to `CATALOG_ERRORS_TOPIC` may not receive all error events under load

---

## L-CPE-007: Processing State TTL is Hardcoded to 5

**Severity**: Low  
**Type**: Configuration Gap

The cache TTL for entity processing state is a magic constant:

```typescript
const CACHE_TTL = 5;

await this.processingDatabase.updateEntityCache(tx, {
  id,
  state: { ttl: CACHE_TTL, ...result.state },
});
```

**Impact**:
- TTL semantics are unclear from the value alone (5 what? processing cycles?)
- Not configurable — operators cannot tune cache retention based on their catalog size

---

## L-CPE-008: No Back-Pressure on Processing Queue

**Severity**: Medium  
**Type**: Resilience

The task pipeline uses a simple low/high watermark model with no back-pressure:

```typescript
const stopPipeline = startTaskPipeline<RefreshStateItem>({
  lowWatermark: 5,
  highWatermark: 10,
  // ...
```

**Impact**:
- If processing is slow (external SCM is slow), the pipeline still polls for new tasks
- No exponential backoff when processing repeatedly fails
- Downstream resource exhaustion (DB connections, network) is not signaled upstream
