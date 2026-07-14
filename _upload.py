"""通过 API 上传 CSV 到本地服务器，验证客户名称匹配"""
import requests
import json

BASE = "http://localhost:5100"

# 1. 登录获取 token
r = requests.post(f"{BASE}/api/login", json={"username": "admin", "password": "admin123"})
token = r.json()["token"]
print(f"Token: {token[:30]}...")

# 2. 上传 CSV 文件
csv_path = "C:/Work/M-企业事业部/2026系统问题/销售工作台/大客户跟进/客户清单_2026-06-29.csv"
with open(csv_path, "rb") as f:
    r = requests.post(
        f"{BASE}/api/data-import/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"files": ("客户清单_2026-06-29.csv", f, "text/csv")},
    )
result = r.json()
print(json.dumps(result, ensure_ascii=False, indent=2))

# 3. 检查修复后还有多少 "1"
if result.get("results"):
    print("\n=== 导入日志 ===")
    r2 = requests.get(
        f"{BASE}/api/data-import/logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    logs = r2.json().get("logs", [])
    for log in logs[:3]:
        print(f"  {log['file_name']:30s} type={log['data_type']} "
              f"ok={log['success_count']} err={log.get('error_count',0)} "
              f"filtered={log.get('filtered_count',0)}")
