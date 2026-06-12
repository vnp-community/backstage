# Git Workflow

Chúng tôi sử dụng mô hình **GitHub Flow** — đơn giản, linh hoạt và phù hợp với CI/CD.

## Mô hình nhánh

```
main (protected) ─────────────────────────────────────────────────► production
                    │              │               │
                    ▼              ▼               ▼
               feature/xyz   fix/bug-123    feat/new-api
```

- **`main`**: Nhánh chính, luôn deployable. Protected — không push trực tiếp.
- **Feature branches**: Mọi thay đổi đều thông qua branch và PR.

## Quy trình làm việc

### 1. Tạo branch mới

```bash
# Luôn đảm bảo main đã được sync
git checkout main
git pull origin main

# Tạo branch mới
git checkout -b feat/add-payment-gateway
# hoặc
git checkout -b fix/order-total-calculation
# hoặc
git checkout -b docs/update-api-guide
```

### Quy tắc đặt tên branch

| Prefix | Dùng cho |
|---|---|
| `feat/` | Feature mới |
| `fix/` | Bug fix |
| `hotfix/` | Urgent production fix |
| `docs/` | Documentation chỉ |
| `refactor/` | Refactoring |
| `chore/` | Build system, tooling |
| `test/` | Tests thêm mới |

### 2. Commit theo chuẩn Conventional Commits

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Ví dụ:**

```bash
git commit -m "feat(payment): add VNPay gateway integration"
git commit -m "fix(order): correct total calculation with discount codes"
git commit -m "docs(api): update authentication endpoint documentation"
git commit -m "chore(deps): upgrade axios to 1.6.0"
```

**Types hợp lệ:**
- `feat`: Feature mới → MINOR version bump
- `fix`: Bug fix → PATCH version bump
- `docs`: Documentation only
- `refactor`: Refactor (không thay đổi behavior)
- `perf`: Performance improvement
- `test`: Thêm hoặc sửa tests
- `chore`: Tooling, CI changes
- `BREAKING CHANGE`: Breaking change → MAJOR version bump

### 3. Push và tạo Pull Request

```bash
git push -u origin feat/add-payment-gateway

# Tạo PR qua GitHub CLI
gh pr create --title "feat(payment): add VNPay gateway" \
  --body "Closes #123

## Mô tả
Thêm tích hợp VNPay payment gateway...

## Checklist
- [x] Tests added
- [x] Documentation updated
- [x] Staging tested"
```

### 4. Code Review

- PR cần ít nhất **1 approval** từ reviewer
- Author nên respond comments trong **1 ngày làm việc**
- Sau khi approved, **squash and merge** (tránh dirty history)

### 5. Merge và cleanup

```bash
# Sau khi PR merged, cleanup local branch
git checkout main
git pull origin main
git branch -d feat/add-payment-gateway
```

## Git Tips

### Undo changes

```bash
# Hoàn tác staged changes
git restore --staged <file>

# Hoàn tác uncommitted changes
git restore <file>

# Hoàn tác commit cuối (giữ changes)
git reset --soft HEAD~1

# Hoàn tác commit đã push (tạo commit mới)
git revert HEAD
```

### Stash

```bash
# Lưu tạm thay đổi
git stash push -m "WIP: adding payment logic"

# Xem danh sách stash
git stash list

# Lấy lại stash gần nhất
git stash pop
```

### Giải quyết conflict

```bash
# Khi có conflict sau merge/rebase
git status  # Xem files bị conflict

# Sau khi resolve thủ công
git add <resolved-files>
git rebase --continue  # nếu đang rebase
# hoặc
git merge --continue   # nếu đang merge
```
