# User Requirements Document (URD)

## Backstage — Open Source Developer Portal

| Thông tin | Chi tiết |
|-----------|----------|
| **Dự án** | Backstage |
| **Phiên bản** | 1.51.0 |
| **Ngày tạo tài liệu** | 27/05/2026 |

---

## 1. Giới thiệu

### 1.1. Mục đích tài liệu

Tài liệu này mô tả các yêu cầu từ phía người dùng (User Requirements) cho hệ thống Backstage Developer Portal. Tài liệu nhằm giúp đội phát triển hiểu rõ nhu cầu của từng nhóm người dùng và các kịch bản sử dụng (use cases) chính.

### 1.2. Phạm vi

Backstage là một framework mã nguồn mở để xây dựng Developer Portal, giúp tổ chức quản lý tập trung toàn bộ hạ tầng phần mềm, công cụ, dịch vụ và tài liệu kỹ thuật.

### 1.3. Đối tượng tài liệu

- Product Owner / Product Manager
- Đội phát triển (Development Team)
- Đội UX/UI Design
- Đội QA/Testing
- Stakeholders (Engineering Managers, VP of Engineering)

---

## 2. Nhóm người dùng (User Personas)

### 2.1. Software Developer (Nhà phát triển phần mềm)

| Thuộc tính | Mô tả |
|------------|-------|
| **Vai trò** | Phát triển và bảo trì các services, thư viện |
| **Mục tiêu** | Tìm kiếm nhanh thông tin về services, tạo project mới dễ dàng, truy cập tài liệu kỹ thuật |
| **Pain points** | Phải chuyển đổi giữa nhiều công cụ, khó tìm thông tin owner của service, tài liệu lỗi thời |
| **Tần suất sử dụng** | Hàng ngày |
| **Kỹ năng kỹ thuật** | Cao |

### 2.2. Platform Engineer (Kỹ sư nền tảng)

| Thuộc tính | Mô tả |
|------------|-------|
| **Vai trò** | Quản trị và mở rộng Backstage instance |
| **Mục tiêu** | Cấu hình plugins, tích hợp các hệ thống bên ngoài, tùy chỉnh developer portal |
| **Pain points** | Thiếu tài liệu plugin development, khó debug configuration issues |
| **Tần suất sử dụng** | Hàng ngày |
| **Kỹ năng kỹ thuật** | Rất cao |

### 2.3. Engineering Manager (Quản lý kỹ thuật)

| Thuộc tính | Mô tả |
|------------|-------|
| **Vai trò** | Quản lý đội phát triển, theo dõi tổng quan hệ thống |
| **Mục tiêu** | Xem tổng quan ownership, đánh giá tech health, theo dõi catalog coverage |
| **Pain points** | Thiếu visibility vào các services đội mình sở hữu |
| **Tần suất sử dụng** | Hàng tuần |
| **Kỹ năng kỹ thuật** | Trung bình - Cao |

### 2.4. DevOps / SRE Engineer

| Thuộc tính | Mô tả |
|------------|-------|
| **Vai trò** | Quản lý infrastructure, CI/CD, monitoring |
| **Mục tiêu** | Xem Kubernetes workloads, kiểm tra trạng thái deployment, quản lý infrastructure |
| **Pain points** | Phải chuyển giữa nhiều dashboards, thiếu liên kết service ↔ infrastructure |
| **Tần suất sử dụng** | Hàng ngày |
| **Kỹ năng kỹ thuật** | Cao |

### 2.5. Technical Writer (Biên tập viên kỹ thuật)

| Thuộc tính | Mô tả |
|------------|-------|
| **Vai trò** | Viết và bảo trì tài liệu kỹ thuật |
| **Mục tiêu** | Tạo, cập nhật tài liệu dễ dàng theo phương pháp docs-as-code |
| **Pain points** | Tài liệu rời rạc, khó tìm, không có chuẩn format |
| **Tần suất sử dụng** | Hàng tuần |
| **Kỹ năng kỹ thuật** | Trung bình |

### 2.6. New Hire (Nhân viên mới)

| Thuộc tính | Mô tả |
|------------|-------|
| **Vai trò** | Nhà phát triển mới gia nhập tổ chức |
| **Mục tiêu** | Nhanh chóng hiểu kiến trúc hệ thống, tìm owner liên hệ, bắt đầu contribute |
| **Pain points** | Không biết bắt đầu từ đâu, không biết ai owns service nào |
| **Tần suất sử dụng** | Hàng ngày (giai đoạn đầu) |
| **Kỹ năng kỹ thuật** | Đang phát triển |

---

## 3. Yêu cầu người dùng (User Requirements)

### 3.1. Quản lý Software Catalog

#### UR-CAT-001: Tra cứu thông tin Service/Component

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Developer, tôi muốn tìm kiếm và xem thông tin chi tiết về bất kỳ service/component nào trong tổ chức |
| **Tiêu chí chấp nhận** | - Tìm kiếm theo tên, loại, owner<br>- Xem thông tin metadata (mô tả, owner, lifecycle, links)<br>- Xem quan hệ với các entity khác<br>- Kết quả hiển thị trong < 2 giây |
| **Độ ưu tiên** | **Cao** |

#### UR-CAT-002: Đăng ký Component mới

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Developer, tôi muốn đăng ký service/component mới vào catalog |
| **Tiêu chí chấp nhận** | - Import từ URL hoặc file `catalog-info.yaml`<br>- Tự động tạo Pull Request nếu cần<br>- Validate YAML format trước khi import<br>- Hiển thị lỗi rõ ràng nếu format sai |
| **Độ ưu tiên** | **Cao** |

#### UR-CAT-003: Xem quan hệ giữa các Entity

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Developer hoặc Engineering Manager, tôi muốn xem đồ thị quan hệ (relationship graph) giữa các components, APIs, systems |
| **Tiêu chí chấp nhận** | - Hiển thị graph trực quan<br>- Có thể zoom in/out, drag nodes<br>- Hiển thị loại quan hệ (dependsOn, providesApi, consumesApi, ownedBy, etc.)<br>- Có thể click vào node để navigate đến entity detail |
| **Độ ưu tiên** | **Trung bình** |

#### UR-CAT-004: Lọc và Export Catalog

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Engineering Manager, tôi muốn lọc catalog theo nhiều tiêu chí và export kết quả |
| **Tiêu chí chấp nhận** | - Lọc theo kind, type, owner, lifecycle, tags<br>- Export dữ liệu đã lọc<br>- Hỗ trợ nhiều format export |
| **Độ ưu tiên** | **Trung bình** |

#### UR-CAT-005: Auto-discovery từ SCM

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Platform Engineer, tôi muốn catalog tự động phát hiện và import components từ các SCM providers |
| **Tiêu chí chấp nhận** | - Hỗ trợ GitHub, GitLab, Bitbucket Cloud/Server, Azure DevOps, Gerrit, Gitea<br>- Cấu hình schedule cho discovery<br>- Xử lý lỗi kết nối gracefully<br>- Logging chi tiết quá trình discovery |
| **Độ ưu tiên** | **Cao** |

---

### 3.2. Software Templates (Scaffolding)

#### UR-TPL-001: Tạo Project mới từ Template

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Developer, tôi muốn tạo project mới từ các template chuẩn hóa của tổ chức |
| **Tiêu chí chấp nhận** | - Hiển thị danh sách templates có sẵn<br>- Wizard step-by-step để nhập thông tin<br>- Preview kết quả trước khi tạo<br>- Tự động tạo repository, CI/CD pipeline, đăng ký vào catalog<br>- Hiển thị tiến trình và kết quả |
| **Độ ưu tiên** | **Cao** |

#### UR-TPL-002: Nhóm Templates theo danh mục

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Developer, tôi muốn xem templates được nhóm theo danh mục (Services, Documentation, etc.) để dễ tìm kiếm |
| **Tiêu chí chấp nhận** | - Templates được phân nhóm rõ ràng<br>- Có thể filter theo nhóm<br>- Mỗi template có mô tả và tags |
| **Độ ưu tiên** | **Trung bình** |

#### UR-TPL-003: Custom Template Actions

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Platform Engineer, tôi muốn tạo custom actions cho scaffolding pipeline để tích hợp với workflow nội bộ |
| **Tiêu chí chấp nhận** | - API rõ ràng để tạo custom actions<br>- Hỗ trợ nhiều SCM providers (GitHub, GitLab, Bitbucket, Azure, GCP)<br>- Có thể test action trong isolation<br>- Dry-run mode để validate trước khi thực thi |
| **Độ ưu tiên** | **Trung bình** |

---

### 3.3. TechDocs (Tài liệu kỹ thuật)

#### UR-DOC-001: Đọc tài liệu kỹ thuật tích hợp

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Developer, tôi muốn đọc tài liệu kỹ thuật của bất kỳ service nào ngay trong Backstage |
| **Tiêu chí chấp nhận** | - Tài liệu hiển thị trong entity page<br>- Hỗ trợ markdown rendering đầy đủ<br>- Navigation sidebar cho multi-page docs<br>- Tìm kiếm nội dung trong tài liệu |
| **Độ ưu tiên** | **Cao** |

#### UR-DOC-002: Viết tài liệu dạng docs-as-code

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Technical Writer hoặc Developer, tôi muốn viết tài liệu bằng Markdown và lưu trữ cùng source code |
| **Tiêu chí chấp nhận** | - Sử dụng MkDocs format<br>- Cấu hình qua `mkdocs.yml`<br>- Tự động build khi có thay đổi<br>- Hỗ trợ plugins MkDocs (diagrams, admonitions, etc.) |
| **Độ ưu tiên** | **Cao** |

#### UR-DOC-003: TechDocs trên Cloud Storage

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Platform Engineer, tôi muốn lưu trữ TechDocs artifacts trên cloud storage cho production |
| **Tiêu chí chấp nhận** | - Hỗ trợ Google GCS, AWS S3, Azure Blob Storage, OpenStack Swift<br>- CI/CD pipeline để build và publish docs<br>- Không phụ thuộc Docker cho build (option local) |
| **Độ ưu tiên** | **Trung bình** |

---

### 3.4. Tìm kiếm (Search)

#### UR-SRC-001: Tìm kiếm toàn cục

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Developer, tôi muốn tìm kiếm bất kỳ thông tin nào (services, docs, APIs) từ một thanh search duy nhất |
| **Tiêu chí chấp nhận** | - Thanh search bar ở trang chủ và navigation<br>- Kết quả bao gồm: Catalog entities, TechDocs content, APIs<br>- Auto-complete / suggestions<br>- Kết quả hiển thị trong < 1 giây<br>- Ranking kết quả theo relevance |
| **Độ ưu tiên** | **Cao** |

#### UR-SRC-002: Tìm kiếm nâng cao

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Developer, tôi muốn sử dụng bộ lọc nâng cao để thu hẹp kết quả tìm kiếm |
| **Tiêu chí chấp nhận** | - Filter theo loại (entities, docs, APIs)<br>- Filter theo owner, lifecycle, tags<br>- Faceted search results |
| **Độ ưu tiên** | **Trung bình** |

---

### 3.5. Authentication & Authorization

#### UR-AUTH-001: Đăng nhập SSO

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Developer, tôi muốn đăng nhập bằng tài khoản SSO của tổ chức (GitHub, Google, Okta, Azure AD, etc.) |
| **Tiêu chí chấp nhận** | - Hỗ trợ tối thiểu: GitHub, Google, Microsoft, Okta, OIDC, SAML<br>- One-click login<br>- Tự động tạo user profile trong Backstage<br>- Session management (timeout, refresh) |
| **Độ ưu tiên** | **Cao** |

#### UR-AUTH-002: Phân quyền truy cập

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Platform Engineer, tôi muốn cấu hình quyền truy cập cho từng plugin/feature |
| **Tiêu chí chấp nhận** | - Hệ thống permission policies<br>- Hỗ trợ role-based hoặc attribute-based access control<br>- Có thể disable/enable permissions globally<br>- Audit log cho các thao tác quan trọng |
| **Độ ưu tiên** | **Cao** |

#### UR-AUTH-003: Guest Access cho Development

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Developer, tôi muốn có thể truy cập Backstage ở môi trường development mà không cần SSO |
| **Tiêu chí chấp nhận** | - Guest provider chỉ hoạt động ở môi trường development<br>- Không yêu cầu cấu hình phức tạp<br>- Cảnh báo rõ ràng khi dùng guest mode |
| **Độ ưu tiên** | **Thấp** |

---

### 3.6. Kubernetes Integration

#### UR-K8S-001: Xem Kubernetes Workloads

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Developer hoặc DevOps, tôi muốn xem trạng thái Kubernetes workloads liên quan đến service của mình |
| **Tiêu chí chấp nhận** | - Hiển thị pods, deployments, services<br>- Trạng thái health/ready<br>- Resource usage (CPU, memory)<br>- Liên kết trực tiếp từ entity page |
| **Độ ưu tiên** | **Trung bình** |

---

### 3.7. Notifications

#### UR-NTF-001: Nhận thông báo

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Developer, tôi muốn nhận thông báo về các sự kiện liên quan (deployment, build failure, ownership changes) |
| **Tiêu chí chấp nhận** | - In-app notifications<br>- Email notifications (optional)<br>- Slack notifications (optional)<br>- Cấu hình notification preferences<br>- Badge count cho unread notifications |
| **Độ ưu tiên** | **Trung bình** |

---

### 3.8. Trang chủ & Personalization

#### UR-HOME-001: Trang chủ tùy chỉnh

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Developer, tôi muốn có trang chủ hiển thị thông tin cá nhân hóa (starred entities, recently visited, useful tools) |
| **Tiêu chí chấp nhận** | - Widget-based home page (drag & drop)<br>- Starred entities<br>- Recently/Top visited entities<br>- Thanh search bar<br>- World clock (multiple timezones)<br>- Company logo<br>- Quick access toolbar |
| **Độ ưu tiên** | **Trung bình** |

#### UR-HOME-002: User Settings

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Developer, tôi muốn tùy chỉnh các cài đặt cá nhân (theme, language, notifications) |
| **Tiêu chí chấp nhận** | - Light/Dark theme toggle<br>- Ngôn ngữ (i18n): en, es, fr, de, ja<br>- Notification preferences<br>- Persistent settings across sessions |
| **Độ ưu tiên** | **Thấp** |

---

### 3.9. API Documentation

#### UR-API-001: Xem API Documentation

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Developer, tôi muốn xem tài liệu API (OpenAPI, AsyncAPI, GraphQL, gRPC) của bất kỳ service nào |
| **Tiêu chí chấp nhận** | - Render OpenAPI/Swagger specs<br>- Render AsyncAPI specs<br>- Render GraphQL schemas<br>- Render gRPC/Protobuf definitions<br>- Hiển thị providing/consuming components<br>- Try-it-out functionality (optional) |
| **Độ ưu tiên** | **Cao** |

---

### 3.10. Platform Administration

#### UR-ADM-001: DevTools

| Thuộc tính | Mô tả |
|------------|-------|
| **Mô tả** | Là một Platform Engineer, tôi muốn có công cụ admin để debug và monitor Backstage instance |
| **Tiêu chí chấp nhận** | - Xem danh sách scheduled tasks<br>- Xem configuration hiện tại<br>- Xem trạng thái các plugins<br>- Xem unprocessed entities |
| **Độ ưu tiên** | **Trung bình** |

---

## 4. Yêu cầu về trải nghiệm người dùng (UX Requirements)

### 4.1. Accessibility

- Hỗ trợ screen readers (WCAG 2.1 AA)
- Keyboard navigation đầy đủ
- Sufficient color contrast
- Focus indicators rõ ràng

### 4.2. Responsive Design

- Desktop-first approach (primary use case)
- Tablet support (responsive layouts)
- Minimum supported resolution: 1080x768

### 4.3. Performance

- First Contentful Paint (FCP) < 2 giây
- Time to Interactive (TTI) < 5 giây
- Lighthouse performance score > 80

### 4.4. Internationalization (i18n)

- Hỗ trợ đa ngôn ngữ: English, Español, Français, Deutsch, 日本語
- Default language: English
- Configurable per-user language preference

### 4.5. Navigation

- Sidebar navigation với icons rõ ràng
- Breadcrumb cho entity pages
- Deep linking cho mọi page/entity
- Back/Forward browser navigation hoạt động đúng

---

## 5. Ràng buộc (Constraints)

### 5.1. Kỹ thuật

- Frontend phải tương thích với Chrome, Firefox, Safari phiên bản mới nhất
- Backend yêu cầu Node.js 22 hoặc 24
- Database: PostgreSQL 17+ (production), SQLite (development)
- Monorepo sử dụng Yarn 4 Berry

### 5.2. Tổ chức

- Open source project dưới CNCF governance
- Apache 2.0 License
- Community-driven development
- Contributor License Agreement (DCO)

### 5.3. Bảo mật

- Tuân thủ CNCF security best practices
- Security vulnerabilities qua HackerOne bug bounty
- Snyk vulnerability scanning
- No credentials in source code (environment variables)

---

## 6. Giả định (Assumptions)

1. Người dùng có quyền truy cập network đến Backstage instance
2. Tổ chức có ít nhất một SCM provider (GitHub, GitLab, etc.)
3. Người dùng có tài khoản SSO của tổ chức
4. Platform team có đủ năng lực để quản trị và customize Backstage
5. Hạ tầng hỗ trợ Docker/Kubernetes cho production deployment

---

## 7. Dependencies (Phụ thuộc)

| Dependency | Mô tả | Mức độ |
|------------|-------|--------|
| SCM Provider | GitHub, GitLab, etc. cho source code | Bắt buộc |
| Identity Provider | SSO provider cho authentication | Bắt buộc |
| PostgreSQL | Database cho production | Bắt buộc (production) |
| Redis | Caching layer | Tùy chọn |
| OpenSearch/Elasticsearch | Full-text search engine | Tùy chọn |
| Cloud Storage | GCS/S3/Azure cho TechDocs | Tùy chọn |
| Kubernetes | K8s cluster cho K8s plugin | Tùy chọn |
