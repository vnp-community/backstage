# Hướng dẫn Import dữ liệu Test vào Backstage

Thư mục này chứa các file cấu trúc (mock data) mẫu để thử nghiệm tính năng **Service Catalog (Catalog quản lý dịch vụ)** của Backstage. Dữ liệu mẫu tuân theo chuẩn Backstage Software Catalog (C4 Model) bao gồm:

- `domain.yaml`: Định nghĩa Business Domain (e-commerce).
- `system.yaml`: Định nghĩa System chứa các components (payment-system).
- `microservice.yaml`: Component Backend (type: service).
- `api.yaml`: Định nghĩa API (OpenAPI).
- `website.yaml`: Component Frontend (type: website).
- `library.yaml`: Component thư viện dùng chung (type: library).
- `data-pipeline.yaml`: Resource Data Pipeline (type: data-pipeline).

## Cách 1: Đăng ký (Register) qua giao diện UI

1. Khởi động Backstage cục bộ (nếu chưa chạy): `yarn dev` hoặc `yarn start` ở thư mục root.
2. Truy cập vào trang Web Backstage (thường là `http://localhost:3000`).
3. Bấm vào menu **Create** ở sidebar bên trái.
4. Chọn nút **Register Existing Component**.
5. Đẩy thư mục code này lên một Git Repository (GitHub, GitLab, Bitbucket...).
6. Dán URL trỏ trực tiếp đến từng file YAML trên kho lưu trữ vào ô URL rồi bấm **Analyze**. 

*(Lưu ý: Bạn cũng có thể gộp tất cả file YAML lại thành một file duy nhất phân cách bằng `---` để chỉ cần đăng ký 1 lần).*

## Cách 2: Nạp tự động thông qua `app-config.yaml` (Dành cho Local Dev)

Cách tiện lợi nhất trên môi trường local là trỏ thẳng Backstage tới các file trên ổ cứng. Mở file `app-config.yaml` ở thư mục gốc của Backstage, tìm đến phần `catalog.locations` và thêm các mục định dạng `type: file` trỏ tới đường dẫn file này.

Ví dụ:

```yaml
catalog:
  locations:
    # Nạp toàn bộ dữ liệu mock của Service Catalog
    - type: file
      target: ../../data/service-catalog/catalog-quan-ly-dich-vu/domain.yaml
    - type: file
      target: ../../data/service-catalog/catalog-quan-ly-dich-vu/system.yaml
    - type: file
      target: ../../data/service-catalog/catalog-quan-ly-dich-vu/microservice.yaml
    - type: file
      target: ../../data/service-catalog/catalog-quan-ly-dich-vu/api.yaml
    - type: file
      target: ../../data/service-catalog/catalog-quan-ly-dich-vu/website.yaml
    - type: file
      target: ../../data/service-catalog/catalog-quan-ly-dich-vu/library.yaml
    - type: file
      target: ../../data/service-catalog/catalog-quan-ly-dich-vu/data-pipeline.yaml
```

*Đường dẫn `target` ở trên là tương đối tính từ thư mục chạy backend (ví dụ `/packages/backend`), bạn có thể đổi thành đường dẫn tuyệt đối (bắt đầu bằng `/Users/...`) nếu Backstage báo lỗi không tìm thấy file.*

Để Backstage được quyền đọc file hệ thống trên Local, hãy chắc chắn bạn đã cấu hình cho phép tại `app-config.yaml`:
```yaml
backend:
  reading:
    allow:
      - host: localhost
        paths:
          - /Users/binhnt/Lab/dev/backstage/data # Thêm quyền truy cập vào thư mục chứa data
```

Sau khi cấu hình xong, hãy khởi động lại App để dữ liệu được nạp vào Catalog tự động!
