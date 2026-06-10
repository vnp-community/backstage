# 07 — Kubernetes Service

## 1. Tổng quan

Kubernetes Service cung cấp integration với Kubernetes clusters — lấy resources, workloads, metrics cho các entities trong catalog, và proxy requests đến K8s API server.

**Tương ứng TypeScript**:
- `plugin-kubernetes-backend` — Cluster management, resource fetching, fan-out handler, proxy

## 2. Responsibilities

- **Cluster Management**: Discover và manage Kubernetes clusters
- **Resource Fetching**: Fetch pods, deployments, services, etc. cho entities
- **Service Location**: Map catalog entities → K8s resources
- **K8s API Proxy**: Proxy requests trực tiếp đến K8s API server
- **Auth Strategy**: Pluggable authentication strategies cho clusters
- **Fan-out Queries**: Query resources across multiple clusters

## 3. Cấu trúc dự án

```
kubernetes-service/
├── cmd/server/main.go
├── internal/
│   ├── entity/
│   │   ├── cluster.go               # Cluster config model
│   │   ├── resource.go              # K8s resource model
│   │   ├── workload.go              # Workload info
│   │   └── errors.go
│   │
│   ├── usecase/
│   │   ├── interfaces.go
│   │   ├── cluster_usecase.go       # Cluster management
│   │   ├── resource_usecase.go      # Fetch K8s resources for entity
│   │   ├── proxy_usecase.go         # K8s API proxy
│   │   └── fanout_usecase.go        # Multi-cluster fan-out
│   │
│   ├── adapter/
│   │   ├── handler/
│   │   │   ├── http/
│   │   │   │   ├── router.go
│   │   │   │   ├── resources_handler.go
│   │   │   │   ├── clusters_handler.go
│   │   │   │   └── proxy_handler.go
│   │   │   └── grpc/
│   │   │       ├── server.go
│   │   │       └── k8s_handler.go
│   │   ├── cluster_supplier/
│   │   │   ├── supplier_interface.go
│   │   │   ├── config_supplier.go    # From app config
│   │   │   ├── gke_supplier.go       # GKE auto-discovery
│   │   │   └── catalog_supplier.go   # From catalog entities
│   │   ├── service_locator/
│   │   │   ├── locator_interface.go
│   │   │   ├── multi_locator.go      # Multi-cluster locator
│   │   │   └── catalog_locator.go    # Catalog-based locator
│   │   ├── fetcher/
│   │   │   └── k8s_fetcher.go        # K8s API client wrapper
│   │   └── auth_strategy/
│   │       ├── strategy_interface.go
│   │       ├── service_account.go
│   │       ├── google.go             # GKE auth
│   │       ├── aws.go                # EKS auth
│   │       └── azure.go              # AKS auth
│   │
│   └── infrastructure/
│       ├── config/config.go
│       ├── server/
│       │   ├── http.go
│       │   └── grpc.go
│       └── client/
│           └── catalog_client.go
│
├── api/
│   ├── proto/kubernetes.proto
│   └── openapi/openapi.yaml
├── config/config.yaml
├── Dockerfile
└── go.mod
```

## 4. API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/resources/workloads/query` | Get workloads by entity |
| `POST` | `/resources/custom/query` | Get custom resources |
| `GET` | `/clusters` | List configured clusters |
| `POST` | `/proxy/:clusterName/**` | Proxy to K8s API |

## 5. Resource Types Fetched

```go
var DefaultResourceTypes = []string{
    "pods",
    "services",
    "deployments",
    "replicasets",
    "horizontalpodautoscalers",
    "ingresses",
    "statefulsets",
    "daemonsets",
    "jobs",
    "cronjobs",
    "configmaps",
}
```

## 6. Configuration

```yaml
kubernetes:
  service_locator_method: "multiTenant"
  
  cluster_locator_methods:
    - type: "config"
      clusters:
        - name: "production"
          url: "https://k8s.prod.example.com"
          auth_provider: "serviceAccount"
          service_account_token: "${K8S_PROD_TOKEN}"
          skip_tls_verify: false
          
        - name: "staging"
          url: "https://k8s.staging.example.com"
          auth_provider: "google"
    
    - type: "gke"
      project_id: "${GCP_PROJECT_ID}"
      region: "us-central1"
  
  custom_resources:
    - group: "argoproj.io"
      apiVersion: "v1alpha1"
      plural: "rollouts"
```
