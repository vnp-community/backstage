# API Versioning Strategy

## Vì sao cần versioning?

API là hợp đồng (contract) giữa provider và consumer. Khi cần thay đổi contract, versioning cho phép chúng ta:
- Không phá vỡ existing consumers
- Cho consumers thời gian migrate
- Deprecate old versions một cách có kiểm soát

## REST API Versioning

### Phương pháp: URL Path Versioning (ưu tiên)

```
GET /api/v1/users         ← Version 1
GET /api/v2/users         ← Version 2 (breaking changes)
```

**Lý do chọn URL path versioning:**
- Dễ debug và log
- Có thể test trực tiếp trên browser
- Cache-friendly
- Rõ ràng với API consumers

### Lifecycle của một API version

```
Draft → Beta → Stable → Deprecated → Sunset

Stable: SLA đầy đủ, backward compatible changes only
Deprecated: Thông báo 6 tháng trước khi sunset
Sunset: Không còn available
```

### Breaking vs Non-breaking Changes

**Non-breaking (có thể thêm trong version hiện tại):**
- Thêm optional request fields
- Thêm response fields mới
- Thêm new endpoints
- Thêm new optional query parameters

**Breaking (yêu cầu version mới):**
- Xóa fields hoặc endpoints
- Đổi tên fields
- Thay đổi data types
- Thay đổi required/optional status
- Thay đổi error codes

### Deprecation Process

```http
# Response headers khi API đã deprecated
HTTP/1.1 200 OK
Deprecation: true
Sunset: Sat, 01 Jun 2025 00:00:00 GMT
Link: <https://api.example.com/v2/users>; rel="successor-version"
```

## GraphQL Versioning

GraphQL không dùng versioning truyền thống. Thay vào đó:

### Schema Evolution

```graphql
# Thêm field mới — non-breaking
type User {
  id: ID!
  name: String!
  email: String!
  # Thêm field mới này không break existing queries
  phoneNumber: String  # nullable → non-breaking
}
```

### Deprecation trong Schema

```graphql
type User {
  id: ID!
  name: String!
  # Deprecated: use `emailAddress` instead
  email: String @deprecated(reason: "Use emailAddress")
  emailAddress: String!
}
```

## gRPC / Protobuf Versioning

Protobuf có backward/forward compatibility tốt nếu tuân thủ rules:

```protobuf
// ✅ An toàn: Thêm optional field mới
message User {
  int64 id = 1;
  string name = 2;
  string email = 3;
  // Thêm field số 4 trở đi — safe
  optional string phone = 4;
}

// ❌ KHÔNG bao giờ làm:
// - Đổi field number của existing field
// - Đổi data type của existing field
// - Xóa required field
```

## Deprecation Communication

Khi deprecate một API version:

1. **Email** tất cả known consumers (từ API analytics)
2. **Response header** deprecation warning
3. **Backstage**: Cập nhật API component với `lifecycle: deprecated`
4. **Slack** `#api-announcements`: Thông báo
5. **Dashboard**: Theo dõi usage để biết ai còn dùng
