# 09 — Notification Service

## 1. Tổng quan

Notification Service quản lý user notifications — tạo, đọc, đánh dấu read/unread, gửi qua nhiều channels (in-app, email, Slack), và xử lý notification processors.

**Tương ứng TypeScript**:
- `plugin-notifications-backend` — Core notifications CRUD, processors, recipient resolving
- `plugin-notifications-backend-module-email` — Email delivery
- `plugin-notifications-backend-module-slack` — Slack delivery

## 2. Responsibilities

- **Notification CRUD**: Create, read, update, delete notifications
- **Recipient Resolution**: Resolve notification recipients (users, groups)
- **Notification Processing**: Process notifications qua configurable pipeline
- **Multi-channel Delivery**: In-app, email, Slack, webhook
- **Read/Unread Tracking**: Track notification read status per user
- **Notification Cleanup**: Scheduled cleanup of old notifications
- **Real-time Push**: Push new notifications via Signal Service

## 3. Cấu trúc dự án

```
notification-service/
├── cmd/server/main.go
├── internal/
│   ├── entity/
│   │   ├── notification.go          # Notification model
│   │   ├── recipient.go             # Recipient model
│   │   ├── channel.go               # Delivery channel
│   │   └── errors.go
│   │
│   ├── usecase/
│   │   ├── interfaces.go
│   │   ├── notification_usecase.go  # CRUD + send
│   │   ├── recipient_usecase.go     # Resolve recipients
│   │   ├── processor_usecase.go     # Process notifications
│   │   └── cleanup_usecase.go       # Scheduled cleanup
│   │
│   ├── adapter/
│   │   ├── handler/
│   │   │   ├── http/
│   │   │   │   ├── router.go
│   │   │   │   └── notification_handler.go
│   │   │   └── grpc/
│   │   │       ├── server.go
│   │   │       └── notification_handler.go
│   │   ├── repository/
│   │   │   └── postgres/
│   │   │       └── notification_repo.go
│   │   ├── processor/
│   │   │   ├── processor_interface.go
│   │   │   ├── email_processor.go
│   │   │   └── slack_processor.go
│   │   └── resolver/
│   │       └── catalog_resolver.go   # Resolve from catalog groups
│   │
│   └── infrastructure/
│       ├── config/config.go
│       ├── database/
│       │   ├── postgres.go
│       │   └── migrations/
│       │       ├── 000001_create_notifications.up.sql
│       │       └── 000002_create_read_status.up.sql
│       ├── server/
│       │   ├── http.go
│       │   └── grpc.go
│       └── client/
│           ├── catalog_client.go
│           └── signal_client.go      # Push real-time via signals
│
├── api/
│   ├── proto/notification.proto
│   └── openapi/openapi.yaml
├── config/config.yaml
├── Dockerfile
└── go.mod
```

## 4. Entity Models

```go
type Notification struct {
    ID          string                 `json:"id"`
    User        string                 `json:"user"`     // recipient user entity ref
    Origin      string                 `json:"origin"`   // sender/system
    Created     time.Time              `json:"created"`
    Updated     *time.Time             `json:"updated,omitempty"`
    Read        *time.Time             `json:"read,omitempty"`
    Saved       *time.Time             `json:"saved,omitempty"`
    Severity    NotificationSeverity   `json:"severity"` // low, normal, high, critical
    Title       string                 `json:"title"`
    Description string                 `json:"description,omitempty"`
    Topic       string                 `json:"topic,omitempty"`
    Link        string                 `json:"link,omitempty"`
    Scope       string                 `json:"scope,omitempty"`
    Payload     map[string]any         `json:"payload,omitempty"`
}

type NotificationSeverity string

const (
    SeverityLow      NotificationSeverity = "low"
    SeverityNormal   NotificationSeverity = "normal"
    SeverityHigh     NotificationSeverity = "high"
    SeverityCritical NotificationSeverity = "critical"
)

type CreateNotificationRequest struct {
    Recipients NotificationRecipients `json:"recipients"`
    Payload    NotificationPayload    `json:"payload"`
}

type NotificationRecipients struct {
    Type       string   `json:"type"`       // "entity", "broadcast"
    EntityRefs []string `json:"entityRef,omitempty"` // user/group entity refs
}

type NotificationPayload struct {
    Title       string `json:"title"`
    Description string `json:"description,omitempty"`
    Link        string `json:"link,omitempty"`
    Topic       string `json:"topic,omitempty"`
    Scope       string `json:"scope,omitempty"`
    Severity    NotificationSeverity `json:"severity"`
}
```

## 5. API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | List notifications for current user |
| `POST` | `/` | Create new notification |
| `GET` | `/count` | Get unread notification count |
| `POST` | `/:id/read` | Mark notification as read |
| `DELETE` | `/:id/read` | Mark notification as unread |
| `POST` | `/:id/save` | Save/bookmark notification |
| `DELETE` | `/:id/save` | Unsave notification |
| `PUT` | `/read` | Mark all as read |
| `GET` | `/health` | Health check |

## 6. Database Schema

```sql
CREATE TABLE notifications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_ref    VARCHAR(255) NOT NULL,
    origin      VARCHAR(255) NOT NULL DEFAULT 'system',
    severity    VARCHAR(20) NOT NULL DEFAULT 'normal',
    title       TEXT NOT NULL,
    description TEXT,
    topic       VARCHAR(255),
    link        TEXT,
    scope       VARCHAR(255),
    payload     JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ,
    read_at     TIMESTAMPTZ,
    saved_at    TIMESTAMPTZ
);

CREATE INDEX idx_notifications_user ON notifications(user_ref);
CREATE INDEX idx_notifications_created ON notifications(created_at DESC);
CREATE INDEX idx_notifications_read ON notifications(user_ref, read_at) WHERE read_at IS NULL;
CREATE INDEX idx_notifications_topic ON notifications(topic);
```

## 7. Configuration

```yaml
notifications:
  processors:
    email:
      enabled: false
      smtp:
        host: "smtp.example.com"
        port: 587
        username: "${SMTP_USER}"
        password: "${SMTP_PASSWORD}"
    slack:
      enabled: false
      webhook_url: "${SLACK_WEBHOOK_URL}"
  
  cleanup:
    enabled: true
    max_age: "90d"
    schedule: "0 2 * * *"   # Daily at 2 AM

database:
  host: "postgres-notification"
  port: 5432
  name: "backstage_notification"
```
