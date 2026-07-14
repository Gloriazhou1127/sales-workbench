import sqlite3
conn = sqlite3.connect('/opt/sales-workbench/server/workbench.db')
c = conn.cursor()

# 1. 按名称找重复
c.execute("""
    SELECT customer_name, COUNT(*) as cnt, GROUP_CONCAT(crm_account_id) as ids
    FROM key_account_hardware 
    WHERE customer_name IS NOT NULL AND customer_name != ''
    GROUP BY customer_name 
    HAVING cnt > 1
    ORDER BY cnt DESC
""")
name_dupes = c.fetchall()
print(f"=== 同名重复: {len(name_dupes)} 组 ===")
for n, cnt, ids in name_dupes:
    print(f"  '{n}': {cnt}条 (IDs: {ids})")

# 2. 按 ID 找重复
c.execute("""
    SELECT crm_account_id, COUNT(*) as cnt, GROUP_CONCAT(customer_name) as names
    FROM key_account_hardware 
    WHERE crm_account_id IS NOT NULL AND crm_account_id != ''
    GROUP BY crm_account_id 
    HAVING cnt > 1
""")
id_dupes = c.fetchall()
print(f"\n=== ID重复: {len(id_dupes)} 组 ===")
for aid, cnt, names in id_dupes[:10]:
    print(f"  {aid}: {cnt}条 (Names: {names})")

# 3. 客户名前面相同但大小写/空格不同的潜在重复
c.execute("""
    SELECT LOWER(TRIM(customer_name)) as norm_name, COUNT(*) as cnt, 
           GROUP_CONCAT(DISTINCT customer_name) as originals,
           GROUP_CONCAT(crm_account_id) as ids
    FROM key_account_hardware 
    WHERE customer_name IS NOT NULL AND customer_name != ''
    GROUP BY norm_name
    HAVING cnt > 1
    ORDER BY cnt DESC
""")
norm_dupes = c.fetchall()
print(f"\n=== 标准化后重复: {len(norm_dupes)} 组 ===")
for nn, cnt, origs, ids in norm_dupes[:20]:
    print(f"  '{nn}' → {origs} (IDs: {ids})")

# 4. 总记录、总唯一ID、总唯一名称
c.execute("SELECT COUNT(*) FROM key_account_hardware")
total = c.fetchone()[0]
c.execute("SELECT COUNT(DISTINCT crm_account_id) FROM key_account_hardware WHERE crm_account_id!=''")
uniq_id = c.fetchone()[0]
c.execute("SELECT COUNT(DISTINCT customer_name) FROM key_account_hardware WHERE customer_name!=''")
uniq_name = c.fetchone()[0]
c.execute("SELECT COUNT(DISTINCT LOWER(TRIM(customer_name))) FROM key_account_hardware WHERE customer_name!=''")
uniq_norm = c.fetchone()[0]

print(f"\n=== 总数 ===")
print(f"总记录: {total}")
print(f"唯一ID: {uniq_id}")
print(f"唯一名称: {uniq_name}")
print(f"唯一标准化名: {uniq_norm}")

conn.close()
