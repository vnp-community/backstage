# Secrets Management

!!! danger "Quy tắc tuyệt đối"
    **TUYỆT ĐỐI KHÔNG** commit bất kỳ secret nào vào Git repository:
    passwords, API keys, tokens, certificates, connection strings.

## Hệ thống quản lý secrets: HashiCorp Vault

Tổ chức sử dụng **HashiCorp Vault** làm hệ thống quản lý secrets trung tâm.

### Cấu trúc Vault

```
vault/
├── secret/          # KV secrets
│   ├── team-a/
│   │   ├── production/
│   │   └── staging/
│   └── team-b/
├── database/        # Dynamic database credentials
├── pki/             # Certificate management
└── aws/             # Dynamic AWS credentials
```

### Truy cập Vault

**Phương thức xác thực:**
- **Kubernetes Auth**: Workloads trong Kubernetes (ưu tiên)
- **OIDC Auth**: Developers (qua Okta SSO)
- **AppRole**: Legacy applications

### Sử dụng trong Kubernetes

**Option 1: Vault Agent Sidecar (khuyến nghị)**

```yaml
# Annotate pod để inject secrets
apiVersion: v1
kind: Pod
metadata:
  annotations:
    vault.hashicorp.com/agent-inject: "true"
    vault.hashicorp.com/agent-inject-secret-config: "secret/team-a/production/my-service"
    vault.hashicorp.com/role: "my-service"
spec:
  serviceAccountName: my-service
  containers:
    - name: my-service
      image: my-service:latest
      env:
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: vault-injected
              key: db_password
```

**Option 2: External Secrets Operator**

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: my-service-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    kind: ClusterSecretStore
    name: vault-backend
  target:
    name: my-service-secrets
  data:
    - secretKey: db-password
      remoteRef:
        key: secret/team-a/production/my-service
        property: db_password
```

## Trong CI/CD (GitHub Actions)

**KHÔNG** dùng GitHub Secrets trực tiếp cho production secrets. Thay vào đó:

```yaml
jobs:
  deploy:
    steps:
      - name: Import secrets from Vault
        uses: hashicorp/vault-action@v2
        with:
          url: https://vault.example.com
          method: jwt
          role: github-actions-my-service
          secrets: |
            secret/team-a/production/my-service db_password | DB_PASSWORD ;
            secret/team-a/production/my-service api_key | API_KEY ;
```

## Secret Rotation

| Loại secret | Rotation frequency |
|---|---|
| Database credentials | 90 ngày (auto-rotation via Vault dynamic secrets) |
| API Keys (3rd party) | 180 ngày |
| TLS certificates | 90 ngày (auto via cert-manager) |
| SSH keys | 1 năm |
| AWS IAM keys (legacy) | 90 ngày |

## Pre-commit Hook

Cài **git-secrets** để tự động phát hiện secrets trước khi commit:

```bash
# Cài đặt
brew install git-secrets
git secrets --install
git secrets --register-aws

# Kiểm tra repo hiện tại
git secrets --scan
```

## Nếu đã commit secret lên Git

1. **Revoke ngay lập tức** secret đó (đổi password, rotate key)
2. Thông báo ngay cho Security Team qua Slack `#security-incidents`
3. Xóa secret khỏi Git history (dùng `git filter-repo`)
4. Force push (cần approval từ repo admin)
5. Notify tất cả collaborators để re-clone

!!! caution "Lưu ý quan trọng"
    Xóa khỏi Git history không có nghĩa là secret đã không bị lộ. Nếu repo là public, hãy assume secret đã bị compromise và revoke ngay.
