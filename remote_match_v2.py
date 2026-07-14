#!/usr/bin/env python3
import sqlite3
import csv

db = sqlite3.connect("/opt/sales-workbench/server/workbench.db")
db.row_factory = sqlite3.Row

cursor = db.cursor()

# 匹配逻辑：
# 1. filled_by（姓名）匹配 owner_name 的姓名部分（格式：姓名-工号）
# 2. 每个填报人的客户列表按 classroom_count DESC 排序
# 3. 该填报人的填报记录按 filled_at 排序
# 4. 1:1 按顺序匹配

print("=== 匹配预览（前50条）===")
print("log_id | filled_by | fill_date   | new_hardware_id | customer_name | crm_account_id")
print("-" * 100)

# 获取所有需要匹配的填报记录
unmatched_logs = cursor.execute("""
    SELECT id, hardware_id, filled_by, fill_date, filled_at
    FROM key_account_followup_logs
    WHERE (crm_account_id IS NULL OR crm_account_id = '')
    ORDER BY filled_by, filled_at
""").fetchall()

# 获取每个填报人对应的客户列表
# owner_name 格式：姓名-工号，提取姓名部分匹配 filled_by
owner_customers = {}
for r in cursor.execute("""
    SELECT id, crm_account_id, customer_name, owner_name, classroom_count
    FROM key_account_hardware
    WHERE owner_name != '' AND owner_name IS NOT NULL
""").fetchall():
    name_part = r['owner_name'].split('-')[0] if '-' in r['owner_name'] else r['owner_name']
    if name_part not in owner_customers:
        owner_customers[name_part] = []
    owner_customers[name_part].append({
        'id': r['id'],
        'crm_account_id': r['crm_account_id'],
        'customer_name': r['customer_name'],
        'owner_name': r['owner_name'],
        'classroom_count': r['classroom_count']
    })

# 按 classroom_count DESC 排序
for name in owner_customers:
    owner_customers[name].sort(key=lambda x: x['classroom_count'] or 0, reverse=True)

# 按填报人分组
owner_logs = {}
for log in unmatched_logs:
    owner = log['filled_by']
    if owner not in owner_logs:
        owner_logs[owner] = []
    owner_logs[owner].append(log)

# 匹配
match_results = []
mismatch_warnings = []

for owner, logs in owner_logs.items():
    customers = owner_customers.get(owner, [])
    if len(logs) != len(customers):
        mismatch_warnings.append("%s: 填报记录%d条 vs 客户%d个" % (owner, len(logs), len(customers)))
    
    for i, log in enumerate(logs):
        if i < len(customers):
            cust = customers[i]
            match_results.append({
                'log_id': log['id'],
                'filled_by': owner,
                'fill_date': log['fill_date'],
                'old_hardware_id': log['hardware_id'],
                'new_hardware_id': cust['id'],
                'crm_account_id': cust['crm_account_id'],
                'customer_name': cust['customer_name'],
                'owner_name': cust['owner_name'],
                'classroom_count': cust['classroom_count']
            })

# 打印预览
for r in match_results[:50]:
    print("%6d | %8s | %10s | %-15d | %s | %s" % (
        r['log_id'], r['filled_by'], r['fill_date'], 
        r['new_hardware_id'], r['customer_name'], r['crm_account_id']
    ))

print()
print("总匹配数: %d / %d" % (len(match_results), len(unmatched_logs)))

if mismatch_warnings:
    print()
    print("=== 警告：填报记录数和客户数不匹配 ===")
    for w in mismatch_warnings:
        print("  " + w)

# 保存到临时表
cursor.execute('DROP TABLE IF EXISTS followup_match_preview')
cursor.execute("""
    CREATE TABLE followup_match_preview (
        log_id INTEGER,
        filled_by TEXT,
        fill_date TEXT,
        old_hardware_id INTEGER,
        new_hardware_id INTEGER,
        crm_account_id TEXT,
        customer_name TEXT,
        owner_name TEXT,
        classroom_count INTEGER
    )
""")
for r in match_results:
    cursor.execute("""
        INSERT INTO followup_match_preview 
        (log_id, filled_by, fill_date, old_hardware_id, new_hardware_id, crm_account_id, customer_name, owner_name, classroom_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (r['log_id'], r['filled_by'], r['fill_date'], r['old_hardware_id'], 
         r['new_hardware_id'], r['crm_account_id'], r['customer_name'], r['owner_name'], r['classroom_count']))
db.commit()

# 导出CSV
with open('/opt/sales-workbench/match_preview.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['log_id', 'filled_by', 'fill_date', 'old_hardware_id', 'new_hardware_id', 'crm_account_id', 'customer_name', 'owner_name', 'classroom_count'])
    for r in match_results:
        writer.writerow([
            r['log_id'], r['filled_by'], r['fill_date'], r['old_hardware_id'],
            r['new_hardware_id'], r['crm_account_id'], r['customer_name'], 
            r['owner_name'], r['classroom_count']
        ])

print()
print("CSV已保存: /opt/sales-workbench/match_preview.csv")
print("共 %d 条匹配记录" % len(match_results))

db.close()
