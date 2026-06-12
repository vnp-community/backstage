# Engineering Principles

Đây là các nguyên tắc cốt lõi hướng dẫn mọi quyết định kỹ thuật trong tổ chức.

## 1. Keep it Simple

> "Complexity is the enemy of reliability."

Luôn ưu tiên giải pháp đơn giản nhất có thể. Complexity có chi phí ẩn: khó debug, khó onboard người mới, khó maintain.

**Áp dụng:**
- Chọn giải pháp đơn giản hơn khi không cần độ phức tạp
- Tách concerns rõ ràng — mỗi component làm một việc tốt
- Tránh over-engineering

## 2. You Ain't Gonna Need It (YAGNI)

Chỉ build những gì **thực sự cần ngay bây giờ**, không build cho tương lai giả định.

**Áp dụng:**
- Không thêm "tính năng có thể cần sau" khi chưa có requirement
- Không abstraction quá sớm
- Thiết kế có thể evolve được, không cần predict tương lai

## 3. Make it Work, Make it Right, Make it Fast

**Thứ tự ưu tiên:**
1. Make it work (correctness)
2. Make it right (clean, maintainable)
3. Make it fast (performance) — chỉ khi có evidence cần thiết

Đừng optimize prematurely. Profiling trước khi optimize.

## 4. Fail Fast and Loudly

Lỗi phải xuất hiện sớm và rõ ràng, không âm thầm fail.

```go
// ✅ Fail fast
func processOrder(order *Order) error {
    if order == nil {
        return errors.New("order cannot be nil") // Fail ngay
    }
    if order.Amount <= 0 {
        return fmt.Errorf("invalid amount: %d", order.Amount)
    }
    // ... process
}

// ❌ Silent failure
func processOrder(order *Order) {
    if order == nil {
        return // Âm thầm ignore
    }
    // ... process
}
```

## 5. Observability is not Optional

Mọi service phải có:
- **Metrics**: Prometheus-compatible `/metrics` endpoint
- **Logs**: JSON có cấu trúc với trace_id
- **Traces**: OpenTelemetry instrumentation
- **Health checks**: `/healthz` và `/readyz`

## 6. Security by Default

Bảo mật không phải là tính năng có thể thêm sau. Phải được tích hợp ngay từ đầu:
- Least privilege cho mọi component
- Validate và sanitize mọi input
- Encrypt sensitive data at rest và in transit

## 7. Embrace Change

Code tốt không phải là code "hoàn hảo ngay từ đầu" — mà là code có thể dễ dàng thay đổi khi requirements thay đổi.

- Viết code có tests để refactor an toàn
- Document những quyết định thiết kế quan trọng (Architecture Decision Records)
- Không sợ refactor code xấu

## 8. Automation over Manual

Nếu bạn làm thứ gì đó lần thứ 3, hãy automate nó.

- Automate testing
- Automate deployment
- Automate monitoring và alerting
- Automate toàn bộ quy trình repetitive

## 9. Shared Ownership

Code không thuộc sở hữu của một người. Toàn team có trách nhiệm với chất lượng codebase:
- Code review thực chất, không phải formality
- Bus factor: không có critical knowledge nằm ở một người
- Documentation là trách nhiệm của tất cả

## 10. Blameless Culture

Khi có sự cố, chúng tôi tìm hiểu **hệ thống đã fail như thế nào**, không phải **ai đã làm sai**.

Mọi incident là cơ hội học hỏi để cải thiện hệ thống.
