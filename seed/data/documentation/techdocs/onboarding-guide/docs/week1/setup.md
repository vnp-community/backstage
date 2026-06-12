# Cài đặt môi trường phát triển

## Yêu cầu hệ thống

- macOS 13+ hoặc Ubuntu 22.04+
- RAM: tối thiểu 16GB (khuyến nghị 32GB)
- Disk: tối thiểu 50GB còn trống

## Bước 1: Cài đặt Homebrew (macOS)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## Bước 2: Các công cụ cơ bản

```bash
# Git
brew install git gh

# Cấu hình Git
git config --global user.name "Tên của bạn"
git config --global user.email "ten@example.com"
git config --global core.editor "code --wait"
git config --global pull.rebase true

# Login GitHub CLI
gh auth login

# Docker
brew install --cask docker

# kubectl
brew install kubectl

# Thêm kubeconfig từ Platform Team
# Nhận file kubeconfig từ Platform Team qua Slack
mkdir -p ~/.kube
cp ~/Downloads/kubeconfig ~/.kube/config
kubectl get nodes  # Kiểm tra kết nối
```

## Bước 3: Language-specific tools

### Go

```bash
brew install go

# Thêm vào ~/.zshrc
export GOPATH=$HOME/go
export PATH=$PATH:$GOPATH/bin

# Kiểm tra
go version
```

### Node.js / TypeScript

```bash
# Cài fnm (Fast Node Manager)
brew install fnm
echo 'eval "$(fnm env --use-on-cd)"' >> ~/.zshrc

# Cài Node.js LTS
fnm install --lts
fnm use lts-latest

# Kiểm tra
node --version
npm --version
```

### Python

```bash
# Cài pyenv
brew install pyenv
echo 'eval "$(pyenv init -)"' >> ~/.zshrc

# Cài Python
pyenv install 3.11.7
pyenv global 3.11.7

# Kiểm tra
python --version
```

## Bước 4: IDE Setup

### VSCode (khuyến nghị)

```bash
brew install --cask visual-studio-code
```

Extensions được khuyến nghị (cài tự động từ `.vscode/extensions.json` trong project):

```json
{
  "recommendations": [
    "golang.go",
    "ms-python.python",
    "ms-vscode.vscode-typescript-next",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "ms-kubernetes-tools.vscode-kubernetes-tools",
    "redhat.vscode-yaml",
    "eamodio.gitlens"
  ]
}
```

## Bước 5: Pre-commit hooks

Chúng tôi dùng pre-commit để tự động kiểm tra code trước khi commit:

```bash
# Cài pre-commit
brew install pre-commit

# Trong mỗi repository
cd my-project
pre-commit install
```

Hooks thường bao gồm:
- Formatting (gofmt, prettier, black)
- Linting
- Secret detection (git-secrets)
- Trailing whitespace

## Bước 6: Truy cập Production (khi cần)

```bash
# Cài Teleport CLI
brew install teleport

# Login
tsh login --proxy=teleport.example.com --auth=okta

# Liệt kê clusters
tsh kube ls

# Connect đến cluster dev
tsh kube login eks-dev-01
```

## Kiểm tra setup hoàn chỉnh

Chạy script kiểm tra:

```bash
curl -sSL https://scripts.internal.example.com/check-setup.sh | bash
```

Script sẽ kiểm tra tất cả công cụ đã được cài đúng version.

!!! note "Gặp vấn đề?"
    Nếu bạn gặp lỗi trong quá trình setup, hãy hỏi trong channel `#platform-engineering` trên Slack.
    Đừng mất nhiều giờ để tự giải quyết một mình!
