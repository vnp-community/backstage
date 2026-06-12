# Platform Engineering Guide

Chào mừng đến với **Platform Engineering Guide** — tài liệu trung tâm về nền tảng kỹ thuật nội bộ của tổ chức.

## Mục tiêu

Platform Engineering tập trung vào việc xây dựng và vận hành **Internal Developer Platform (IDP)** — một lớp tự phục vụ giúp các kỹ sư sản phẩm làm việc hiệu quả hơn, không cần phụ thuộc vào các thao tác thủ công từ đội vận hành.

## Triết lý

> "Platform Engineering is the discipline of designing and building toolchains and workflows that enable self-service capabilities for software engineering organizations."

Chúng tôi áp dụng mô hình **Golden Path** — cung cấp con đường được kiến nghị, được tự động hóa và được bảo trì tốt để triển khai dịch vụ, thay vì áp đặt các quy tắc cứng nhắc.

## Các thành phần chính

| Thành phần | Mô tả | Trạng thái |
|---|---|---|
| Developer Portal | Backstage — cổng thông tin trung tâm | ✅ Production |
| Service Catalog | Quản lý toàn bộ component, API, system | ✅ Production |
| Self-Service Templates | Scaffolding service mới qua Backstage | ✅ Production |
| CI/CD Platform | GitHub Actions + ArgoCD | ✅ Production |
| Observability Stack | Prometheus + Grafana + Loki + Tempo | ✅ Production |
| Secret Management | HashiCorp Vault | ✅ Production |
| Container Platform | Kubernetes (EKS) | ✅ Production |

## Liên hệ

Đội Platform Engineering: `#platform-engineering` trên Slack

Để yêu cầu tính năng mới hoặc báo cáo sự cố, hãy tạo ticket trong hệ thống JIRA của chúng tôi.
