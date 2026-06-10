# Hướng dẫn sử dụng Backstage dành cho Developer

| Thông tin | Chi tiết |
|-----------|----------|
| **Phiên bản** | 1.51.0 |
| **Cập nhật** | 03/06/2026 |
| **Đối tượng** | Software Developer, DevOps Engineer |

---

## 1. Giới thiệu

Backstage là **developer portal** tập trung của tổ chức — nơi bạn có thể:

- Tra cứu toàn bộ services, APIs, thư viện trong **Software Catalog**
- Tạo project mới chuẩn hóa từ **Software Templates**
- Đọc và viết tài liệu kỹ thuật qua **TechDocs**
- Xem sơ đồ kiến trúc hệ thống qua tích hợp **Structurizr**
- Tìm kiếm xuyên suốt toàn bộ portal

---

## 2. Truy cập Backstage

| Môi trường | URL |
|------------|-----|
| **Local** | http://localhost:7007 |
| **Production** | Xem biến `APP_BASE_URL` trong cấu hình deployment |

Đăng nhập bằng tài khoản tổ chức (hoặc **Guest** trong môi trường local/development).

---

## 3. Chạy môi trường local

### 3.1. Yêu cầu

- Docker và Docker Compose
- Biến môi trường đã được khai báo (xem `.env.example` hoặc mục 3.2)

### 3.2. Biến môi trường cần thiết

Tạo file `.env` trong thư mục `deploy/local/`:

```env
# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Structurizr (architecture docs)
STRUCTURIZR_URL=https://structurizr.com
STRUCTURIZR_WORKSPACE_ID=<your-workspace-id>
STRUCTURIZR_API_KEY=<your-api-key>
STRUCTURIZR_API_SECRET=<your-api-secret>
```

### 3.3. Khởi động bằng Makefile

```bash
cd deploy/local

# Lần đầu — build image từ source
make build

# Khởi động tất cả services
make up

# Xem logs
make logs

# Dừng
make down
```

Backstage sẽ sẵn sàng tại http://localhost:7007 sau khi PostgreSQL healthy.

---

## 4. Software Catalog

Catalog là nơi đăng ký và tra cứu toàn bộ phần mềm của tổ chức.

### 4.1. Các loại entity

| Kind | Mô tả |
|------|-------|
| `Component` | Microservice, thư viện, website, data pipeline |
| `API` | REST, GraphQL, gRPC, AsyncAPI endpoint |
| `System` | Nhóm các components liên quan |
| `Domain` | Nhóm các systems theo business domain |
| `Resource` | Database, queue, bucket, external service |
| `User` / `Group` | Thành viên và nhóm trong tổ chức |

### 4.2. Đăng ký component mới

1. Tạo file `catalog-info.yaml` ở gốc repository của service:

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: my-service
  description: Mô tả ngắn về service
  annotations:
    backstage.io/techdocs-ref: dir:.
  tags:
    - backend
    - java
spec:
  type: service
  lifecycle: production
  owner: team-platform
  system: my-system
```

2. Vào Backstage → **Catalog** → **Register Existing Component**
3. Nhập URL tới file `catalog-info.yaml` trên SCM (GitHub, GitLab…)
4. Backstage tự động import và hiển thị entity

### 4.3. Các trường quan trọng

| Trường | Bắt buộc | Mô tả |
|--------|----------|-------|
| `metadata.name` | ✅ | Tên unique của entity |
| `metadata.description` | | Mô tả ngắn |
| `metadata.annotations` | | Metadata bổ sung (TechDocs, CI/CD link…) |
| `spec.type` | ✅ | `service`, `library`, `website`, `pipeline` |
| `spec.lifecycle` | ✅ | `experimental`, `production`, `deprecated` |
| `spec.owner` | ✅ | `user:<name>` hoặc `group:<name>` |
| `spec.system` | | System mà component thuộc về |

---

## 5. Software Templates (Scaffolder)

Templates cho phép tạo project mới theo chuẩn của tổ chức chỉ trong vài bước.

### 5.1. Tạo project từ template

1. Vào **Create** (hoặc **Catalog** → **Create Component**)
2. Chọn template phù hợp (Backend Service, Frontend App, Library…)
3. Điền thông tin theo wizard (tên, owner, repository…)
4. Xem lại và bấm **Create**
5. Backstage tạo repository, cấu trúc thư mục, CI pipeline và tự động đăng ký vào Catalog

### 5.2. Xem tiến trình task

Sau khi tạo, bạn có thể theo dõi từng bước của scaffolding task trong **Task Activity** tab.

---

## 6. TechDocs

TechDocs cho phép viết tài liệu kỹ thuật dạng Markdown và đọc trực tiếp trong Backstage.

### 6.1. Cấu hình TechDocs cho component

Thêm annotation vào `catalog-info.yaml`:

```yaml
metadata:
  annotations:
    backstage.io/techdocs-ref: dir:.
```

Tạo file `mkdocs.yml` ở gốc repository:

```yaml
site_name: 'Tên Service'
docs_dir: docs
nav:
  - Overview: index.md
  - Architecture: architecture.md
  - API: api.md
  - Runbook: runbook.md
```

Tạo thư mục `docs/` với các file Markdown tương ứng.

### 6.2. Xem tài liệu

1. Vào entity trong Catalog
2. Chọn tab **Docs**
3. Tài liệu được render và có thể tìm kiếm full-text

### 6.3. Build TechDocs locally (tùy chọn)

```bash
npx @techdocs/cli serve
```

---

## 7. Kiến trúc hệ thống với Structurizr

Backstage tích hợp với Structurizr để hiển thị sơ đồ kiến trúc theo mô hình C4.

### 7.1. Truy cập workspace

Structurizr API được proxy qua Backstage tại:

```
/api/proxy/structurizr/api/workspace/<WORKSPACE_ID>
```

### 7.2. Xem sơ đồ kiến trúc

Nếu plugin Structurizr được cài đặt, sơ đồ C4 sẽ hiển thị trong tab **Architecture** của entity.

### 7.3. Cập nhật kiến trúc

Kiến trúc được định nghĩa bằng **Structurizr DSL** trong workspace. Liên hệ Platform Team để được cấp quyền chỉnh sửa workspace.

---

## 8. Tìm kiếm

Sử dụng thanh tìm kiếm ở đầu trang để tìm:

- **Entities**: services, APIs, systems, teams
- **TechDocs**: nội dung trong các file tài liệu
- **Templates**: template phù hợp với nhu cầu

Hỗ trợ lọc theo `kind`, `lifecycle`, `owner`, `tags`.

---

## 9. Quản lý ownership

Mỗi entity cần có `owner` rõ ràng. Bạn có thể:

- Xem danh sách component do team mình sở hữu: **Catalog** → lọc theo `owner`
- Xem component mình sở hữu: **Home** → **Your owned entities**
- Kiểm tra health và coverage của team qua trang **Group** entity

---

## 10. FAQ

**Q: Làm sao để cập nhật thông tin entity?**
Sửa file `catalog-info.yaml` trong repository — Backstage tự động đồng bộ theo lịch.

**Q: Entity của tôi không hiển thị sau khi đăng ký?**
Kiểm tra tab **Relations** và **Raw YAML** của entity. Xem logs backend để tìm lỗi import.

**Q: Làm sao để xóa entity khỏi Catalog?**
Vào entity → **⋮** (menu) → **Unregister entity**. Hoặc xóa Location tương ứng.

**Q: Tôi cần thêm annotation mới cho CI/CD pipeline?**
Xem danh sách [Well-known Annotations](https://backstage.io/docs/features/software-catalog/well-known-annotations) và thêm vào `metadata.annotations`.

**Q: Cần hỗ trợ thêm?**
Liên hệ **Platform Team** qua Slack hoặc tạo issue trong repository của Backstage instance.
