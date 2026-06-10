COMPOSE = docker compose
IMAGE   = backstage-local:latest

.PHONY: help build up down restart logs ps clean rebuild

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  build     Build Docker image từ source"
	@echo "  up        Khởi động tất cả services"
	@echo "  down      Dừng và xóa containers"
	@echo "  restart   Restart Backstage service"
	@echo "  logs      Xem logs realtime (Ctrl+C để thoát)"
	@echo "  ps        Trạng thái các services"
	@echo "  clean     Xóa containers, volumes và image"
	@echo "  rebuild   Build lại image rồi khởi động"

build:
	@echo ">>> Building $(IMAGE) ..."
	docker build -t $(IMAGE) -f ../../Dockerfile ../../

up:
	$(COMPOSE) up -d
	@echo ">>> Backstage đang chạy tại http://localhost:7007"

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart backstage

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

clean:
	$(COMPOSE) down -v --remove-orphans
	docker rmi $(IMAGE) 2>/dev/null || true

rebuild: build up
