# Security Handbook

Chào mừng đến với **Security Handbook** — tài liệu bảo mật trung tâm của tổ chức.

!!! warning "Quan trọng"
    Tài liệu này áp dụng cho **toàn bộ** nhân viên và nhà thầu làm việc với hệ thống và dữ liệu của tổ chức.

## Triết lý bảo mật

Chúng tôi xây dựng bảo mật theo nguyên tắc **"Shift Left Security"** — đưa bảo mật vào sớm nhất có thể trong quy trình phát triển, thay vì chỉ kiểm tra ở cuối.

```
Design → Code → Build → Test → Release → Deploy → Monitor
  ↑         ↑      ↑       ↑        ↑         ↑         ↑
Security review integrated at every stage (DevSecOps)
```

## Nguyên tắc cốt lõi

### 1. Least Privilege
Mọi người, hệ thống và process chỉ có quyền tối thiểu cần thiết để hoàn thành nhiệm vụ.

### 2. Defense in Depth
Nhiều lớp bảo vệ — không có single point of failure về bảo mật.

### 3. Zero Trust
Không tin tưởng bất kỳ traffic nào mặc định, kể cả traffic nội bộ. Xác thực và authorize mọi request.

### 4. Security by Default
Cấu hình mặc định phải là cấu hình an toàn. Opt-out khỏi bảo mật không được phép.

## Tóm tắt Policies

| Policy | Áp dụng cho | Tài liệu |
|---|---|---|
| Access Control Policy | Tất cả nhân viên | [Chi tiết](policies/access-control.md) |
| Data Classification Policy | Tất cả nhân viên | [Chi tiết](policies/data-classification.md) |
| Secure Coding Standard | Engineers | [Chi tiết](secure-dev/owasp-top10.md) |
| Secrets Management | Engineers | [Chi tiết](secure-dev/secrets-management.md) |
| Incident Response Policy | Security + On-call | [Chi tiết](incident/process.md) |

## Báo cáo sự cố bảo mật

Nếu bạn phát hiện lỗ hổng bảo mật, **KHÔNG** tạo public issue. Hãy:

1. **Email**: security@example.com (PGP key: [0xABCD1234])
2. **Slack** (private): DM `@security-team`
3. **Trang Web**: https://security.example.com/report

Chúng tôi cam kết phản hồi trong **24 giờ** và giải quyết theo mức độ nghiêm trọng.
