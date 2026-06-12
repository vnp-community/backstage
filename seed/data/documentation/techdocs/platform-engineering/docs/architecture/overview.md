# Tổng quan Kiến trúc

## Internal Developer Platform (IDP)

Platform của chúng tôi được xây dựng theo mô hình **Platform as a Product**, với Backstage là Developer Portal trung tâm kết nối toàn bộ hệ sinh thái.

```
┌──────────────────────────────────────────────────────────────┐
│                    Developer Portal (Backstage)               │
├──────────┬──────────┬──────────┬──────────┬──────────────────┤
│ Catalog  │Templates │ TechDocs │  Search  │   Plugins...     │
└──────────┴──────────┴──────────┴──────────┴──────────────────┘
           ↕                ↕                    ↕
┌──────────────────┐  ┌──────────────┐  ┌──────────────────────┐
│   GitHub Actions │  │    ArgoCD    │  │  Kubernetes (EKS)    │
│   (CI Pipeline)  │  │ (CD/GitOps)  │  │  - Dev / Staging     │
└──────────────────┘  └──────────────┘  │  - Production        │
                                         └──────────────────────┘
           ↕
┌──────────────────────────────────────────────────────────────┐
│                    Observability Stack                        │
│    Prometheus  │  Grafana  │  Loki  │  Tempo  │  Alertmanager│
└──────────────────────────────────────────────────────────────┘
```

## Nguyên tắc thiết kế

### 1. Self-Service First
Mọi tác vụ thông thường (tạo service mới, cấp quyền, deploy) đều phải có thể thực hiện tự động thông qua Portal mà không cần ticket thủ công.

### 2. GitOps
Toàn bộ trạng thái hạ tầng và ứng dụng được lưu trữ trong Git. Không có thao tác thủ công nào lên production.

### 3. Everything as Code
- Infrastructure as Code (Terraform)
- Configuration as Code (Helm/Kustomize)
- Policy as Code (OPA Gatekeeper)
- Documentation as Code (TechDocs)

### 4. Golden Path, Not Paved Road
Chúng tôi cung cấp con đường được kiến nghị với tooling tốt nhất, nhưng các team vẫn có thể chọn giải pháp khác nếu có lý do chính đáng.

## Môi trường

| Môi trường | Cluster | Mục đích |
|---|---|---|
| Development | `eks-dev-01` | Testing, feature development |
| Staging | `eks-staging-01` | Pre-production validation |
| Production | `eks-prod-01`, `eks-prod-02` | Production traffic (multi-AZ) |
