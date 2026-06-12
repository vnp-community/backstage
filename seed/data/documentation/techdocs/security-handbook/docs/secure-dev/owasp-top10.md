# OWASP Top 10 — Secure Coding Guide

Tài liệu này hướng dẫn cách phòng chống **OWASP Top 10** vulnerabilities trong code của chúng tôi.

## A01: Broken Access Control

### Vấn đề
Logic phân quyền sai hoặc thiếu, cho phép user truy cập tài nguyên không được phép.

### Phòng chống

```typescript
// ❌ Sai — dùng client-supplied user ID mà không verify
async function getOrder(req: Request) {
  const order = await db.orders.findById(req.body.userId);
  return order;
}

// ✅ Đúng — luôn dùng authenticated user từ token
async function getOrder(req: AuthenticatedRequest) {
  const order = await db.orders.findOne({
    id: req.params.orderId,
    userId: req.user.id, // lấy từ JWT, không từ request body
  });
  if (!order) throw new ForbiddenError();
  return order;
}
```

## A02: Cryptographic Failures

### Vấn đề
Dữ liệu nhạy cảm không được mã hóa hoặc dùng thuật toán yếu.

### Quy tắc

| Trường hợp | Không dùng | Nên dùng |
|---|---|---|
| Hash password | MD5, SHA1, SHA256 | Argon2id, bcrypt (cost≥12) |
| Mã hóa dữ liệu | DES, 3DES, RC4 | AES-256-GCM |
| Giao thức | TLS 1.0, 1.1, SSLv3 | TLS 1.3 (hoặc tối thiểu TLS 1.2) |
| Random number | `Math.random()` | `crypto.randomBytes()` |

```go
// ✅ Hash password đúng cách với Argon2
import "golang.org/x/crypto/argon2"

func hashPassword(password string) string {
    salt := make([]byte, 16)
    rand.Read(salt)
    hash := argon2.IDKey([]byte(password), salt, 1, 64*1024, 4, 32)
    return base64.StdEncoding.EncodeToString(hash)
}
```

## A03: Injection

### Vấn đề
SQL Injection, Command Injection, LDAP Injection, v.v.

### Phòng chống — SQL Injection

```python
# ❌ Sai — string concatenation
query = f"SELECT * FROM users WHERE name = '{user_input}'"
cursor.execute(query)

# ✅ Đúng — parameterized query
cursor.execute("SELECT * FROM users WHERE name = %s", (user_input,))
```

```go
// ✅ Go — dùng GORM với parameterized query
db.Where("username = ? AND email = ?", username, email).First(&user)
```

### Phòng chống — Command Injection

```python
# ❌ Sai
import os
os.system(f"convert {user_input} output.pdf")

# ✅ Đúng — dùng subprocess với list arguments
import subprocess
subprocess.run(["convert", user_input, "output.pdf"],
               capture_output=True, check=True)
```

## A05: Security Misconfiguration

### Checklist Production

- [ ] Debug mode tắt
- [ ] Stack traces không hiển thị cho user
- [ ] Không có default credentials
- [ ] Tắt các features không dùng
- [ ] HTTP Security headers đầy đủ

```
Content-Security-Policy: default-src 'self'
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

## A07: Identification and Authentication Failures

### Quy tắc

- **Session token**: tối thiểu 128 bits entropy
- **Session timeout**: 30 phút idle, 8 giờ absolute
- **MFA**: bắt buộc cho admin accounts
- **Rate limiting**: login endpoint bị giới hạn 5 attempts/minute

```typescript
// ✅ Rate limiting với express-rate-limit
import rateLimit from 'express-rate-limit';

const loginLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 5,
  message: 'Too many login attempts',
  standardHeaders: true,
  legacyHeaders: false,
});

app.post('/auth/login', loginLimiter, authController.login);
```

## A09: Security Logging and Monitoring Failures

### Phải log những gì?

```json
// Mọi authentication event
{
  "event": "auth.login.success",
  "user_id": "usr_123",
  "ip": "1.2.3.4",
  "user_agent": "Mozilla/5.0...",
  "timestamp": "2024-01-15T10:30:00Z"
}

// Mọi authorization failure
{
  "event": "authz.denied",
  "user_id": "usr_123",
  "resource": "order:456",
  "action": "delete",
  "timestamp": "2024-01-15T10:31:00Z"
}
```

### Không được log

- Passwords (kể cả hash)
- Secrets và API keys
- Credit card numbers
- Session tokens

!!! tip "Công cụ kiểm tra"
    Dùng `semgrep` với ruleset `p/owasp-top-ten` để tự động phát hiện các vulnerabilities phổ biến trong code review.
