#!/bin/bash
# 销售工作台 - 一键部署脚本
# 用法: chmod +x setup.sh && sudo bash setup.sh YOUR_DOMAIN

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

DOMAIN="${1:-}"
if [ -z "$DOMAIN" ]; then
    echo -e "${RED}用法: sudo bash setup.sh your-domain.com${NC}"
    exit 1
fi

echo -e "${GREEN}============================${NC}"
echo -e "${GREEN}  销售工作台 - 部署安装    ${NC}"
echo -e "${GREEN}  域名: ${DOMAIN}${NC}"
echo -e "${GREEN}============================${NC}"

# ---------- 1. 系统依赖 ----------
echo -e "${YELLOW}[1/7] 安装系统依赖...${NC}"
apt update -qq
apt install -y -qq python3 python3-pip python3-venv nginx certbot python3-certbot-nginx

# ---------- 2. 创建目录 ----------
echo -e "${YELLOW}[2/7] 创建应用目录...${NC}"
mkdir -p /opt/sales-workbench /var/log/sales-workbench
cp -r . /opt/sales-workbench/

# ---------- 3. Python 虚拟环境 ----------
echo -e "${YELLOW}[3/7] 安装 Python 依赖...${NC}"
cd /opt/sales-workbench
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# ---------- 4. 配置 Nginx ----------
echo -e "${YELLOW}[4/7] 配置 Nginx...${NC}"
sed "s/YOUR_DOMAIN/${DOMAIN}/g" deploy/nginx.conf > /etc/nginx/sites-available/sales-workbench
ln -sf /etc/nginx/sites-available/sales-workbench /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# ---------- 5. HTTPS 证书 ----------
echo -e "${YELLOW}[5/7] 申请 SSL 证书 (Let's Encrypt)...${NC}"
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "admin@${DOMAIN}" --redirect

# ---------- 6. Systemd 服务 ----------
echo -e "${YELLOW}[6/7] 注册系统服务...${NC}"
cp deploy/sales-workbench.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable sales-workbench
systemctl start sales-workbench

# ---------- 7. 开机自启 ----------
echo -e "${YELLOW}[7/7] 验证服务状态...${NC}"
sleep 3
systemctl status sales-workbench --no-pager

echo -e ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}  访问地址: https://${DOMAIN}${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e ""
echo -e "常用命令:"
echo -e "  查看状态: systemctl status sales-workbench"
echo -e "  重启服务: systemctl restart sales-workbench"
echo -e "  查看日志: journalctl -u sales-workbench -f"
echo -e "  更新证书: certbot renew --dry-run"
