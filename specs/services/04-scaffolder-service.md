# 04 — Scaffolder Service

## 1. Tổng quan

Scaffolder Service quản lý software templates và thực thi template workflows. Nó cho phép developers tạo mới components, services, libraries từ predefined templates thông qua một hệ thống task-based với nhiều built-in và custom actions.

**Tương ứng TypeScript**:
- `plugin-scaffolder-backend` — Core scaffolder, task broker, built-in actions
- `plugin-scaffolder-backend-module-github` — GitHub-specific actions (publish, PR)
- `plugin-scaffolder-backend-module-notifications` — Notification actions

## 2. Responsibilities

- **Template Listing**: Lấy danh sách templates từ Catalog Service
- **Task Management**: Tạo, theo dõi, cancel tasks
- **Task Broker**: Queue và dispatch tasks đến workers
- **Action Execution**: Thực thi các actions trong template steps
- **Workspace Management**: Tạo/cleanup temporary workspaces cho mỗi task
- **Template Rendering**: Render Nunjucks templates với input values
- **Dry Run**: Simulate template execution không thực sự tạo resources
- **Autocomplete**: Provide autocomplete suggestions cho template inputs
- **Action Registry**: Register và manage custom actions

## 3. Cấu trúc dự án

```
scaffolder-service/
├── cmd/server/main.go
├── internal/
│   ├── entity/
│   │   ├── template.go              # Template model
│   │   ├── task.go                  # Task model + status
│   │   ├── action.go                # Action definition model
│   │   ├── workspace.go             # Workspace model
│   │   ├── step.go                  # Step execution result
│   │   └── errors.go
│   │
│   ├── usecase/
│   │   ├── interfaces.go
│   │   ├── task_usecase.go          # Create, get, list, cancel tasks
│   │   ├── template_usecase.go      # List templates, get template
│   │   ├── action_usecase.go        # List/execute actions
│   │   ├── autocomplete_usecase.go  # Autocomplete providers
│   │   ├── dryrun_usecase.go        # Dry run execution
│   │   └── broker/
│   │       ├── task_broker.go       # Task queuing & dispatch
│   │       └── task_worker.go       # Task execution worker
│   │
│   ├── adapter/
│   │   ├── handler/
│   │   │   ├── http/
│   │   │   │   ├── router.go
│   │   │   │   ├── task_handler.go
│   │   │   │   ├── template_handler.go
│   │   │   │   ├── action_handler.go
│   │   │   │   ├── autocomplete_handler.go
│   │   │   │   └── events_handler.go    # SSE for task log streaming
│   │   │   └── grpc/
│   │   │       ├── server.go
│   │   │       └── scaffolder_handler.go
│   │   ├── repository/
│   │   │   └── postgres/
│   │   │       ├── task_repo.go
│   │   │       └── step_repo.go
│   │   └── action/                      # Built-in action implementations
│   │       ├── registry.go              # Action registry
│   │       ├── fetch_plain.go           # fetch:plain
│   │       ├── fetch_plain_file.go      # fetch:plain:file
│   │       ├── fetch_template.go        # fetch:template
│   │       ├── fetch_template_file.go   # fetch:template:file
│   │       ├── catalog_register.go      # catalog:register
│   │       ├── catalog_write.go         # catalog:write
│   │       ├── catalog_fetch.go         # catalog:fetch
│   │       ├── debug_log.go             # debug:log
│   │       ├── debug_wait.go            # debug:wait
│   │       ├── fs_delete.go             # fs:delete
│   │       ├── fs_rename.go             # fs:rename
│   │       ├── fs_read_dir.go           # fs:readdir
│   │       ├── github_publish.go        # publish:github
│   │       ├── github_pr.go             # publish:github:pull-request
│   │       └── notification_send.go     # notification:send
│   │
│   └── infrastructure/
│       ├── config/config.go
│       ├── database/
│       │   ├── postgres.go
│       │   └── migrations/
│       │       ├── 000001_create_tasks.up.sql
│       │       └── 000002_create_steps.up.sql
│       ├── server/
│       │   ├── http.go
│       │   └── grpc.go
│       ├── template/
│       │   ├── nunjucks.go          # Nunjucks template renderer (Go implementation)
│       │   ├── filters.go           # Custom template filters
│       │   └── globals.go           # Template global functions
│       ├── workspace/
│       │   └── workspace_provider.go # Temp directory management
│       └── client/
│           ├── catalog_client.go    # Get templates from catalog
│           ├── permission_client.go
│           └── scm_client.go        # Git operations
│
├── api/
│   ├── proto/scaffolder.proto
│   └── openapi/openapi.yaml
├── migrations/
├── config/config.yaml
├── Dockerfile
└── go.mod
```

## 4. Entity Models

```go
// internal/entity/task.go

type TaskStatus string

const (
    TaskStatusOpen       TaskStatus = "open"
    TaskStatusProcessing TaskStatus = "processing"
    TaskStatusCompleted  TaskStatus = "completed"
    TaskStatusFailed     TaskStatus = "failed"
    TaskStatusCancelled  TaskStatus = "cancelled"
)

type Task struct {
    ID              string            `json:"id"`
    Spec            TaskSpec          `json:"spec"`
    Status          TaskStatus        `json:"status"`
    CreatedAt       time.Time         `json:"createdAt"`
    LastHeartbeatAt *time.Time        `json:"lastHeartbeatAt,omitempty"`
    CompletedAt     *time.Time        `json:"completedAt,omitempty"`
    CreatedBy       string            `json:"createdBy"` // user entity ref
    Secrets         map[string]string `json:"-"`         // never serialized
}

type TaskSpec struct {
    APIVersion      string              `json:"apiVersion"`
    TemplateRef     string              `json:"templateRef"`
    Parameters      map[string]any      `json:"parameters"`
    Steps           []TaskStep          `json:"steps"`
    Output          map[string]string   `json:"output,omitempty"`
}

type TaskStep struct {
    ID     string         `json:"id"`
    Name   string         `json:"name"`
    Action string         `json:"action"` // e.g. "fetch:template"
    Input  map[string]any `json:"input,omitempty"`
    If     string         `json:"if,omitempty"` // condition expression
}

type StepResult struct {
    StepID      string         `json:"stepId"`
    Status      TaskStatus     `json:"status"`
    Output      map[string]any `json:"output,omitempty"`
    StartedAt   time.Time      `json:"startedAt"`
    CompletedAt *time.Time     `json:"completedAt,omitempty"`
    Error       string         `json:"error,omitempty"`
}

type TaskEvent struct {
    Type    string `json:"type"`    // "log", "completion"
    Body    any    `json:"body"`
    TaskID  string `json:"taskId"`
    StepID  string `json:"stepId,omitempty"`
    Created time.Time `json:"createdAt"`
}

type TaskLogEntry struct {
    Message   string `json:"message"`
    LogLevel  string `json:"logLevel"` // info, warn, error
    Timestamp time.Time `json:"createdAt"`
}
```

```go
// internal/entity/action.go

type Action struct {
    ID          string       `json:"id"`          // "fetch:template"
    Description string       `json:"description"`
    Schema      ActionSchema `json:"schema,omitempty"`
    Examples    []ActionExample `json:"examples,omitempty"`
}

type ActionSchema struct {
    Input  json.RawMessage `json:"input,omitempty"`  // JSON Schema
    Output json.RawMessage `json:"output,omitempty"` // JSON Schema
}

// ActionHandler is the interface each action must implement
type ActionHandler interface {
    ID() string
    Description() string
    Schema() ActionSchema
    Execute(ctx context.Context, input ActionInput) (*ActionOutput, error)
}

type ActionInput struct {
    Parameters    map[string]any
    WorkspacePath string
    Logger        Logger
    TemplateInfo  *TemplateInfo
    Secrets       map[string]string
    UserEntityRef string
}

type ActionOutput struct {
    Output map[string]any
    Links  []OutputLink
}

type OutputLink struct {
    Title string `json:"title"`
    URL   string `json:"url"`
    Icon  string `json:"icon,omitempty"`
}
```

## 5. Use Case Interfaces

```go
// internal/usecase/interfaces.go

type TaskRepository interface {
    Create(ctx context.Context, task *entity.Task) error
    GetByID(ctx context.Context, id string) (*entity.Task, error)
    List(ctx context.Context, filter TaskListFilter) ([]entity.Task, error)
    UpdateStatus(ctx context.Context, id string, status entity.TaskStatus) error
    Heartbeat(ctx context.Context, id string) error
    Cancel(ctx context.Context, id string) error
    
    // Step results
    SaveStepResult(ctx context.Context, taskID string, result *entity.StepResult) error
    GetStepResults(ctx context.Context, taskID string) ([]entity.StepResult, error)
    
    // Event log
    AppendEvent(ctx context.Context, taskID string, event *entity.TaskEvent) error
    GetEvents(ctx context.Context, taskID string, after int64) ([]entity.TaskEvent, error)
}

type TaskListFilter struct {
    CreatedBy string
    Status    entity.TaskStatus
    Limit     int
    Offset    int
}

type ActionRegistry interface {
    Register(handler ActionHandler)
    Get(id string) (ActionHandler, error)
    List() []entity.Action
}

type WorkspaceProvider interface {
    Create(ctx context.Context, taskID string) (string, error)  // returns workspace path
    Cleanup(ctx context.Context, taskID string) error
}

type TemplateRenderer interface {
    Render(template string, values map[string]any) (string, error)
    RenderFile(templatePath string, outputPath string, values map[string]any) error
}

type CatalogClient interface {
    GetTemplates(ctx context.Context) ([]entity.Entity, error)
    GetTemplate(ctx context.Context, templateRef string) (*entity.Entity, error)
    RegisterEntity(ctx context.Context, entityRef string) error
}
```

## 6. API Endpoints

### 6.1 REST API

| Method | Path | Description |
|---|---|---|
| `GET` | `/v2/templates` | List available templates |
| `GET` | `/v2/templates/:templateRef` | Get template detail |
| `POST` | `/v2/tasks` | Create new task (execute template) |
| `GET` | `/v2/tasks` | List tasks |
| `GET` | `/v2/tasks/:taskId` | Get task status |
| `POST` | `/v2/tasks/:taskId/cancel` | Cancel running task |
| `GET` | `/v2/tasks/:taskId/events` | SSE stream for task events/logs |
| `GET` | `/v2/tasks/:taskId/eventstream` | SSE stream (alternative) |
| `POST` | `/v2/dry-runs` | Dry run template execution |
| `GET` | `/v2/actions` | List all available actions |
| `POST` | `/v2/autocomplete/:provider/:resource` | Autocomplete for template inputs |

### 6.2 gRPC API

```protobuf
syntax = "proto3";
package backstage.scaffolder.v1;

service ScaffolderService {
    rpc CreateTask(CreateTaskRequest) returns (CreateTaskResponse);
    rpc GetTask(GetTaskRequest) returns (TaskResponse);
    rpc ListTasks(ListTasksRequest) returns (ListTasksResponse);
    rpc CancelTask(CancelTaskRequest) returns (google.protobuf.Empty);
    rpc StreamTaskEvents(StreamTaskEventsRequest) returns (stream TaskEvent);
    rpc ListActions(ListActionsRequest) returns (ListActionsResponse);
}
```

## 7. Database Schema

```sql
-- migrations/000001_create_tasks.up.sql

CREATE TABLE scaffolder_tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spec            JSONB NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'open',
    created_by      VARCHAR(255) NOT NULL,
    secrets         BYTEA,                   -- encrypted secrets
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_heartbeat  TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ
);

CREATE INDEX idx_tasks_status ON scaffolder_tasks(status);
CREATE INDEX idx_tasks_created_by ON scaffolder_tasks(created_by);
CREATE INDEX idx_tasks_created_at ON scaffolder_tasks(created_at DESC);

-- Task events/logs (append-only)
CREATE TABLE scaffolder_task_events (
    id        BIGSERIAL PRIMARY KEY,
    task_id   UUID NOT NULL REFERENCES scaffolder_tasks(id) ON DELETE CASCADE,
    type      VARCHAR(50) NOT NULL,      -- "log", "completion", "cancelled"
    body      JSONB NOT NULL,
    step_id   VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_task_events_task ON scaffolder_task_events(task_id, id);
```

```sql
-- migrations/000002_create_steps.up.sql

CREATE TABLE scaffolder_step_results (
    id          BIGSERIAL PRIMARY KEY,
    task_id     UUID NOT NULL REFERENCES scaffolder_tasks(id) ON DELETE CASCADE,
    step_id     VARCHAR(255) NOT NULL,
    status      VARCHAR(50) NOT NULL,
    output      JSONB,
    error       TEXT,
    started_at  TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    
    UNIQUE(task_id, step_id)
);
```

## 8. Task Broker Architecture

```go
// internal/usecase/broker/task_broker.go

type TaskBroker struct {
    repo      TaskRepository
    workers   int
    actions   ActionRegistry
    workspace WorkspaceProvider
    renderer  TemplateRenderer
    publisher EventPublisher
    logger    zerolog.Logger
    
    taskChan  chan *entity.Task
    stopChan  chan struct{}
}

func (b *TaskBroker) Start(ctx context.Context) {
    // Launch worker pool
    for i := 0; i < b.workers; i++ {
        go b.worker(ctx, i)
    }
    
    // Polling loop for pending tasks
    go b.pollPendingTasks(ctx)
}

func (b *TaskBroker) worker(ctx context.Context, workerID int) {
    for task := range b.taskChan {
        b.executeTask(ctx, task)
    }
}

func (b *TaskBroker) executeTask(ctx context.Context, task *entity.Task) {
    // 1. Create workspace
    workDir, _ := b.workspace.Create(ctx, task.ID)
    defer b.workspace.Cleanup(ctx, task.ID)
    
    // 2. Update status to processing
    b.repo.UpdateStatus(ctx, task.ID, entity.TaskStatusProcessing)
    
    // 3. Execute each step sequentially
    stepOutputs := make(map[string]any)
    for _, step := range task.Spec.Steps {
        // Check if step condition is met
        if step.If != "" && !evaluateCondition(step.If, stepOutputs) {
            continue
        }
        
        // Resolve action handler
        handler, err := b.actions.Get(step.Action)
        if err != nil {
            b.failTask(ctx, task.ID, step.ID, err)
            return
        }
        
        // Render step inputs with template values
        renderedInput := b.renderInputs(step.Input, task.Spec.Parameters, stepOutputs)
        
        // Execute action
        output, err := handler.Execute(ctx, ActionInput{
            Parameters:    renderedInput,
            WorkspacePath: workDir,
            Secrets:       task.Secrets,
            UserEntityRef: task.CreatedBy,
        })
        
        if err != nil {
            b.failTask(ctx, task.ID, step.ID, err)
            return
        }
        
        stepOutputs[step.ID] = output.Output
        b.repo.SaveStepResult(ctx, task.ID, &entity.StepResult{
            StepID: step.ID, Status: entity.TaskStatusCompleted, Output: output.Output,
        })
    }
    
    // 4. Mark task as completed
    b.repo.UpdateStatus(ctx, task.ID, entity.TaskStatusCompleted)
    b.publisher.PublishTaskCompleted(ctx, task)
}
```

## 9. Built-in Actions

| Action ID | Description | Key Inputs |
|---|---|---|
| `fetch:plain` | Download files from URL | `url`, `targetPath` |
| `fetch:plain:file` | Download single file | `url`, `targetPath` |
| `fetch:template` | Fetch & render template directory | `url`, `targetPath`, `values` |
| `fetch:template:file` | Fetch & render single template file | `url`, `targetPath`, `values` |
| `catalog:register` | Register entity in catalog | `catalogInfoUrl` |
| `catalog:write` | Write catalog-info.yaml | `entity`, `filePath` |
| `catalog:fetch` | Fetch entity from catalog | `entityRef` |
| `debug:log` | Log message | `message`, `listWorkspace` |
| `debug:wait` | Wait for duration | `minutes`, `seconds` |
| `fs:delete` | Delete files/dirs | `files` |
| `fs:rename` | Rename files | `files` (array of from→to) |
| `fs:readdir` | List directory contents | `path` |
| `publish:github` | Create GitHub repo & push code | `repoUrl`, `description`, `defaultBranch` |
| `publish:github:pull-request` | Create GitHub PR | `repoUrl`, `title`, `branchName` |
| `notification:send` | Send notification | `recipients`, `title`, `description` |

## 10. Configuration

```yaml
scaffolder:
  workers: 4
  workspace:
    base_dir: "/tmp/backstage-scaffolder"
    cleanup_after: "1h"
  
  task:
    heartbeat_interval: "10s"
    stale_timeout: "5m"
    max_concurrent: 10
  
  template:
    nunjucks:
      autoescape: false

database:
  host: "postgres-scaffolder"
  port: 5432
  name: "backstage_scaffolder"
  user: "${DB_USER}"
  password: "${DB_PASSWORD}"
```
