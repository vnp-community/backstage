# Internal Developer Platform (IDP)

## Định nghĩa

**Internal Developer Platform (IDP)** là tập hợp các công cụ, dịch vụ, và quy trình tự phục vụ mà Platform Team xây dựng và bảo trì để Product Engineers có thể làm việc độc lập mà không cần phụ thuộc vào Ops.

## Các lớp của IDP

### Layer 1: Developer Portal (Backstage)
Cổng thông tin trung tâm nơi engineer tìm thấy mọi thứ cần thiết:
- **Service Catalog**: Xem tất cả services, APIs, teams, resources
- **Software Templates**: Tạo service mới với Golden Path
- **TechDocs**: Tài liệu kỹ thuật tập trung
- **Search**: Tìm kiếm toàn bộ tổ chức

### Layer 2: Delivery Platform
- **Source Control**: GitHub (org: `my-org`)
- **CI**: GitHub Actions với shared workflows
- **CD**: ArgoCD (GitOps)
- **Registry**: GitHub Container Registry (ghcr.io)

### Layer 3: Runtime Platform
- **Compute**: Kubernetes (EKS) với Cluster Autoscaler
- **Networking**: AWS ALB Ingress + AWS VPC CNI
- **Storage**: AWS EBS (block), AWS EFS (shared), AWS S3 (object)
- **DNS**: Route 53 với External DNS

### Layer 4: Data & Observability
- **Metrics**: Prometheus + Thanos (long-term retention)
- **Dashboards**: Grafana (SSO-enabled)
- **Logs**: Loki + Promtail
- **Traces**: Tempo + OpenTelemetry
- **Alerts**: Alertmanager → PagerDuty → Slack

### Layer 5: Security
- **Secrets**: HashiCorp Vault (với Vault Agent Injector)
- **Policy**: OPA Gatekeeper
- **Scanning**: Trivy (containers), Semgrep (code), Dependabot
- **Identity**: Okta (SSO), Teleport (infra access)

## Team Topologies

Chúng tôi áp dụng mô hình [Team Topologies](https://teamtopologies.com/):

- **Platform Team**: Xây dựng và vận hành IDP
- **Stream-aligned Teams**: Product teams xây dựng features
- **Enabling Teams**: Chuyên gia hỗ trợ các stream-aligned teams
- **Complicated Subsystem Teams**: Xử lý domain phức tạp (ML, Data)
