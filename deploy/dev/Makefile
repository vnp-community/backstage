COMPOSE   = docker compose
SERVER    = 172.20.2.41
GATEWAY   = 172.20.2.16
SSH_USER  = ubuntu
REMOTE    = $(SSH_USER)@$(SERVER)
GW_REMOTE = $(SSH_USER)@$(GATEWAY)

DEPLOY_DIR  = ~/backstage
GATEWAY_DIR = /home/ubuntu/vnp-qa-platform/proxy

.PHONY: help up down restart logs logs-backstage ps status check-ports \
        push-image deploy sync-config \
        ssl-init ssl-upgrade gateway-reload gateway-status \
        shell-backstage shell-postgres setup-server

help:
	@echo "Backstage Deploy — b14.openledger.vn"
	@echo "  App server : $(SERVER)"
	@echo "  Gateway    : $(GATEWAY) (nginx proxy + certbot)"
	@echo ""
	@echo "  App server (172.20.2.41):"
	@echo "    make up              Khoi dong tat ca containers"
	@echo "    make down            Dung tat ca containers"
	@echo "    make restart         Restart container bs-app"
	@echo "    make logs            Xem logs tat ca services"
	@echo "    make logs-backstage  Xem logs chi backstage"
	@echo "    make ps              Trang thai containers"
	@echo "    make status          Trang thai + port chi tiet"
	@echo "    make push-image      Build + chuyen image len server"
	@echo "    make sync-config     Dong bo config files len server"
	@echo "    make deploy          sync-config + start"
	@echo ""
	@echo "  Gateway nginx (172.20.2.16) — thu tu lan dau:"
	@echo "    make ssl-init        Buoc 1: Deploy HTTP config + cap SSL cert"
	@echo "    make ssl-upgrade     Buoc 2: Upgrade len HTTPS config + reload"
	@echo "    make gateway-reload  Reload nginx tren gateway"
	@echo "    make gateway-status  Kiem tra nginx + cert tren gateway"
	@echo ""
	@echo "  Debug:"
	@echo "    make shell-backstage  Shell vao container bs-app"
	@echo "    make shell-postgres   psql vao container bs-postgres"
	@echo "    make setup-server     Tao thu muc deploy tren server"

# ---------------------------------------------------------------
# App server containers (172.20.2.41)
# ---------------------------------------------------------------
up:
	ssh $(REMOTE) "cd $(DEPLOY_DIR) && $(COMPOSE) up -d"
	@echo ">>> Backstage (internal): http://$(SERVER):7007"
	@echo ">>> Backstage (public)  : https://b14.openledger.vn"
	@echo ">>> Structurizr (admin) : http://$(SERVER):8080"

down:
	ssh $(REMOTE) "cd $(DEPLOY_DIR) && $(COMPOSE) down"

restart:
	ssh $(REMOTE) "cd $(DEPLOY_DIR) && $(COMPOSE) restart backstage"

logs:
	ssh $(REMOTE) "cd $(DEPLOY_DIR) && $(COMPOSE) logs -f"

logs-backstage:
	ssh $(REMOTE) "cd $(DEPLOY_DIR) && $(COMPOSE) logs -f backstage"

ps:
	ssh $(REMOTE) "cd $(DEPLOY_DIR) && $(COMPOSE) ps"

status:
	@echo "=== Backstage containers ($(SERVER)) ==="
	ssh $(REMOTE) "cd $(DEPLOY_DIR) && $(COMPOSE) ps 2>/dev/null || echo '(chua chay)'"
	@echo ""
	@echo "=== Port 7007 / 8080 tren $(SERVER) ==="
	ssh $(REMOTE) "ss -tlnp | grep -E ':7007|:8080' || echo '(trong)'"
	@echo ""
	@echo "=== Gateway nginx ($(GATEWAY)) ==="
	ssh $(GW_REMOTE) "docker exec ms-nginx-proxy nginx -t 2>&1 | tail -3"

check-ports:
	@echo ">>> Kiem tra port 7007, 8080 tren $(SERVER)..."
	@ssh $(REMOTE) "ss -tlnp | grep -E ':7007|:8080' && echo 'CANH BAO: Port da bi chiem!' || echo 'OK: Port trong.'"

# ---------------------------------------------------------------
# Build + transfer image
# ---------------------------------------------------------------
push-image:
	@echo ">>> Build image backstage:latest..."
	docker build -t backstage:latest -f ../../packages/backend/Dockerfile ../../
	@echo ">>> Pipe image len $(SERVER)..."
	docker save backstage:latest | ssh $(REMOTE) "docker load"
	@echo ">>> Done. Chay 'make restart' de ap dung image moi."

# ---------------------------------------------------------------
# Sync config files to app server
# ---------------------------------------------------------------
sync-config:
	ssh $(REMOTE) "mkdir -p $(DEPLOY_DIR)"
	scp docker-compose.yml          $(REMOTE):$(DEPLOY_DIR)/
	scp app-config.yaml             $(REMOTE):$(DEPLOY_DIR)/
	scp app-config.production.yaml  $(REMOTE):$(DEPLOY_DIR)/
	@echo ">>> Config da sync len $(SERVER):$(DEPLOY_DIR)"
	@echo ">>> QUAN TRONG: .env khong tu dong sync — copy thu cong neu thay doi:"
	@echo "    scp .env $(REMOTE):$(DEPLOY_DIR)/.env"

deploy: sync-config
	ssh $(REMOTE) "cd $(DEPLOY_DIR) && $(COMPOSE) up -d --no-build"
	@echo ">>> Deploy hoan thanh."

# ---------------------------------------------------------------
# Gateway nginx (172.20.2.16) — SSL termination
#
# Quy trinh lan dau:
#   1. make ssl-init     → deploy HTTP-only config + chay certbot
#   2. make ssl-upgrade  → thay bang HTTPS config + reload
# ---------------------------------------------------------------

# Bước 1: Deploy HTTP-only config cho ACME challenge, sau đó chạy certbot
# Dùng `docker exec ms-certbot` thay vì `docker compose run` để tránh bị treo TTY qua SSH
ssl-init:
	@echo ">>> [1/3] Upload HTTP-only config (de certbot ACME challenge hoat dong)..."
	scp nginx/b14-openledger-init.conf \
	    $(GW_REMOTE):$(GATEWAY_DIR)/conf.d/b14-openledger.conf
	@echo ">>> [2/3] Reload nginx de phuc vu ACME challenge..."
	ssh $(GW_REMOTE) "docker compose -f $(GATEWAY_DIR)/docker-compose.yml exec -T nginx nginx -t 2>&1 | tail -2 && \
	  docker compose -f $(GATEWAY_DIR)/docker-compose.yml exec -T nginx nginx -s reload"
	@echo ">>> [3/3] Chay certbot xin cert cho b14.openledger.vn..."
	@echo ">>> Yeu cau: DNS b14.openledger.vn → 103.67.184.32 da active"
	ssh $(GW_REMOTE) "docker exec ms-certbot certbot certonly \
	    --webroot --webroot-path /var/www/certbot \
	    -d b14.openledger.vn \
	    --email admin@openledger.vn \
	    --agree-tos --no-eff-email --non-interactive"
	@echo ">>> SSL cert da cap thanh cong!"
	@echo ">>> Chay 'make ssl-upgrade' de kich hoat HTTPS."

# Bước 2: Thay HTTP-only bằng HTTPS config đầy đủ
ssl-upgrade:
	@echo ">>> Upload HTTPS config day du cho b14.openledger.vn..."
	scp nginx/b14-openledger.conf \
	    $(GW_REMOTE):$(GATEWAY_DIR)/conf.d/b14-openledger.conf
	@echo ">>> Test va reload nginx..."
	ssh $(GW_REMOTE) "cd $(GATEWAY_DIR) && \
	  docker compose exec nginx nginx -t 2>&1 | tail -3 && \
	  docker compose exec nginx nginx -s reload"
	@echo ">>> HTTPS active: https://b14.openledger.vn"

# Reload nginx trên gateway
gateway-reload:
	ssh $(GW_REMOTE) "cd $(GATEWAY_DIR) && \
	  docker compose exec nginx nginx -t && \
	  docker compose exec nginx nginx -s reload"
	@echo ">>> Nginx gateway da reload."

# Kiểm tra trạng thái nginx + cert
gateway-status:
	@echo "=== Nginx config test ==="
	ssh $(GW_REMOTE) "docker exec ms-nginx-proxy nginx -t 2>&1 | tail -5"
	@echo ""
	@echo "=== b14 cert ==="
	ssh $(GW_REMOTE) "docker exec ms-certbot \
	  openssl x509 -in /etc/letsencrypt/live/b14.openledger.vn/fullchain.pem \
	  -noout -subject -dates 2>/dev/null || echo '(cert chua ton tai — chay make ssl-init)'"
	@echo ""
	@echo "=== Tat ca certs (Let Encrypt) ==="
	ssh $(GW_REMOTE) "docker exec ms-certbot certbot certificates 2>/dev/null | grep -E 'Domains:|Expiry|b14'"

# ---------------------------------------------------------------
# Debug shells
# ---------------------------------------------------------------
shell-backstage:
	ssh -t $(REMOTE) "cd $(DEPLOY_DIR) && $(COMPOSE) exec backstage sh"

shell-postgres:
	ssh -t $(REMOTE) "cd $(DEPLOY_DIR) && $(COMPOSE) exec postgres psql -U \$$POSTGRES_USER backstage"

# ---------------------------------------------------------------
# Setup lần đầu (Docker đã có sẵn trên 172.20.2.41)
# ---------------------------------------------------------------
setup-server:
	ssh $(REMOTE) "mkdir -p $(DEPLOY_DIR)"
	scp .env.example $(REMOTE):$(DEPLOY_DIR)/.env.example
	@echo ">>> Thu muc $(DEPLOY_DIR) da tao tren $(SERVER)"
	@echo ">>> Buoc tiep theo:"
	@echo "    1. ssh $(REMOTE) 'cp $(DEPLOY_DIR)/.env.example $(DEPLOY_DIR)/.env && nano $(DEPLOY_DIR)/.env'"
	@echo "    2. make check-ports"
	@echo "    3. make push-image"
	@echo "    4. make deploy"
	@echo "    5. make ssl-init      (cap SSL cert lan dau)"
	@echo "    6. make ssl-upgrade   (kich hoat HTTPS)"
