# Backstage Seed Scripts

Bộ Python scripts để triển khai dữ liệu test lên Backstage server thông qua REST API.

## Cấu trúc

```
seed/
├── data/                          # Dữ liệu nguồn (YAML entities)
│   ├── features.md                # Mô tả các feature groups
│   ├── service-catalog/           # Feature: Service Catalog
│   │   ├── catalog-service-management/
│   │   └── metadata-and-ownership/
│   ├── apis/                      # Feature: API Catalog
│   ├── documentation/             # Feature: TechDocs
│   └── ...                        # Các feature khác
│
└── scripts/                       # Scripts triển khai
    ├── README.md                  # File này
    ├── requirements.txt           # Python dependencies
    ├── .env.example               # Template cấu hình
    │
    ├── backstage_client.py        # Backstage API client (core)
    ├── config.py                  # Load .env và cấu hình
    │
    ├── seed_catalog.py            # Seed qua Location API (khuyến nghị)
    ├── seed_entities.py           # Seed theo feature groups
    ├── cleanup.py                 # Dọn dẹp catalog
    ├── verify.py                  # Kiểm tra và báo cáo
    └── run_all.py                 # Pipeline điều phối (main entry point)
```

## Cài đặt

```bash
cd seed/scripts

# Tạo virtual environment
python -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate    # Windows

# Cài dependencies
pip install -r requirements.txt

# Cấu hình .env
cp .env.example .env
# Chỉnh sửa .env với thông tin server
```

## Cấu hình `.env`

```bash
# Backstage server URL (từ deploy/dev/.env)
BACKSTAGE_BASE_URL=https://b14.openledger.vn

# Token xác thực (để trống nếu dangerouslyDisableDefaultAuthPolicy: true)
BACKSTAGE_TOKEN=

# Tùy chọn khác
MAX_RETRIES=3
REQUEST_DELAY=0.2
LOG_LEVEL=INFO
```

> **Lưu ý**: Khi `dangerouslyDisableDefaultAuthPolicy: true` trong `app-config.yaml`
> (cấu hình hiện tại của dev server), không cần token.

## Sử dụng

### 🚀 Chạy đầy đủ pipeline (khuyến nghị)

```bash
python run_all.py
```

Pipeline tự động: health-check → seed → chờ 10s → verify

### 🧪 Dry-run (kiểm tra trước)

```bash
python run_all.py --dry-run
```

### 📦 Seed theo từng feature

```bash
# Chỉ seed Service Catalog
python run_all.py --feature service-catalog

# Chỉ seed APIs
python run_all.py --feature apis

# Chỉ seed Documentation
python run_all.py --feature documentation
```

Các feature group (theo `features.md`):

| Feature Group | Mô tả |
|---|---|
| `service-catalog` | Catalog quản lý dịch vụ, Metadata & Ownership |
| `apis` | API Catalog, API Discovery |
| `documentation` | TechDocs, Versioned Docs |
| `software-templates` | Scaffolder, Golden Path |
| `ci-cd` | Pipeline Integration, Build & Deployment |
| `infrastructure` | Kubernetes Plugin, Cloud Integration |
| `monitoring` | Observability, Health Status |
| `architecture` | Dependency Visualization |
| `security` | Permission Framework, Authentication |
| `collaboration` | Team Ownership, Developer Portal |
| `extensibility` | Plugin Architecture, Custom Plugins |
| `governance` | Software Standards, Compliance Tracking |
| `developer-experience` | Self-Service Platform, Centralized View |
| `search` | Global Search |

### 📋 Liệt kê dữ liệu

```bash
python seed_catalog.py --list
```

### 🔍 Verify catalog

```bash
python verify.py
python verify.py --feature service-catalog
python verify.py --export report.json
```

### 📊 Xem trạng thái hiện tại

```bash
python seed_entities.py --status
```

### 🧹 Dọn dẹp

```bash
# Preview (không xóa)
python cleanup.py

# Xóa thật sự
python cleanup.py --confirm

# Chỉ xóa locations
python cleanup.py --locations-only --confirm

# Xóa một loại entity
python cleanup.py --kind Component --confirm
```

## Cách hoạt động

### Chiến lược seed

Scripts dùng **Backstage Catalog Location API** để đăng ký dữ liệu:

1. Đọc file YAML từ `seed/data/`
2. Gọi `POST /api/catalog/locations` với path đến file
3. Backstage tự động crawl và ingest entities từ file đó
4. Các entities xuất hiện trong catalog sau vài giây

Cách này **idempotent** — chạy lại không gây lỗi (locations đã tồn tại sẽ được bỏ qua).

### Thứ tự seed

Entities được seed theo thứ tự để đảm bảo relations hợp lệ:
1. Domain
2. Group, User
3. System
4. Resource
5. Component
6. API
7. Template

## Debug

```bash
# Tăng log level
LOG_LEVEL=DEBUG python run_all.py

# Kiểm tra kết nối
python run_all.py --health-only

# Seed một file cụ thể
python -c "
from backstage_client import BackstageClient, BackstageConfig
c = BackstageClient(BackstageConfig('https://b14.openledger.vn'))
print(c.health_check())
"
```

## API Reference

### `backstage_client.BackstageClient`

| Method | Mô tả |
|---|---|
| `health_check()` | Kiểm tra kết nối |
| `register_location(type, target)` | Đăng ký Location |
| `list_locations()` | Liệt kê locations |
| `list_entities(kind, namespace, limit)` | Lấy danh sách entities |
| `get_entity(kind, namespace, name)` | Lấy entity cụ thể |
| `refresh_entity(entity_ref)` | Trigger refresh |
| `delete_entity(uid)` | Xóa entity |
| `delete_location(id)` | Xóa location |
| `validate_entity(entity)` | Validate entity format |
| `get_facets(facets)` | Lấy aggregated facets |
