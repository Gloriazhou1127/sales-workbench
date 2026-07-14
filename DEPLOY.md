# 销售工作台 - 线上化部署指南

## 你的选择：腾讯云 + SQLite + 域名HTTPS

---

## 你需要做的（三步）

### 第一步：注册腾讯云（5分钟）

1. 访问 [cloud.tencent.com](https://cloud.tencent.com) 注册账号
2. 实名认证（个人/企业均可）

### 第二步：购买服务器 + 域名

**轻量应用服务器**（推荐新人套餐）：
- 规格：2核2G / 40G SSD / 3M带宽
- 方案：选择 Ubuntu 22.04 LTS 系统
- 约 ¥58-68/月（新用户优惠）

**域名**（可选，约 ¥30-50/年）：
- 在腾讯云 DNSPod 注册，后续 SSL 证书免费
- 如果暂时不用域名，可用 IP 直连（跳过证书步骤）

### 第三步：告诉我服务器信息

购买后提供：
- 服务器公网 IP
- root 密码（或 SSH 密钥）
- 域名（如果有）

---

## 我来做的（一键部署）

准备好后，我会帮你一键完成：

```
sudo bash setup.sh your-domain.com
```

自动完成：
1. 安装 Python + Nginx + 依赖
2. 创建虚拟环境 + 安装包
3. 配置 Nginx 反向代理
4. 申请免费 SSL 证书（Let's Encrypt）
5. 注册 systemd 开机自启服务
6. 配置每日数据库自动备份

---

## 部署包文件清单

已准备好的配置文件：

| 文件 | 用途 |
|------|------|
| `deploy/setup.sh` | 一键部署脚本 |
| `deploy/nginx.conf` | Nginx 配置（含 HTTPS 跳转） |
| `deploy/sales-workbench.service` | Systemd 服务（崩溃自动重启） |
| `deploy/backup.sh` | 每日备份脚本（保留30天） |
| `.env` | 环境配置（含随机密钥） |
| `requirements.txt` | Python 依赖清单 |
| `server/wsgi.py` | 生产环境入口 |
| `server/gunicorn.conf.py` | 多 worker + 自动重启 |

---

## 成本估算

| 项目 | 月费 | 年费 |
|------|------|------|
| 轻量服务器 2核2G | ~¥60 | ~¥720 |
| 域名 (.cn) | — | ~¥30 |
| SSL 证书 | 免费 | 免费 |
| **合计** | **~¥60/月** | **~¥750/年** |

---

## 部署后日常运维

```bash
# 查看服务状态
systemctl status sales-workbench

# 重启
systemctl restart sales-workbench

# 查看实时日志
journalctl -u sales-workbench -f

# SSL 证书自动续期（已内置）
certbot renew
```
