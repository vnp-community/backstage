# 10 — Signal Service

## 1. Tổng quan

Signal Service cung cấp real-time communication qua WebSocket — cho phép server push events đến connected clients (notifications, catalog changes, scaffolder task updates).

**Tương ứng TypeScript**:
- `plugin-signals-backend` — WebSocket server, event subscription, broadcast

## 2. Responsibilities

- **WebSocket Management**: Manage WebSocket connections per user
- **Event Subscription**: Clients subscribe to specific channels/topics
- **Event Broadcasting**: Broadcast events to subscribed clients
- **Connection Lifecycle**: Handle connect, disconnect, reconnect
- **User Mapping**: Map WebSocket connections → user entity refs
- **Cross-service Signaling**: Receive signals từ other services via Event Service

## 3. Cấu trúc dự án

```
signal-service/
├── cmd/server/main.go
├── internal/
│   ├── entity/
│   │   ├── signal.go                # Signal message model
│   │   ├── connection.go            # WebSocket connection model
│   │   ├── subscription.go          # Subscription model
│   │   └── errors.go
│   │
│   ├── usecase/
│   │   ├── interfaces.go
│   │   ├── signal_usecase.go        # Send/broadcast signals
│   │   ├── subscription_usecase.go  # Manage subscriptions
│   │   └── connection_usecase.go    # Connection lifecycle
│   │
│   ├── adapter/
│   │   ├── handler/
│   │   │   └── http/
│   │   │       ├── router.go
│   │   │       └── websocket_handler.go
│   │   └── hub/
│   │       └── signal_hub.go         # WebSocket hub (gorilla/websocket)
│   │
│   └── infrastructure/
│       ├── config/config.go
│       ├── server/http.go
│       └── client/
│           └── event_subscriber.go   # Subscribe to NATS events
│
├── api/openapi/openapi.yaml
├── config/config.yaml
├── Dockerfile
└── go.mod
```

## 4. Entity Models

```go
type Signal struct {
    Channel string         `json:"channel"`   // "notifications", "catalog", "scaffolder"
    Message json.RawMessage `json:"message"`
}

type SignalSubscription struct {
    Channel  string `json:"channel"`
    UserRef  string `json:"userRef"`
    ClientID string `json:"clientId"`
}
```

## 5. WebSocket Protocol

```json
// Client → Server: Subscribe
{ "action": "subscribe", "channel": "notifications" }

// Client → Server: Unsubscribe
{ "action": "unsubscribe", "channel": "notifications" }

// Server → Client: Signal
{ "channel": "notifications", "message": { ... } }

// Server → Client: Ping
{ "action": "ping" }

// Client → Server: Pong
{ "action": "pong" }
```

## 6. API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | WebSocket upgrade endpoint |
| `GET` | `/health` | Health check |

## 7. Hub Architecture

```go
type Hub struct {
    clients    map[string]*Client           // clientID → Client
    userIndex  map[string]map[string]bool   // userRef → set of clientIDs
    channels   map[string]map[string]bool   // channel → set of clientIDs
    register   chan *Client
    unregister chan *Client
    broadcast  chan *Signal
    mu         sync.RWMutex
}

func (h *Hub) Run(ctx context.Context) {
    for {
        select {
        case client := <-h.register:
            h.addClient(client)
        case client := <-h.unregister:
            h.removeClient(client)
        case signal := <-h.broadcast:
            h.broadcastToChannel(signal)
        case <-ctx.Done():
            return
        }
    }
}
```

## 8. Configuration

```yaml
signals:
  websocket:
    max_connections: 10000
    ping_interval: "30s"
    pong_timeout: "10s"
    write_timeout: "5s"
    read_buffer_size: 1024
    write_buffer_size: 1024
    max_message_size: 65536
  
  channels:
    - "notifications"
    - "catalog"
    - "scaffolder"

  nats:
    subscribe_subjects:
      - "backstage.signal.>"     # All signal events
```
