# Incident Response Process

## Mục tiêu

Đảm bảo mọi sự cố bảo mật được phát hiện, xử lý và ghi nhận một cách có hệ thống để:
- Giảm thiểu thiệt hại
- Học hỏi và cải thiện
- Tuân thủ nghĩa vụ pháp lý (báo cáo vi phạm dữ liệu trong 72h theo GDPR)

## Phân loại sự cố bảo mật

| Loại | Ví dụ | Mức độ |
|---|---|---|
| **Data Breach** | Dữ liệu khách hàng bị lộ | Critical |
| **Account Takeover** | Tài khoản admin bị compromise | Critical |
| **Ransomware** | Hệ thống bị mã hóa | Critical |
| **Phishing thành công** | Nhân viên cung cấp credentials | High |
| **Unauthorized Access** | Truy cập trái phép vào hệ thống | High |
| **Malware** | Phát hiện malware trong endpoint | Medium |
| **Vulnerability** | Lỗ hổng nghiêm trọng được báo cáo | Medium-High |

## Quy trình xử lý

### Phase 1: Preparation
- Duy trì danh sách liên hệ incident response team
- Test và update runbooks hàng quý
- Tabletop exercises 2 lần/năm

### Phase 2: Detection & Analysis

**Nguồn phát hiện:**
- SIEM alerts (Splunk)
- Security scanning tools
- Bug bounty reports
- Nhân viên báo cáo
- Third-party notification

**Phân tích ban đầu (trong 1h):**
```
1. Thu thập IOCs (Indicators of Compromise)
2. Xác định scope — "bao nhiêu hệ thống/users bị ảnh hưởng?"
3. Phân loại mức độ
4. Thông báo stakeholders theo mức độ
```

### Phase 3: Containment

**Short-term containment (trong 4h):**
- Isolate hệ thống bị ảnh hưởng
- Block malicious IPs/domains
- Revoke compromised credentials

**Long-term containment:**
- Patch vulnerability
- Rebuild systems từ clean backup

### Phase 4: Eradication

- Xóa malware, backdoors
- Patching tất cả affected systems
- Reset credentials của accounts liên quan

### Phase 5: Recovery

- Restore từ backup đã verified sạch
- Monitor closely trong 30 ngày

### Phase 6: Post-Incident

- **Blameless post-mortem** trong 5 ngày làm việc
- Root cause analysis
- Action items với deadline cụ thể

## Thông báo pháp lý

### GDPR/PDPA
Nếu có vi phạm dữ liệu cá nhân:
- **72 giờ**: Báo cáo cơ quan quản lý
- **Reasonable time**: Thông báo cho data subjects nếu có rủi ro cao

### Liên hệ khẩn cấp

| Vai trò | Liên hệ |
|---|---|
| CISO | ciso@example.com / +84-xxx-xxx-xxx |
| Legal | legal@example.com |
| PR/Comms | comms@example.com |
| Security Team 24/7 | security-oncall@example.com |
