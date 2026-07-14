#!/usr/bin/env python3
"""销售工作台 - 腾讯云自动化部署脚本"""
import paramiko
import sys
import time
import os

# ============================================================
# 配置（从环境变量或命令行读取）
# ============================================================
HOST = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('DEPLOY_HOST', '')
USER = sys.argv[2] if len(sys.argv) > 2 else os.environ.get('DEPLOY_USER', 'ubuntu')
PASSWORD = sys.argv[3] if len(sys.argv) > 3 else os.environ.get('DEPLOY_PASS', '')
APP_DIR = '/opt/sales-workbench'
LOG_DIR = '/var/log/sales-workbench'
PORT = 5100

if not HOST:
    print("用法: python deploy.py <服务器IP> <用户名> <密码>")
    sys.exit(1)

print(f"🔗 连接到 {USER}@{HOST}...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASSWORD, timeout=30)
print("✅ SSH 连接成功")

def run(cmd, description=""):
    if description:
        print(f"📋 {description}...")
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
    # Send sudo password if needed
    if 'sudo' in cmd:
        stdin.write(PASSWORD + '\n')
        stdin.flush()
    out = stdout.read().decode()
    err = stderr.read().decode()
    if err and 'WARNING' not in err and 'sudo' not in err.lower():
        print(f"  ⚠️  {err.strip()[:200]}")
    if out.strip():
        print(f"  {out.strip()[:300]}")
    return out, err

# ---------- 1. 系统更新 & 依赖 ----------
print("\n--- [1/6] 安装系统依赖 ---")
run("sudo apt update -qq", "更新软件源")
run("sudo apt install -y -qq python3 python3-pip python3-venv nginx", "安装 Python3 + Nginx")

# ---------- 2. 创建目录 ----------
print("\n--- [2/6] 创建目录 ---")
run(f"sudo mkdir -p {APP_DIR} {LOG_DIR}", "创建应用目录")
run(f"sudo chown -R {USER}:{USER} {APP_DIR} {LOG_DIR}", "设置目录权限")

# ---------- 3. 上传项目文件 ----------
print("\n--- [3/6] 上传项目文件 ---")
project_path = os.path.join(os.path.dirname(__file__), '..')
# 排除不需要的目录
excludes = {'venv', '__pycache__', '.git', '.workbuddy', 'crm_exports', 'cloudflared.exe', 'tmp_sync.py', 'import_local.py'}

sftp = client.open_sftp()
upload_count = 0
for root, dirs, files in os.walk(project_path):
    # 过滤目录
    dirs[:] = [d for d in dirs if d not in excludes]
    
    for fname in files:
        # 跳过一些不需要的文件
        if fname in ('workbench.db',):
            continue
        
        local_path = os.path.join(root, fname)
        rel_path = os.path.relpath(local_path, project_path)
        remote_path = os.path.join(APP_DIR, rel_path).replace('\\', '/')
        
        # 确保远程目录存在
        remote_dir = os.path.dirname(remote_path).replace('\\', '/')
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            sftp.mkdir(remote_dir)
        
        sftp.put(local_path, remote_path)
        upload_count += 1
        if upload_count % 10 == 0:
            print(f"  已上传 {upload_count} 个文件...")

sftp.close()
print(f"✅ 共上传 {upload_count} 个文件")

# ---------- 4. 安装 Python 依赖 ----------
print("\n--- [4/6] 安装 Python 依赖 ---")
run(f"cd {APP_DIR} && python3 -m venv venv", "创建虚拟环境")
run(f"cd {APP_DIR} && ./venv/bin/pip install -r requirements.txt 2>&1 | tail -5", "安装 Python 依赖")

# ---------- 5. 配置 Nginx（无域名，IP 直接访问） ----------
print("\n--- [5/6] 配置 Nginx ---")
nginx_config = f"""server {{
    listen 80 default_server;
    server_name _;

    # 日志
    access_log /var/log/sales-workbench/access.log;
    error_log /var/log/sales-workbench/error.log;

    # 文件上传限制
    client_max_body_size 50M;

    # 代理到 Flask
    location / {{
        proxy_pass http://127.0.0.1:{PORT};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}"""

# 通过 SFTP 上传 nginx 配置到临时目录，再用 sudo cp
import io
sftp = client.open_sftp()
sftp.putfo(io.BytesIO(nginx_config.encode()), '/tmp/nginx-sales-workbench')
sftp.close()
run("sudo cp /tmp/nginx-sales-workbench /etc/nginx/sites-available/sales-workbench", "写入 Nginx 配置")

run("sudo ln -sf /etc/nginx/sites-available/sales-workbench /etc/nginx/sites-enabled/", "启用站点")
run("sudo rm -f /etc/nginx/sites-enabled/default", "删除默认站点")
out, _ = run("sudo nginx -t 2>&1", "测试 nginx 配置")

# 如果 nginx 配置有错误，print it
if 'successful' not in out.lower():
    print(f"  ⚠️ Nginx 配置测试失败: {out}")

run("sudo systemctl reload nginx", "重载 Nginx")

# ---------- 6. 启动应用 ----------
print("\n--- [6/6] 启动应用 ---")

# systemd 服务文件
service_config = f"""[Unit]
Description=Sales Workbench
After=network.target

[Service]
User={USER}
Group={USER}
WorkingDirectory={APP_DIR}
Environment="PATH={APP_DIR}/venv/bin"
Environment="PYTHONPATH={APP_DIR}/server"
ExecStart={APP_DIR}/venv/bin/gunicorn -c server/gunicorn.conf.py server.wsgi:application
Restart=always
RestartSec=5
StandardOutput=append:/var/log/sales-workbench/gunicorn.log
StandardError=append:/var/log/sales-workbench/gunicorn-error.log

[Install]
WantedBy=multi-user.target
"""

# 通过 SFTP 上传 systemd 服务配置
sftp = client.open_sftp()
sftp.putfo(io.BytesIO(service_config.encode()), '/tmp/sales-workbench.service')
sftp.close()
run("sudo cp /tmp/sales-workbench.service /etc/systemd/system/sales-workbench.service", "写入 systemd 配置")

run("sudo systemctl daemon-reload", "重载 systemd")
run("sudo systemctl enable sales-workbench", "设置开机自启")
run("sudo systemctl restart sales-workbench", "启动服务")

# 检查状态
time.sleep(3)
out, _ = run("sudo systemctl is-active sales-workbench", "检查服务状态")
is_active = out.strip()

print(f"\n{'='*50}")
if is_active == 'active':
    print(f"🎉 部署成功！")
    print(f"   访问地址: http://{HOST}")
    print(f"   管理员: admin / admin123")
else:
    print(f"⚠️ 服务未启动，检查日志:")
    run("sudo journalctl -u sales-workbench --no-pager -n 30")
print(f"{'='*50}")

client.close()
