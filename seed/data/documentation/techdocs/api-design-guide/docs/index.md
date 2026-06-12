# API Design Guide

Chào mừng đến với **API Design Guide** — tài liệu chuẩn thiết kế API của tổ chức.

## Tại sao cần API Design Guide?

API tốt là API mà developers muốn dùng. API xấu là API mà developers phải dùng. Chúng tôi hướng đến việc xây dựng APIs thuộc loại đầu tiên.

## Nguyên tắc API-First

Trước khi code, hãy **thiết kế API contract** (OpenAPI spec hoặc GraphQL schema hoặc Proto file) và review với:
- Frontend/mobile team sẽ consume API
- Backend team khác nếu có service-to-service communication
- API Guild (nếu là public API)

## Phân loại APIs

| Loại | Mô tả | Standard |
|---|---|---|
| **Public API** | Expose cho external developers | OpenAPI 3.x + API Gateway |
| **Partner API** | Expose cho đối tác cụ thể | OpenAPI 3.x + mTLS |
| **Internal API** | Service-to-service | gRPC (ưu tiên) hoặc REST |
| **GraphQL** | Frontend-driven queries | Schema-first + Apollo Federation |

## Chọn đúng protocol

```
Cần real-time bidirectional? → WebSocket / gRPC streaming
Cần performance cao giữa services? → gRPC
Cần flexible queries cho frontend? → GraphQL
Cần đơn giản và HTTP cacheable? → REST
```

## Quy trình thiết kế API mới

1. **Draft** OpenAPI/Proto spec → review với consumers
2. **Mock** API với Prism hoặc Apollo Studio
3. **Validate** spec với Spectral linter
4. **Implement** theo spec (spec là source of truth)
5. **Publish** spec lên Backstage API Catalog
6. **Monitor** với API analytics

## Versioning Strategy

- **REST**: URL path versioning (`/v1/`, `/v2/`)
- **GraphQL**: Schema evolution (avoid breaking changes)
- **gRPC**: Protobuf backward compatibility rules

Xem chi tiết từng loại API trong menu bên trái.
