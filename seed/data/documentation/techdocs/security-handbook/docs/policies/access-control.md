# Access Control Policy

## Phạm vi áp dụng
Policy này áp dụng cho tất cả nhân viên, nhà thầu và hệ thống kỹ thuật.

## Nguyên tắc

### Principle of Least Privilege (PoLP)
Mọi user và service account chỉ được cấp quyền tối thiểu cần thiết để hoàn thành công việc.

### Separation of Duties
Không có cá nhân nào có quyền thực hiện đồng thời nhiều bước quan trọng trong một quy trình (ví dụ: cả approve và execute payment).

### Need to Know
Quyền truy cập dữ liệu chỉ được cấp cho những ai thực sự cần trong công việc hiện tại.

## Quản lý tài khoản

### Tạo tài khoản
- Tất cả tài khoản nhân viên được cấp qua Okta (SSO)
- Password policy: tối thiểu 12 ký tự, có chữ hoa/thường/số/ký tự đặc biệt
- **Bắt buộc MFA** cho mọi tài khoản

### Offboarding
Khi nhân viên nghỉ việc:
1. HR thông báo IT Security trong ngày làm việc cuối
2. Tài khoản Okta bị vô hiệu hóa ngay lập tức
3. Revoke tất cả sessions và tokens
4. Transfer ownership của resources (repositories, Cloud accounts)
5. Audit log access 30 ngày gần nhất

### Review định kỳ
- **Quarterly**: Review quyền truy cập của toàn bộ team
- **Semi-annual**: Review privileged accounts (admin, production access)

## Quyền truy cập Production

### Nguyên tắc
- Production access phải được approve bởi manager trực tiếp
- Chỉ cấp quyền trong thời gian cần thiết (just-in-time access)
- Mọi thao tác production phải được audit log

### Quy trình xin quyền Production

```
1. Tạo Jira ticket với lý do cụ thể
2. Manager approve
3. Security Team grant quyền tạm thời (4h mặc định, tối đa 24h)
4. Sau khi xong, quyền tự động bị revoke
5. Audit log được giữ 1 năm
```

### Công cụ: Teleport
Tất cả truy cập production SSH/Kubernetes đều qua **Teleport**:

```bash
# Login Teleport
tsh login --proxy=teleport.example.com

# List clusters
tsh kube ls

# Connect to production cluster
tsh kube login eks-prod-01
kubectl get pods -n app-team-a
```

## Service Accounts

### Kubernetes Service Accounts
- Mỗi service có Service Account riêng (không dùng `default`)
- RBAC: chỉ cấp quyền tối thiểu cần thiết
- Không mount Service Account token trừ khi cần

### AWS IAM Roles
- Sử dụng **IRSA** (IAM Roles for Service Accounts) thay vì long-lived credentials
- Không dùng Access Key/Secret Key cho workloads (chỉ cho CI/CD pipeline với rotation)
- Rotate credentials định kỳ 90 ngày
