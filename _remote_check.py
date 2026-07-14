import sqlite3
import datetime

db = sqlite3.connect('server/workbench.db')
db.row_factory = sqlite3.Row

print("=== key_account_visits table ===")
count = db.execute('SELECT COUNT(*) FROM key_account_visits').fetchone()[0]
print(f'Total records: {count}')

rows = db.execute(
    'SELECT v.user_id, u.username, u.display_name, v.last_visited_at '
    'FROM key_account_visits v '
    'LEFT JOIN users u ON u.id = v.user_id '
    'ORDER BY v.last_visited_at DESC'
).fetchall()
for r in rows:
    print(f"  user_id={r['user_id']} name={r['display_name'] or r['username']} visited={r['last_visited_at']}")

# Check if table schema is correct
print("\n=== Table schema ===")
for col in db.execute('PRAGMA table_info(key_account_visits)').fetchall():
    print(f"  {dict(col)}")

db.close()
print("\nDone!")
