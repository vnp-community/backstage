# RESTful API Design Principles

## URL Design

### Dùng danh từ số nhiều cho resources

```
✅  GET    /api/v1/users
✅  GET    /api/v1/users/{userId}
✅  POST   /api/v1/users
✅  PUT    /api/v1/users/{userId}
✅  DELETE /api/v1/users/{userId}

❌  GET    /api/v1/getUser
❌  POST   /api/v1/createUser
❌  GET    /api/v1/user (số ít)
```

### Quan hệ giữa resources

```
GET /api/v1/users/{userId}/orders           # Lấy orders của user
GET /api/v1/users/{userId}/orders/{orderId} # Lấy 1 order cụ thể
POST /api/v1/users/{userId}/orders          # Tạo order cho user
```

### Query parameters

```
# Filtering
GET /api/v1/orders?status=pending&currency=VND

# Pagination
GET /api/v1/orders?page=2&limit=20

# Sorting
GET /api/v1/orders?sort=created_at&order=desc

# Field selection (sparse fieldset)
GET /api/v1/users?fields=id,name,email
```

## HTTP Methods

| Method | Idempotent | Safe | Sử dụng |
|---|---|---|---|
| GET | ✅ | ✅ | Lấy resource |
| POST | ❌ | ❌ | Tạo resource |
| PUT | ✅ | ❌ | Thay thế hoàn toàn |
| PATCH | ❌ | ❌ | Cập nhật một phần |
| DELETE | ✅ | ❌ | Xóa resource |
| HEAD | ✅ | ✅ | Như GET nhưng không có body |

## HTTP Status Codes

```
2xx — Success
  200 OK           — Request thành công (GET, PUT, PATCH)
  201 Created      — Resource được tạo (POST)
  204 No Content   — Thành công, không có response body (DELETE)
  206 Partial Content — Pagination khi trả về subset

4xx — Client Errors
  400 Bad Request  — Input không hợp lệ
  401 Unauthorized — Chưa xác thực
  403 Forbidden    — Đã xác thực nhưng không có quyền
  404 Not Found    — Resource không tồn tại
  409 Conflict     — Xung đột (ví dụ: email đã tồn tại)
  422 Unprocessable Entity — Validation errors
  429 Too Many Requests — Rate limit exceeded

5xx — Server Errors
  500 Internal Server Error — Lỗi không xác định
  502 Bad Gateway — Upstream service fail
  503 Service Unavailable — Service tạm thời không khả dụng
```

## Response Format

### Success Response

```json
{
  "data": {
    "id": "usr_123",
    "name": "Nguyễn Văn A",
    "email": "vana@example.com",
    "created_at": "2024-01-15T10:30:00Z"
  },
  "meta": {
    "request_id": "req_abc123"
  }
}
```

### Error Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input validation failed",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      },
      {
        "field": "phone",
        "message": "Phone number must be 10 digits"
      }
    ]
  },
  "meta": {
    "request_id": "req_abc123"
  }
}
```

### Paginated Response

```json
{
  "data": [...],
  "pagination": {
    "page": 2,
    "limit": 20,
    "total": 156,
    "total_pages": 8,
    "has_next": true,
    "has_prev": true
  },
  "meta": {
    "request_id": "req_abc123"
  }
}
```

## Naming Conventions

- **Fields**: `snake_case` (VD: `created_at`, `user_id`)
- **Timestamps**: ISO 8601 format (`2024-01-15T10:30:00Z`)
- **IDs**: String prefixed với entity type (`usr_123`, `ord_456`)
- **Booleans**: Dùng `is_`, `has_`, `can_` prefix (`is_active`, `has_profile`)
- **Currency**: Lưu dạng integer (cents/xu), kèm currency code

## Idempotency Keys

Với các operations quan trọng (payment, order creation), hỗ trợ idempotency key:

```
POST /api/v1/payments
Headers:
  Idempotency-Key: a1b2c3d4-e5f6-...

Body:
  { "amount": 100000, "currency": "VND" }
```

Nếu request trùng `Idempotency-Key`, trả về kết quả của request trước mà không xử lý lại.
