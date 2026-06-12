# Code Review Guidelines

Code review là một trong những hoạt động quan trọng nhất để duy trì chất lượng code và chia sẻ kiến thức trong team.

## Mục tiêu của Code Review

- Phát hiện bugs trước khi vào production
- Đảm bảo code dễ đọc và maintainable
- Chia sẻ kiến thức domain và kỹ thuật
- Đảm bảo tuân thủ coding standards
- Đưa ra góc nhìn thứ hai về thiết kế

## Trách nhiệm của Author

### Trước khi tạo PR
- Self-review code của chính mình trước
- Đảm bảo tests pass và coverage đủ
- PR có scope rõ ràng, không quá lớn (< 400 lines thay đổi lý tưởng)
- Viết PR description đầy đủ

### PR Description Template

```markdown
## Mô tả
[Mô tả ngắn gọn về thay đổi và lý do]

## Loại thay đổi
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation

## Cách test
[Mô tả cách reviewer có thể verify thay đổi]

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Staging tested (nếu applicable)

## Liên kết
- Closes #[issue number]
- Related to #[issue number]
```

### Responding to Reviews
- Respond mọi comment (kể cả chỉ là "Done" hoặc "Acknowledged")
- Giải thích khi không đồng ý, không chỉ revert
- Request re-review sau khi sửa

## Trách nhiệm của Reviewer

### Quy tắc chung
- Review trong **1 ngày làm việc** sau khi được assigned
- Tập trung vào logic và thiết kế, không phải style (đó là việc của linter)
- Phân biệt "blocking" vs "suggestion"

### Comment Format

```
# Blocking (phải fix trước khi merge)
🚨 [BLOCKING]: This will cause a race condition under concurrent load.
Please add a mutex here.

# Suggestion (không bắt buộc)
💡 [NIT]: Consider renaming `x` to `userCount` for clarity.

# Question (cần clarification)
❓ [QUESTION]: Is this expected to handle the case where `items` is empty?

# Praise (khuyến khích!)
✅ [PRAISE]: Nice refactoring, much cleaner than before!
```

### Những gì cần kiểm tra

**Correctness:**
- Logic có đúng không?
- Edge cases được handle không?
- Error handling đầy đủ không?

**Security:**
- Input validation
- Authentication/authorization
- Không expose sensitive data trong logs/responses

**Performance:**
- N+1 query problems
- Thiếu indexes
- Memory leaks

**Maintainability:**
- Code có dễ đọc không?
- Functions có quá dài không?
- Có code duplication không?

**Tests:**
- Tests có cover happy path và edge cases?
- Tests có thực sự test behavior hay chỉ test implementation?

## Approval Rules

| PR size | Reviews cần |
|---|---|
| < 50 lines | 1 approval |
| 50-400 lines | 1 approval |
| > 400 lines | 2 approvals |
| Breaking API changes | 2 approvals + API Guild review |
| Security-sensitive changes | Security Team review |

## Merge Strategy

Chúng tôi dùng **Squash and Merge** làm default:
- Git history sạch, 1 commit per PR
- Commit message = PR title (theo Conventional Commits)
- Chi tiết có trong PR description
