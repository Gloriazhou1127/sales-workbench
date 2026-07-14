import sqlite3
conn = sqlite3.connect('/opt/sales-workbench/server/workbench.db')
c = conn.cursor()

# 部门分布
c.execute("""
    SELECT COALESCE(department,'NULL') as dept, COUNT(*) as cnt
    FROM key_account_hardware
    GROUP BY department
    ORDER BY cnt DESC
""")
print("=== 部门分布 ===")
for dept, cnt in c.fetchall():
    marker = "✓" if dept.startswith("企培") or dept == "NULL" else "✗ 异常"
    print(f"  {marker} [{dept}]: {cnt}")

# 异常部门的记录
c.execute("""
    SELECT crm_account_id, customer_name, department, classroom_count, lent_units
    FROM key_account_hardware
    WHERE department IS NOT NULL AND department != '' AND department NOT LIKE '企培%'
    LIMIT 20
""")
bad = c.fetchall()
print(f"\n=== 异常部门记录 ({len(bad)}) ===")
for r in bad:
    print(f"  {r}")

# 空部门的记录
c.execute("""
    SELECT COUNT(*) FROM key_account_hardware WHERE department IS NULL OR department=''
""")
null_dept = c.fetchone()[0]
print(f"\n空部门记录: {null_dept}")

# 借用客户的部门分布
c.execute("""
    SELECT COALESCE(department,'NULL') as dept, COUNT(*) as cnt
    FROM key_account_hardware
    WHERE lent_date IS NOT NULL AND lent_date!=''
    GROUP BY department
    ORDER BY cnt DESC
""")
print("\n=== 借用客户部门分布 ===")
for dept, cnt in c.fetchall():
    print(f"  [{dept}]: {cnt}")

conn.close()
