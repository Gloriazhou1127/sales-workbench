import sqlite3
db = sqlite3.connect('server/workbench.db')
cur = db.cursor()

total = cur.execute('SELECT COUNT(*) FROM key_account_hardware').fetchone()[0]
bad = cur.execute("SELECT COUNT(*) FROM key_account_hardware WHERE customer_name = '1'").fetchone()[0]
print(f'Total: {total}')
print(f'customer_name=1: {bad}')

print()
print('Sample of customer_name=1 records:')
for r in cur.execute("SELECT id, crm_account_id, customer_name, department, owner_name, classroom_count, created_date FROM key_account_hardware WHERE customer_name = '1' LIMIT 15"):
    print(f'  ID={r[0]}  CRM={r[1]}  Dept={r[3]}  Owner={r[4]}  Class={r[5]}  Created={r[6]}')

print()
print('Other short numeric names:')
for r in cur.execute("SELECT customer_name, COUNT(*) as cnt FROM key_account_hardware WHERE customer_name GLOB '[0-9]*' AND length(customer_name) <= 4 GROUP BY customer_name ORDER BY cnt DESC LIMIT 20"):
    print(f'  Name="{r[0]}"  count={r[1]}')

normal = cur.execute("SELECT COUNT(*) FROM key_account_hardware WHERE customer_name != '1' AND customer_name != ''").fetchone()[0]
empty = cur.execute("SELECT COUNT(*) FROM key_account_hardware WHERE customer_name = '' OR customer_name IS NULL").fetchone()[0]
print(f'\nNormal: {normal}')
print(f'Empty: {empty}')

db.close()
