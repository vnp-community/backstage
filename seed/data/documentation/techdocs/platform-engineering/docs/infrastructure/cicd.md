# CI/CD Pipeline

## Tổng quan

Chúng tôi sử dụng mô hình **GitOps** với:
- **CI (Continuous Integration)**: GitHub Actions
- **CD (Continuous Deployment)**: ArgoCD

## CI Pipeline với GitHub Actions

### Shared Workflows

Platform Team cung cấp các reusable workflows tại `.github/workflows/shared/`:

| Workflow | Mục đích |
|---|---|
| `ci-go.yml` | Build + test Go applications |
| `ci-typescript.yml` | Build + test TypeScript/Node apps |
| `ci-python.yml` | Build + test Python applications |
| `docker-build.yml` | Build và push Docker image |
| `security-scan.yml` | Trivy + Semgrep scanning |
| `deploy-helm.yml` | Deploy bằng Helm |

### Ví dụ sử dụng

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    uses: my-org/.github/.github/workflows/shared/ci-go.yml@main
    with:
      go-version: '1.21'

  docker:
    needs: test
    uses: my-org/.github/.github/workflows/shared/docker-build.yml@main
    with:
      image-name: my-service
    secrets: inherit

  security:
    uses: my-org/.github/.github/workflows/shared/security-scan.yml@main
    secrets: inherit
```

### Branch Protection Rules

Các nhánh `main` và `release/*` yêu cầu:
- ✅ CI tests phải pass
- ✅ Security scan phải pass
- ✅ Ít nhất 1 code review approval
- ✅ Branch phải up-to-date với base

## CD với ArgoCD

### ApplicationSet Pattern

Chúng tôi dùng **ApplicationSet** để quản lý deploy đa môi trường:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: my-service
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - env: dev
            cluster: eks-dev-01
            namespace: app-team-a
          - env: staging
            cluster: eks-staging-01
            namespace: app-team-a
          - env: prod
            cluster: eks-prod-01
            namespace: app-team-a
  template:
    metadata:
      name: '{{env}}-my-service'
    spec:
      project: team-a
      source:
        repoURL: https://github.com/my-org/my-service
        targetRevision: HEAD
        path: 'deploy/{{env}}'
      destination:
        server: 'https://{{cluster}}.example.com'
        namespace: '{{namespace}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

### Sync Strategy

| Môi trường | Auto Sync | Prune | Self-Heal |
|---|---|---|---|
| Dev | ✅ Yes | ✅ Yes | ✅ Yes |
| Staging | ✅ Yes | ✅ Yes | ✅ Yes |
| Production | ❌ Manual | ✅ Yes | ✅ Yes |

Production deploy yêu cầu manual approval trong ArgoCD UI.

## Rollback

### Rollback tự động (staging/dev)
ArgoCD tự rollback nếu health check fail sau khi sync.

### Rollback thủ công (production)
```bash
# Xem lịch sử deployment
argocd app history prod-my-service

# Rollback về revision cụ thể
argocd app rollback prod-my-service <revision-id>
```
