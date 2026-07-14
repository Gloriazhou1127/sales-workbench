#!/usr/bin/env python3
"""迁移脚本：给key_account_followup_logs表添加crm_account_id字段，并填充现有记录"""
import sqlite3

db = sqlite3.connect('/opt/sales-workbench/server/workbench.db')

# 1. 添加crm_account_id和customer_name_snapshot字段
try:
    db.execute('ALTER TABLE key_account_followup_logs ADD COLUMN crm_account_id TEXT')
    print('✅ 已添加crm_account_id字段')
except Exception as e:
    print(f'crm_account_id字段已存在: {e}')

try:
    db.execute('ALTER TABLE key_account_followup_logs ADD COLUMN customer_name_snapshot TEXT')
    print('✅ 已添加customer_name_snapshot字段')
except Exception as e:
    print(f'customer_name_snapshot字段已存在: {e}')

# 2. 给现有填报记录填充crm_account_id
updated = 0
logs = db.execute('SELECT id, hardware_id FROM key_account_followup_logs WHERE crm_account_id IS NULL OR crm_account_id = ""').fetchall()
print(f'\n找到 {len(logs)} 条需要更新的填报记录')

for log in logs:
    log_id = log[0]
    hardware_id = log[1]
    # 查找对应的crm_account_id和客户名称
    hardware = db.execute('SELECT crm_account_id, customer_name FROM key_account_hardware WHERE id = ?', (hardware_id,)).fetchone()
    if hardware:
        crm_id = hardware[0]
        customer_name = hardware[1]
        db.execute('UPDATE key_account_followup_logs SET crm_account_id = ?, customer_name_snapshot = ? WHERE id = ?',
                   (crm_id, customer_name, log_id))
        updated += 1
        if updated <= 5:  # 只打印前5条
            print(f'  更新 log_id={log_id}: crm_id={crm_id}, name={customer_name}')

db.commit()

# 3. 验证
total_logs = db.execute('SELECT COUNT(*) FROM key_account_followup_logs').fetchone()[0]
with_crm_id = db.execute('SELECT COUNT(*) FROM key_account_followup_logs WHERE crm_account_id IS NOT NULL AND crm_account_id != ""').fetchone()[0]
print(f'\n✅ 迁移完成: {with_crm_id}/{total_logs} 条填报记录已关联crm_account_id')

db.close()
