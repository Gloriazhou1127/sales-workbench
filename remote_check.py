#!/usr/bin/env python3
import sqlite3

db = sqlite3.connect("/opt/sales-workbench/server/workbench.db")
db.row_factory = sqlite3.Row

cursor = db.cursor()

# 查看 filled_by 的所有值
print("=== 填报记录中的 filled_by ===")
rows = cursor.execute(
    "SELECT DISTINCT filled_by, COUNT(*) as cnt FROM key_account_followup_logs GROUP BY filled_by ORDER BY cnt DESC"
).fetchall()
for r in rows:
    print("  [" + r["filled_by"] + "] (" + str(r["cnt"]) + "条)")

print("")

# 查看 owner_name 的所有值（前30个）
print("=== 客户表中的 owner_name（样例）===")
rows = cursor.execute(
    "SELECT DISTINCT owner_name, COUNT(*) as cnt FROM key_account_hardware WHERE owner_name != '' AND owner_name IS NOT NULL GROUP BY owner_name ORDER BY cnt DESC LIMIT 30"
).fetchall()
for r in rows:
    print("  [" + r["owner_name"] + "] (" + str(r["cnt"]) + "个客户)")

db.close()
