# 14 — MCP Service

## 1. Tổng quan

MCP (Model Context Protocol) Service cung cấp MCP-compatible actions cho AI assistants — cho phép AI tools tương tác với Backstage resources (catalog entities, scaffolder templates, search, etc.).

**Tương ứng TypeScript**:
- `plugin-mcp-actions-backend` — MCP actions & tool definitions

## 2. Responsibilities

- **MCP Tool Registry**: Register và expose MCP-compatible tools
- **Tool Execution**: Execute MCP tool calls
- **Context Building**: Xây dựng context từ Backstage resources cho AI
- **Resource Access**: Cung cấp read access đến catalog, search, docs
- **Action Proxy**: Proxy MCP actions đến corresponding backend services

## 3. Cấu trúc dự án

```
mcp-service/
├── cmd/server/main.go
├── internal/
│   ├── entity/
│   │   ├── tool.go                  # MCP Tool definition
│   │   ├── resource.go              # MCP Resource definition
│   │   ├── prompt.go                # MCP Prompt definition
│   │   └── errors.go
│   │
│   ├── usecase/
│   │   ├── interfaces.go
│   │   ├── tool_usecase.go          # List & execute tools
│   │   ├── resource_usecase.go      # List & read resources
│   │   └── prompt_usecase.go        # List & get prompts
│   │
│   ├── adapter/
│   │   ├── handler/
│   │   │   ├── http/
│   │   │   │   ├── router.go
│   │   │   │   └── mcp_handler.go   # MCP SSE/Streamable HTTP transport
│   │   │   └── grpc/
│   │   │       ├── server.go
│   │   │       └── mcp_handler.go
│   │   └── tool/                    # Built-in MCP tools
│   │       ├── registry.go
│   │       ├── catalog_search.go    # Search catalog entities
│   │       ├── catalog_get.go       # Get entity details
│   │       ├── search_query.go      # Full-text search
│   │       ├── scaffolder_list.go   # List templates
│   │       ├── scaffolder_create.go # Create from template
│   │       └── techdocs_read.go     # Read documentation
│   │
│   └── infrastructure/
│       ├── config/config.go
│       ├── server/
│       │   ├── http.go
│       │   └── grpc.go
│       └── client/
│           ├── catalog_client.go
│           ├── search_client.go
│           ├── scaffolder_client.go
│           └── techdocs_client.go
│
├── api/
│   ├── proto/mcp.proto
│   └── openapi/openapi.yaml
├── config/config.yaml
├── Dockerfile
└── go.mod
```

## 4. Entity Models

```go
type MCPTool struct {
    Name        string          `json:"name"`
    Description string          `json:"description"`
    InputSchema json.RawMessage `json:"inputSchema"` // JSON Schema
}

type MCPToolCall struct {
    Name       string         `json:"name"`
    Arguments  map[string]any `json:"arguments"`
}

type MCPToolResult struct {
    Content []MCPContent `json:"content"`
    IsError bool         `json:"isError,omitempty"`
}

type MCPContent struct {
    Type string `json:"type"` // "text", "image", "resource"
    Text string `json:"text,omitempty"`
}

type MCPResource struct {
    URI         string `json:"uri"`
    Name        string `json:"name"`
    Description string `json:"description,omitempty"`
    MimeType    string `json:"mimeType,omitempty"`
}
```

## 5. Built-in MCP Tools

| Tool Name | Description | Arguments |
|---|---|---|
| `backstage_catalog_search` | Search entities in catalog | `query`, `kind`, `limit` |
| `backstage_catalog_get_entity` | Get entity details by ref | `entityRef` |
| `backstage_catalog_list_kinds` | List available entity kinds | — |
| `backstage_search` | Full-text search across Backstage | `query`, `types`, `limit` |
| `backstage_scaffolder_list_templates` | List available templates | `limit` |
| `backstage_scaffolder_create` | Execute a template | `templateRef`, `parameters` |
| `backstage_techdocs_read` | Read documentation page | `entityRef`, `path` |

## 6. API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/sse` | MCP SSE transport (Server-Sent Events) |
| `POST` | `/messages` | MCP Streamable HTTP transport |
| `GET` | `/health` | Health check |

## 7. MCP Protocol Flow

```
AI Client (Claude, Gemini, etc.)
    │
    │ MCP SSE/HTTP
    ▼
┌──────────────────┐
│  MCP Service     │
│                  │
│  1. Parse MCP    │
│     request      │
│  2. Route to     │
│     tool handler │
│  3. Call backend │
│     services     │
│  4. Format MCP   │
│     response     │
└──────────────────┘
    │ gRPC
    ├──→ Catalog Service
    ├──→ Search Service
    ├──→ Scaffolder Service
    └──→ TechDocs Service
```

## 8. Configuration

```yaml
mcp:
  enabled: true
  
  transport: "sse"     # "sse" or "streamable-http"
  
  server:
    name: "backstage-mcp"
    version: "1.0.0"
    
  tools:
    catalog_search:
      enabled: true
      max_results: 50
    catalog_get_entity:
      enabled: true
    search:
      enabled: true
      max_results: 20
    scaffolder_list_templates:
      enabled: true
    scaffolder_create:
      enabled: true
    techdocs_read:
      enabled: true
  
  auth:
    required: true
    allowed_clients: ["*"]   # or specific client IDs
```
