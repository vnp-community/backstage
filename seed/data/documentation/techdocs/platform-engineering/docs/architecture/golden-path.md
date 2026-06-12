# Golden Path Templates

Golden Path là tập hợp các template và công cụ được Platform Team xây dựng, kiểm thử và bảo trì để giúp Product Team tạo service mới một cách nhanh chóng và tuân thủ chuẩn kỹ thuật.

## Tại sao cần Golden Path?

Không có Golden Path, mỗi team có thể:
- Cấu hình CI/CD khác nhau, dẫn đến bảo trì phức tạp
- Bỏ qua security scanning
- Thiếu observability chuẩn
- Không có on-call runbook

Golden Path giải quyết điều này bằng cách **baked-in defaults** mà vẫn cho phép tùy chỉnh.

## Danh sách Templates

### Backend Service (Go / TypeScript / Java)

Template cho microservice đầy đủ tính năng, bao gồm:

- ✅ Dockerfile tối ưu (multi-stage build)
- ✅ GitHub Actions workflow (test, lint, build, push)
- ✅ Helm chart (với resource limits, HPA, PodDisruptionBudget)
- ✅ ArgoCD Application manifest
- ✅ Prometheus metrics endpoint (`/metrics`)
- ✅ Health check endpoints (`/healthz`, `/readyz`)
- ✅ Structured logging (JSON format)
- ✅ OpenTelemetry tracing
- ✅ Skeleton TechDocs

**Sử dụng:** Tìm template `backend-service` trong Backstage > Software Templates.

### Frontend App (React / Next.js)

Template cho ứng dụng frontend, bao gồm:

- ✅ Next.js với TypeScript
- ✅ ESLint + Prettier
- ✅ Storybook
- ✅ Playwright e2e tests
- ✅ Lighthouse CI
- ✅ CDN deployment (CloudFront)

### Data Pipeline (Python / Spark)

Template cho data pipeline, bao gồm:

- ✅ Airflow DAG skeleton
- ✅ Great Expectations data validation
- ✅ dbt model skeleton
- ✅ Data catalog registration

## Tuỳ chỉnh Golden Path

Nếu bạn cần thay đổi một phần trong template:

1. Trao đổi với Platform Team trong `#platform-engineering`
2. Nếu thay đổi có lợi cho nhiều team, sẽ được merge vào template chính
3. Nếu chỉ dùng cho một team, có thể fork template và tự bảo trì

!!! warning "Lưu ý"
    Việc fork template đồng nghĩa với việc team tự chịu trách nhiệm bảo trì security patches và cập nhật dependency.
