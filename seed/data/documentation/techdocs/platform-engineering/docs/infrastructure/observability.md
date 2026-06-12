# Observability Platform

## Tổng quan

Chúng tôi xây dựng observability stack theo mô hình **Three Pillars of Observability**:

| Pillar | Tool | Storage |
|---|---|---|
| Metrics | Prometheus + Thanos | S3 (90 ngày) |
| Logs | Loki + Promtail | S3 (30 ngày) |
| Traces | Tempo + OpenTelemetry | S3 (14 ngày) |

## Metrics (Prometheus)

### SLI/SLO Chuẩn

Chúng tôi đo lường 4 Golden Signals cho mọi service:

```promql
# Latency — P99 request duration
histogram_quantile(0.99,
  rate(http_request_duration_seconds_bucket{job="my-service"}[5m])
)

# Error Rate — % requests lỗi
rate(http_requests_total{job="my-service",status=~"5.."}[5m])
/ rate(http_requests_total{job="my-service"}[5m])

# Traffic — RPS
rate(http_requests_total{job="my-service"}[5m])

# Saturation — CPU usage %
container_cpu_usage_seconds_total{container="my-service"}
```

### SLO Targets

| Service Tier | Availability | Latency (P99) |
|---|---|---|
| Tier 1 (critical) | 99.95% | < 500ms |
| Tier 2 (standard) | 99.9% | < 1s |
| Tier 3 (best-effort) | 99.5% | < 5s |

## Logging (Loki)

### Log Format Chuẩn

Tất cả services phải xuất log dạng **JSON có cấu trúc**:

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "service": "my-service",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "message": "Request processed successfully",
  "duration_ms": 42,
  "user_id": "usr_123",
  "request_id": "req_abc123"
}
```

### Query Logs trong Grafana

```logql
# Xem logs của service trong 30 phút qua
{job="my-service"} | json | level="ERROR" | line_format "{{.message}}"

# Đếm lỗi theo loại
sum by (error_type) (
  count_over_time({job="my-service"} | json | level="ERROR" [5m])
)
```

## Tracing (Tempo + OpenTelemetry)

### Instrumentation

Sử dụng OpenTelemetry SDK cho tất cả services:

```go
// Go example
import "go.opentelemetry.io/otel"

func handleRequest(ctx context.Context, req *Request) {
    ctx, span := otel.Tracer("my-service").Start(ctx, "handleRequest")
    defer span.End()

    // ... business logic
    span.SetAttributes(
        attribute.String("user.id", req.UserID),
        attribute.Int("items.count", len(req.Items)),
    )
}
```

### Trace Sampling

| Môi trường | Sampling Rate |
|---|---|
| Development | 100% |
| Staging | 100% |
| Production | 10% (tail-based) |

## Alerting

### Alert Routing

```
Alert fired
    → Alertmanager
    → Route by severity & team label
        → critical: PagerDuty (immediate page)
        → warning: Slack #alerts-{team}
        → info: Slack #alerts-{team} (low priority)
```

### Alert Template

```yaml
# Ví dụ PrometheusRule
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: my-service-alerts
  labels:
    team: team-a
spec:
  groups:
    - name: my-service
      interval: 1m
      rules:
        - alert: HighErrorRate
          expr: |
            rate(http_requests_total{job="my-service",status=~"5.."}[5m])
            / rate(http_requests_total{job="my-service"}[5m]) > 0.05
          for: 5m
          labels:
            severity: critical
            team: team-a
          annotations:
            summary: "High error rate in my-service"
            description: "Error rate is {{ $value | humanizePercentage }}"
            runbook_url: "https://backstage.example.com/docs/my-service/runbooks/high-error-rate"
```

!!! tip "Runbook URL"
    Mỗi alert nên có `runbook_url` trỏ về TechDocs của service để on-call engineer biết cách xử lý.
