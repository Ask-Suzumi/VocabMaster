#!/bin/bash
# VocabMaster 一键部署脚本（Nginx + HTTPS + Docker）
# 用法: bash deploy.sh muvsera.cc.cd your@email.com

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${RED}[!]${NC} $1"; }
info() { echo -e "${CYAN}[>]${NC} $1"; }

DOMAIN="${1:-}"
EMAIL="${2:-admin@example.com}"

if [ -z "$1" ]; then
  echo "用法: bash deploy.sh <域名> [邮箱]"
  echo "示例: bash deploy.sh vocab.example.com admin@example.com"
  exit 1
fi

SERVER_IP=$(curl -s ifconfig.me)

echo "============================================"
echo "  VocabMaster 一键部署"
echo "  域名: $DOMAIN"
echo "  服务器 IP: $SERVER_IP"
echo "============================================"
echo ""

# ─── 1. 清理 Docker 构建残余 ───
info "清理临时文件..."
cd /home/vocabmaster
rm -rf '=' resolving exporting extracting '[internal]' naming reading transferring unpacking resolve sha256:* 2>/dev/null || true
log "目录已清理"

# ─── 2. 安装依赖 ───
info "安装 Nginx + Certbot..."
apt update -qq
apt install -y -qq nginx certbot python3-certbot-nginx
log "Nginx + Certbot 安装完成"

# ─── 3. 检查 DNS ───
info "检查 DNS 解析..."
DNS_IP=$(dig +short "$DOMAIN" @8.8.8.8 2>/dev/null || host "$DOMAIN" 8.8.8.8 2>/dev/null | awk '/has address/ {print $NF}')
if [ -z "$DNS_IP" ]; then
  warn "⚠️  DNS 尚未解析到 $DOMAIN"
  warn "   请在 DNS 管理后台添加 A 记录: $DOMAIN → $SERVER_IP"
  warn "   等待 DNS 生效后重新运行此脚本"
  exit 1
elif [ "$DNS_IP" != "$SERVER_IP" ]; then
  warn "⚠️  DNS 解析到 $DNS_IP，但服务器 IP 是 $SERVER_IP"
  warn "   请检查 A 记录是否正确"
  exit 1
fi
log "DNS 解析正确: $DOMAIN → $DNS_IP"

# ─── 4. 配置 Nginx ───
info "配置 Nginx 反向代理..."
cat > /etc/nginx/sites-available/vocabmaster << NGINXEOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
NGINXEOF

ln -sf /etc/nginx/sites-available/vocabmaster /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
log "Nginx 配置完成"

# ─── 5. 申请 SSL 证书 ───
info "申请 Let's Encrypt SSL 证书..."
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect
log "SSL 证书申请成功"

# ─── 6. 自动续期 ───
info "配置证书自动续期..."
CERTBOT_CRON="0 3 * * * certbot renew --quiet --post-hook 'systemctl reload nginx'"
(crontab -l 2>/dev/null | grep -v certbot; echo "$CERTBOT_CRON") | crontab -
log "自动续期已配置（每天凌晨3点检查）"

# ─── 7. 检查 Docker 服务 ───
info "检查 VocabMaster 服务..."
if docker ps --format '{{.Names}}' | grep -q vocabmaster; then
  log "Docker 容器运行中"
else
  warn "Docker 容器未运行，正在启动..."
  cd /home/vocabmaster && docker-compose up -d
  log "Docker 容器已启动"
fi

# ─── 完成 ───
echo ""
echo "============================================"
echo -e "  ${GREEN}部署完成！${NC}"
echo ""
echo "  访问地址: https://$DOMAIN"
echo "  API 文档: https://$DOMAIN/docs"
echo "============================================"
