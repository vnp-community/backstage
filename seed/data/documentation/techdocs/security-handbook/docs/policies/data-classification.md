# Data Classification Policy

## Mục đích

Chính sách phân loại dữ liệu giúp xác định mức độ bảo vệ phù hợp cho từng loại dữ liệu, đảm bảo tuân thủ pháp lý (GDPR, PDPA) và bảo vệ thông tin của khách hàng và tổ chức.

## Các cấp độ phân loại

### 🔴 Confidential (Bí mật)
Dữ liệu có mức độ nhạy cảm cao nhất. Nếu bị lộ sẽ gây tổn hại nghiêm trọng.

**Ví dụ:**
- Thông tin thẻ tín dụng (PAN, CVV)
- Mật khẩu và credentials
- Private keys, certificates
- Thông tin y tế (PHI)
- Dữ liệu cá nhân nhạy cảm (PDPA/GDPR Special Category)

**Yêu cầu:**
- Mã hóa AES-256 at rest và in transit
- Truy cập need-to-know basis, có audit log
- Không được lưu trong log
- Xóa sau khi hết thời hạn sử dụng

### 🟡 Internal (Nội bộ)
Dữ liệu dành cho nhân viên, không phổ biến ra ngoài nhưng không gây hại nghiêm trọng nếu lộ.

**Ví dụ:**
- Thông tin nhân viên
- Tài liệu nội bộ
- Source code
- Dữ liệu kinh doanh không nhạy cảm

**Yêu cầu:**
- Chỉ chia sẻ qua kênh được mã hóa
- Không chia sẻ với bên ngoài khi chưa được approve

### 🟢 Public (Công khai)
Dữ liệu có thể chia sẻ tự do với bên ngoài.

**Ví dụ:**
- Tài liệu marketing
- Thông cáo báo chí
- API public documentation
- Open source code

## Xử lý dữ liệu cá nhân (PDPA/GDPR)

### Nguyên tắc
- **Consent**: Thu thập dữ liệu phải có consent rõ ràng
- **Purpose Limitation**: Chỉ dùng dữ liệu cho mục đích đã khai báo
- **Data Minimization**: Chỉ thu thập dữ liệu thực sự cần thiết
- **Retention**: Xóa dữ liệu sau khi hết mục đích sử dụng

### Data Subject Rights
- **Quyền truy cập**: User có quyền xem dữ liệu của họ
- **Quyền xóa**: User có quyền yêu cầu xóa dữ liệu ("right to be forgotten")
- **Quyền chỉnh sửa**: User có quyền yêu cầu sửa dữ liệu sai

Mọi yêu cầu data subject rights phải được xử lý trong **30 ngày**.

## Data Retention Schedule

| Loại dữ liệu | Retention period |
|---|---|
| Transaction logs | 7 năm (yêu cầu pháp lý) |
| Application logs | 90 ngày |
| Security audit logs | 1 năm |
| User profile data | Trong thời gian account còn active + 30 ngày |
| Backup | 30 ngày |
