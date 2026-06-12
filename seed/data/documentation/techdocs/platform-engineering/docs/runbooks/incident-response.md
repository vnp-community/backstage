# Incident Response Runbook

## Mức độ ưu tiên

| Severity | Mô tả | Thời gian phản hồi | Kênh |
|---|---|---|---|
| **P1** | Production hoàn toàn down | 5 phút | PagerDuty + Slack War Room |
| **P2** | Feature chính bị ảnh hưởng | 15 phút | PagerDuty + Slack |
| **P3** | Degraded performance | 1 giờ | Slack |
| **P4** | Minor issue | Next business day | Jira ticket |

## Quy trình xử lý sự cố

### Bước 1: Acknowledge
Khi nhận alert PagerDuty, acknowledge ngay lập tức (trong 5 phút) để ngăn escalation.

### Bước 2: Triage
```
1. Xác định scope: "bao nhiêu user/service bị ảnh hưởng?"
2. Xác định impact: "revenue impact ước tính là bao nhiêu?"
3. Tạo war room: /incident create trong Slack
4. Notify stakeholders
```

### Bước 3: Điều tra (OODA Loop)
**Observe**: Thu thập thông tin từ dashboards, logs, traces
```bash
# Xem recent deployments
kubectl get events -n app-team-a --sort-by='.lastTimestamp' | tail -20

# Xem pod status
kubectl get pods -n app-team-a -l app=my-service

# Xem logs gần nhất
kubectl logs -n app-team-a -l app=my-service --tail=100 -f
```

**Orient**: Phân tích nguyên nhân có thể

**Decide**: Chọn action phù hợp

**Act**: Thực thi action

### Bước 4: Mitigate (không nhất thiết phải fix hoàn toàn)
Ưu tiên khôi phục service trước, điều tra root cause sau:
- Rollback deployment nếu cần
- Scale up nếu do traffic spike
- Circuit breaker nếu downstream dependency fail

### Bước 5: Resolve và Retrospective
Sau khi resolve, tạo **Post-Mortem document** trong vòng 48 giờ.

## Post-Mortem Template

```markdown
# Incident Post-Mortem: [Tiêu đề]

**Date**: YYYY-MM-DD
**Severity**: P1/P2/P3
**Duration**: X giờ Y phút
**Authored by**: [Tên]

## Timeline
- HH:MM — Mô tả sự kiện

## Root Cause
[Nguyên nhân gốc]

## Impact
- X users bị ảnh hưởng
- Y% requests fail trong Z phút

## Contributing Factors
- Factor 1
- Factor 2

## Action Items
| Action | Owner | Due Date |
|---|---|---|
| ... | ... | ... |

## Lessons Learned
[Bài học rút ra]
```

!!! note "Blameless Culture"
    Post-mortem phải là **blameless** — tập trung vào systemic issues, không quy lỗi cho cá nhân.
