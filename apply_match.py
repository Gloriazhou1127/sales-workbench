#!/usr/bin/env python3
import sqlite3

db = sqlite3.connect("/opt/sales-workbench/server/workbench.db")
db.row_factory = sqlite3.Row

cursor = db.cursor()

print("开始更新填报记录...")

# 从 followup_match_preview 表读取匹配结果并更新
rows = cursor.execute("""
    SELECT log_id, new_hardware_id, crm_account_id, customer_name
    FROM followup_match_preview
""").fetchall()

updated = 0
for r in rows:
    cursor.execute("""
        UPDATE key_account_followup_logs
        SET hardware_id = ?,
            crm_account_id = ?,
            customer_name_snapshot = ?
        WHERE id = ?
    """, (r['new_hardware_id'], r['crm_account_id'], r['customer_name'], r['log_id']))
    updated += 1

db.commit()

print("更新完成！共更新 %d 条记录" % updated)

# 验证
print()
print("=== 验证：随机抽查5条 ===")
rows = cursor.execute("""
    SELECT f.id, f.filled_by, f.crm_account_id, f.customer_name_snapshot, h.customer_name as actual_name
    FROM key_account_followup_logs f
    LEFT JOIN key_account_hardware h ON f.hardware_id = h.id
    WHERE f.crm_account_id IS NOT NULL
    LIMIT 5
""").fetchall()
for r in rows:
    match_ok = "✓" if r['customer_name_snapshot'] == r['actual_name'] else "✗"
    print("  log_id=%d, %s customer_name=%s, actual=%s" % (r['id'], match_ok, r['customer_name_snapshot'], r['actual_name']))

# 检查是否还有未关联的
remaining = cursor.execute("""
    SELECT COUNT(*) FROM key_account_followup_logs
    WHERE crm_account_id IS NULL OR crm_account_id = ''
""").fetchone()[0]
print()
print("剩余未关联记录: %d" % remaining)

db.close()
