# Limitation: Scaffolder Plugin

## Package
`@backstage/plugin-scaffolder-backend`, `@backstage/plugin-scaffolder-node`

## Source Files
- `plugins/scaffolder-backend/src/scaffolder/tasks/NunjucksWorkflowRunner.ts`
- `plugins/scaffolder-backend/src/scaffolder/tasks/StorageTaskBroker.ts`
- `plugins/scaffolder-backend/src/scaffolder/tasks/DatabaseTaskStore.ts`

---

## L-SCF-001: Task Recovery is Fully Experimental

**Severity**: High  
**Type**: Reliability Gap

Task recovery uses `EXPERIMENTAL_` prefix throughout:

```typescript
const enabled =
  this.config?.getOptionalBoolean('scaffolder.EXPERIMENTAL_recoverTasks') ?? false;

const isRecoverableTask = task.spec.EXPERIMENTAL_recovery?.EXPERIMENTAL_strategy === 'startOver';
```

**Impact**:
- Task recovery after node crash is not production-stable
- `startOver` is the only recovery strategy — no "resume from last checkpoint" as default
- No clear migration path from experimental → stable API
- Operators enabling this feature cannot rely on its behavior across upgrades

---

## L-SCF-002: Task Events Polled Every Second

**Severity**: Medium  
**Type**: Performance

The `event$()` observable polls the database every 1 second for new events:

```typescript
await new Promise(resolve => setTimeout(resolve, 1000));
```

**Impact**:
- Every active task creates a continuous database polling loop
- N concurrent scaffolder tasks = N database queries per second
- Does not scale well when thousands of tasks run concurrently
- Long-running tasks (e.g., template rendering) hold database connections continuously

---

## L-SCF-003: Task Workspace Stored as Binary BLOB in Database

**Severity**: High  
**Type**: Architecture Limitation

The workspace (files written during scaffolding) is serialized and stored as a binary `Buffer` column in the database:

```typescript
export type RawDbTaskRow = {
  workspace?: Buffer;
};

async serializeWorkspace(options: { path: string; taskId: string }): Promise<void> {
  const workspace = (await serializeWorkspace(options)).contents;
  await this.db<RawDbTaskRow>('tasks').where({ id: options.taskId }).update({ workspace });
}
```

**Impact**:
- Large workspaces (many files or binary assets) create very large database rows
- PostgreSQL row size limitations can be hit for complex templates
- No streaming — the entire workspace is loaded into memory for rehydration
- Replication lag for large BLOBs in high-availability setups
- Database backup size grows proportionally with active/stuck tasks

---

## L-SCF-004: Heartbeat is Hardcoded to 1 Second

**Severity**: Low  
**Type**: Configuration Gap

The task heartbeat interval is hardcoded:

```typescript
this.heartbeatTimeoutId = setTimeout(async () => {
  await this.storage.heartbeatTask(this.task.taskId);
  this.startTimeout();
}, 1000);  // 1000ms hardcoded
```

**Impact**:
- Cannot configure heartbeat frequency without code changes
- In high-latency database environments, the 1-second interval may cause false "stale task" detection
- Each active task makes 1 DB write per second just for heartbeating

---

## L-SCF-005: No Task Queue Priority

**Severity**: Medium  
**Type**: Missing Feature

Tasks are claimed in FIFO order (first `open` task found):

```typescript
const [task] = await tx<RawDbTaskRow>('tasks')
  .where({ status: 'open' })
  .limit(1)
  .select();
```

**Impact**:
- No priority queue — critical operations cannot preempt long-running low-priority tasks
- A single slow task does not block others, but high-priority scaffolding requests wait behind existing queue
- No SLA enforcement per template type

---

## L-SCF-006: Nunjucks Template Rendering in Single Thread

**Severity**: Medium  
**Type**: Performance

Template rendering using `SecureTemplater` runs in the same Node.js thread as the HTTP server:

```typescript
const { render: renderTemplate, dispose } = await SecureTemplater.loadRenderer({ ... });
```

**Impact**:
- CPU-intensive template rendering blocks the Node.js event loop
- Under load, scaffolder template rendering degrades overall backend responsiveness
- No worker thread isolation for template execution

---

## L-SCF-007: Task Secrets Stored as Plain JSON in Database

**Severity**: High  
**Type**: Security

Task secrets are serialized and stored directly in the database:

```typescript
await this.db<RawDbTaskRow>('tasks').insert({
  secrets: options.secrets ? JSON.stringify(options.secrets) : undefined,
  // ...
});
```

**Impact**:
- Secrets at rest are not encrypted (only as secure as database access controls)
- Secrets are visible in database backups and replicas
- No key rotation or secret versioning mechanism
- For recoverable tasks, secrets are retained in the database longer (non-recoverable tasks null-out secrets on claim)

---

## L-SCF-008: Task Log Events Grow Unboundedly

**Severity**: Medium  
**Type**: Database Growth

Every log message emitted during task execution is stored permanently in `task_events` table:

```typescript
async emitLogEvent(options: TaskStoreEmitOptions): Promise<void> {
  await this.db<RawDbTaskEventRow>('task_events').insert({ ... });
}
```

**Impact**:
- No TTL or automatic cleanup for old task events
- Long-running or verbose tasks can produce thousands of event rows
- `task_events` table grows indefinitely without a manual vacuum/cleanup process

---

## L-SCF-009: Cancel Detects Current Step by Scanning All Events

**Severity**: Low  
**Type**: Performance

Task cancellation determines the current step by loading all events and scanning them:

```typescript
async cancel(taskId: string) {
  const { events } = await this.storage.listEvents({ taskId });
  const currentStepId = events
    .filter(({ body }) => body?.stepId)
    .reduce((prev, curr) => (prev.id > curr.id ? prev : curr)).body.stepId;
```

**Impact**:
- O(N) event scan for every cancel operation, where N is all events for the task
- For long-running tasks with many log events, this query returns and processes thousands of rows just to cancel
