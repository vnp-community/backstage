# 11 — Event Service

## 1. Tổng quan

Event Service là event bus trung tâm — nhận events từ external sources (GitHub webhooks, GitLab webhooks) và internal services, rồi publish đến subscribers qua NATS JetStream.

**Tương ứng TypeScript**:
- `plugin-events-backend` — Core event bus, HTTP event receiver
- `plugin-events-backend-module-github` — GitHub webhook events
- `plugin-events-backend-module-gitlab` — GitLab webhook events
- `plugin-events-backend-module-bitbucket-*` — Bitbucket events
- `plugin-events-backend-module-gerrit` — Gerrit events
- `plugin-events-backend-module-aws-sqs` — AWS SQS events
- `plugin-events-backend-module-google-pubsub` — Google PubSub events
- `plugin-events-backend-module-kafka` — Kafka events

## 2. Responsibilities

- **Event Ingestion**: Receive events từ external webhooks
- **Event Publishing**: Publish events đến NATS JetStream
- **Event Routing**: Route events đến correct topics/subjects
- **Webhook Validation**: Validate webhook signatures (GitHub, GitLab)
- **Multi-transport Support**: Adapter cho NATS, Kafka, Google PubSub, AWS SQS
- **Event Persistence**: Persist events cho replay/audit

## 3. Cấu trúc dự án

```
event-service/
├── cmd/server/main.go
├── internal/
│   ├── entity/
│   │   ├── event.go                 # Event model
│   │   ├── topic.go                 # Topic/subject model
│   │   ├── subscription.go          # Subscription model
│   │   └── errors.go
│   │
│   ├── usecase/
│   │   ├── interfaces.go
│   │   ├── publish_usecase.go       # Publish events
│   │   ├── subscribe_usecase.go     # Manage subscriptions
│   │   └── webhook_usecase.go       # Process webhooks
│   │
│   ├── adapter/
│   │   ├── handler/
│   │   │   ├── http/
│   │   │   │   ├── router.go
│   │   │   │   ├── webhook_handler.go    # Receive webhooks
│   │   │   │   └── publish_handler.go    # Internal publish endpoint
│   │   │   └── grpc/
│   │   │       ├── server.go
│   │   │       └── event_handler.go
│   │   ├── transport/
│   │   │   ├── transport_interface.go
│   │   │   ├── nats/
│   │   │   │   └── nats_transport.go     # NATS JetStream
│   │   │   ├── kafka/
│   │   │   │   └── kafka_transport.go
│   │   │   ├── google_pubsub/
│   │   │   │   └── pubsub_transport.go
│   │   │   └── aws_sqs/
│   │   │       └── sqs_transport.go
│   │   └── webhook_validator/
│   │       ├── validator_interface.go
│   │       ├── github_validator.go       # Validate GitHub signatures
│   │       ├── gitlab_validator.go       # Validate GitLab tokens
│   │       └── bitbucket_validator.go
│   │
│   └── infrastructure/
│       ├── config/config.go
│       ├── server/
│       │   ├── http.go
│       │   └── grpc.go
│       └── nats/
│           └── client.go                 # NATS JetStream client
│
├── api/
│   ├── proto/events.proto
│   └── openapi/openapi.yaml
├── config/config.yaml
├── Dockerfile
└── go.mod
```

## 4. Entity Models

```go
type Event struct {
    ID        string            `json:"id"`
    Topic     string            `json:"topic"`     // "github.push", "catalog.entity.created"
    Source    string            `json:"source"`    // "github", "catalog-service"
    Type      string            `json:"type"`      // event type
    Payload   json.RawMessage   `json:"payload"`
    Metadata  map[string]string `json:"metadata"`
    CreatedAt time.Time         `json:"createdAt"`
}

type Subscription struct {
    ID      string   `json:"id"`
    Topics  []string `json:"topics"`   // ["github.push", "github.pull_request"]
    Handler string   `json:"handler"`  // callback URL or NATS subject
}
```

## 5. API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/http/:topic` | Receive webhook event for topic |
| `POST` | `/publish` | Internal: publish event |
| `GET` | `/health` | Health check |

## 6. gRPC API

```protobuf
syntax = "proto3";
package backstage.events.v1;

service EventService {
    rpc Publish(PublishEventRequest) returns (google.protobuf.Empty);
    rpc Subscribe(SubscribeRequest) returns (stream Event);
}

message PublishEventRequest {
    string topic = 1;
    bytes payload = 2;
    map<string, string> metadata = 3;
}
```

## 7. Event Flow

```
External Webhook (GitHub/GitLab/etc.)
    │
    ▼
┌──────────────────┐
│ Webhook Handler  │  ← Validate signature
│ (HTTP POST)      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Event Service    │  ← Normalize event format
│ (Publish UC)     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ NATS JetStream   │  ← Persistent message queue
│ (Event Bus)      │
└────────┬─────────┘
         │
    ┌────┼────┬────────┐
    ▼    ▼    ▼        ▼
 Catalog  Search  Signal  Notification
 Service  Service Service  Service
```

## 8. Configuration

```yaml
events:
  transport: "nats"    # "nats", "kafka", "google-pubsub"
  
  nats:
    url: "nats://nats:4222"
    stream: "backstage-events"
    max_age: "72h"       # Event retention
    max_msgs: 1000000
  
  kafka:
    brokers: ["kafka:9092"]
    topic_prefix: "backstage."
  
  google_pubsub:
    project_id: "${GCP_PROJECT_ID}"
    topic_prefix: "backstage-"
  
  webhooks:
    github:
      secret: "${GITHUB_WEBHOOK_SECRET}"
    gitlab:
      token: "${GITLAB_WEBHOOK_TOKEN}"
    
  topics:
    - "github.push"
    - "github.pull_request"
    - "github.repository"
    - "gitlab.push"
    - "gitlab.merge_request"
    - "catalog.entity.created"
    - "catalog.entity.updated"
    - "catalog.entity.deleted"
    - "scaffolder.task.created"
    - "scaffolder.task.completed"
    - "notification.created"
```
