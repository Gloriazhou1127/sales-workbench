"""
WSGI 入口 — 生产环境用 gunicorn 启动:
    gunicorn -c gunicorn.conf.py wsgi:application
"""
from server.app import app
application = app

if __name__ == '__main__':
    app.run()
