# Deployment Runbook

## Deployment Checklist

Trước khi deploy production, hãy đảm bảo:

- [ ] All CI tests pass trên PR
- [ ] Security scan pass (no HIGH/CRITICAL vulnerabilities)
- [ ] Code review được approve bởi ít nhất 1 senior engineer
- [ ] Staging deployment đã được test
- [ ] Monitoring dashboard đã được chuẩn bị để quan sát
- [ ] Rollback plan đã được chuẩn bị

## Quy trình Deploy Production

### 1. Tạo deployment window
Deployment production tốt nhất trong giờ thấp điểm (9h-11h, 14h-16h giờ VN, ngày thường).

### 2. Sync ArgoCD

Mở ArgoCD UI → tìm application `prod-<service-name>` → click **Sync**.

Hoặc dùng CLI:
```bash
argocd app sync prod-my-service --timeout 300
```

### 3. Monitor deployment

Quan sát trong 10-15 phút sau khi deploy:

```bash
# Theo dõi pod rollout
kubectl rollout status deployment/my-service -n app-team-a -w

# Xem metric error rate trong Grafana
open https://grafana.example.com/d/my-service-dashboard
```

### 4. Smoke test

Chạy smoke test sau khi deploy:
```bash
curl -f https://api.example.com/healthz
curl -f https://api.example.com/api/v1/status
```

## Rollback

### Khi nào cần rollback?
- Error rate tăng đột biến (> 1% so với baseline)
- P99 latency tăng > 2x
- Critical business flow không hoạt động

### Cách rollback

**Option 1: ArgoCD Rollback (nhanh nhất)**
```bash
# Xem lịch sử
argocd app history prod-my-service

# Rollback về revision trước
argocd app rollback prod-my-service <previous-revision>
```

**Option 2: Git revert**
```bash
git revert HEAD
git push origin main
# ArgoCD sẽ tự động sync
```

**Option 3: Helm rollback**
```bash
helm rollback my-service --namespace app-team-a
```

## Deployment Freeze

Trong các giai đoạn sau, KHÔNG deploy production:
- **24h trước** ngày sale/campaign lớn
- **Thứ Sáu sau 16h** (trừ hotfix)
- **Ngày lễ quốc gia**
- **Trong thời gian incident đang xảy ra**

Xem lịch deployment freeze tại: `#platform-announcements` trên Slack.
