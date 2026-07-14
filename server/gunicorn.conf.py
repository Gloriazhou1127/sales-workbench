"""Gunicorn 生产配置"""
import os
import multiprocessing

# 绑定地址和端口
bind = f"{os.environ.get('SERVER_HOST', '0.0.0.0')}:{os.environ.get('SERVER_PORT', '5100')}"

# Worker 数量（建议 CPU 核数 * 2 + 1）
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))

# Worker 类型（Flask 推荐 sync）
worker_class = 'sync'

# 单 worker 最大请求数（防止内存泄漏）
max_requests = 1000
max_requests_jitter = 100

# 超时
timeout = 120
graceful_timeout = 30

# 日志
accesslog = '-'
errorlog = '-'
loglevel = os.environ.get('GUNICORN_LOGLEVEL', 'info')

# 进程名
proc_name = 'sales-workbench'

# 如果有反向代理（nginx），设置转发头
forwarded_allow_ips = '*'
