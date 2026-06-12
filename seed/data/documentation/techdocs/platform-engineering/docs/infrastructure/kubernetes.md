# Kubernetes Platform

## Tổng quan

Chúng tôi chạy Kubernetes trên **Amazon EKS** với cấu hình được quản lý bằng Terraform và Helm.

## Cluster Layout

```
eks-prod-01 (us-east-1)
├── System Node Group (m5.large × 3) — kube-system, monitoring, ingress
├── App Node Group (t3.xlarge × 5-20, auto-scaling) — workloads
└── GPU Node Group (g4dn.xlarge × 0-5, spot) — ML workloads
```

## Namespace Convention

| Namespace | Mục đích |
|---|---|
| `kube-system` | Core Kubernetes components |
| `monitoring` | Prometheus, Grafana, Alertmanager |
| `ingress-nginx` | Ingress controller |
| `argocd` | ArgoCD |
| `vault` | HashiCorp Vault |
| `cert-manager` | TLS certificate management |
| `app-{team-name}` | Workloads của từng team |

## Resource Limits

Mọi workload **bắt buộc** phải có resource requests và limits:

```yaml
resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
```

Workload không có resource limits sẽ bị chặn bởi OPA Gatekeeper.

## Horizontal Pod Autoscaler (HPA)

Tất cả production workloads nên có HPA:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-service
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

## Pod Disruption Budget

Để đảm bảo high availability trong quá trình upgrade:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: my-service
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: my-service
```

## Troubleshooting

### Pod ở trạng thái Pending
```bash
kubectl describe pod <pod-name> -n app-<team>
# Kiểm tra Events ở cuối output
```

Nguyên nhân thường gặp:
- Không đủ node resources → xem xét tăng node group
- PVC không được bind → kiểm tra StorageClass
- Image không pull được → kiểm tra ghcr.io credentials
