# -*- coding: utf-8 -*-
"""从本地CSV/Excel文件导入大客户打点数据到SQLite"""

import csv, sqlite3, os, sys
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = r'C:\Work\M-企业事业部\2026系统问题\销售工作台\大客户跟进'
DB_PATH = os.path.join(BASE, 'server', 'workbench.db')

print(f"DB: {DB_PATH}")
print(f"Data dir: {DATA_DIR}")

# ============================================================
# 1. 读取客户清单 (处理重复列名"客户")
# ============================================================
customers = {}  # crm_account_id -> {name, dept, owner, classroom, ka_sme}
customers_by_name = {}  # name -> crm_account_id (for matching)

with open(os.path.join(DATA_DIR, '一体机客户打点情况_清单.csv'), 'r', encoding='utf-8-sig') as f:
    # 手动解析，因为CSV有两个"客户"列
    header_line = f.readline().strip()
    headers = [h.strip('"') for h in header_line.split('","')]
    # headers: ['所属部门', '客户所有人', '客户', 'ID', '教室数量', 'KA/SME(for教培)', '创建日期', '客户']
    # 第3列(索引2)是客户名称，第8列(索引7)是重复的"客户"标记
    print(f"客户清单 headers: {headers}")

    reader = csv.reader(f)
    for row in reader:
        if len(row) < 5:
            continue
        dept = row[0].strip('"').strip()
        owner = row[1].strip('"').strip()
        name = row[2].strip('"').strip()
        cid = row[3].strip('"').strip()
        classroom = row[4].strip('"').strip()
        ka_sme = row[5].strip('"').strip() if len(row) > 5 else ''
        # skip "TOTAL" summary row
        if dept == 'TOTAL' or owner == 'TOTAL':
            continue
        try:
            classroom_int = int(classroom) if classroom else 0
        except:
            classroom_int = 0

        customers[cid] = {
            'name': name,
            'dept': dept,
            'owner': owner,
            'classroom': classroom_int,
            'ka_sme': ka_sme,
            'created_date': row[6].strip('"').strip() if len(row) > 6 else '',
        }
        customers_by_name[name] = cid

print(f"客户清单: {len(customers)} 条")
print(f"  示例: {list(customers.items())[0]}")

# ============================================================
# 2. 读取借用打点 -> 按客户ID聚合一休机借用数量
# ============================================================
lent_by_id = defaultdict(int)  # crm_account_id -> total lent

with open(os.path.join(DATA_DIR, '一体机客户打点情况_借用打点_客户明细.csv'), 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    print(f"借用打点 headers: {reader.fieldnames}")
    for row in reader:
        cid = row.get('ID', '').strip()
        count = row.get('一体机借用数量', '0').strip()
        try:
            lent_by_id[cid] += int(count) if count else 0
        except:
            pass

print(f"借用打点: {len(lent_by_id)} 个客户, 总计 {sum(lent_by_id.values())} 台")
print(f"  示例: {list(lent_by_id.items())[:3]}")

# ============================================================
# 3. 读取采购打点 (xlsx) -> 按客户ID聚合各周采购数量
# ============================================================
import openpyxl
purchased_by_id = defaultdict(int)

wb = openpyxl.load_workbook(os.path.join(DATA_DIR, '一体机客户打点情况_零星采购打点_客户明细.xlsx'))
ws = wb.active
rows = list(ws.iter_rows(values_only=True))

# 数据结构: row[0]=部门, row[1]=所有人, row[2]=客户名, row[3]=ID, row[4:]=各周数值
# 前4行是表头/汇总，第5行起是数据
for row in rows[4:]:  # skip header rows
    cid = str(row[3]).strip() if row[3] else ''
    name = str(row[2]).strip() if row[2] else ''
    if not cid or cid == 'None':
        continue
    # 跳过合计行
    if str(row[0]).strip() == '合计' or name == '合计':
        continue
    # 各周数值求和
    total = 0
    for val in row[4:]:
        if val and str(val).strip() not in ('', '-', 'None'):
            try:
                total += int(float(val))
            except:
                pass
    purchased_by_id[cid] += total

print(f"采购打点: {len(purchased_by_id)} 个客户, 总计 {sum(purchased_by_id.values())} 台")
print(f"  示例: {list(purchased_by_id.items())[:3]}")

# ============================================================
# 4. 读取拜访明细 -> 按客户名称聚合拜访次数和最近拜访日期
# ============================================================
visits_by_name = defaultdict(lambda: {'count': 0, 'last_date': ''})

with open(os.path.join(DATA_DIR, '拜访明细_打点客户.csv'), 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    print(f"拜访明细 headers: {reader.fieldnames}")
    for row in reader:
        name = row.get('客户', '').strip()
        if not name:
            continue
        date_str = row.get('创建日期', '').strip()
        visits_by_name[name]['count'] += 1
        if date_str and date_str > visits_by_name[name]['last_date']:
            visits_by_name[name]['last_date'] = date_str

print(f"拜访明细: {len(visits_by_name)} 个不同客户, 总计 {sum(v['count'] for v in visits_by_name.values())} 次")
print(f"  示例: {list(visits_by_name.items())[:3]}")

# ============================================================
# 5. 读取商机复盘表 -> 按客户ID聚合商机数和商机金额
# ============================================================
opp_by_id = defaultdict(lambda: {'count': 0, 'amount': 0.0})

with open(os.path.join(DATA_DIR, '商机复盘表.csv'), 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    print(f"商机复盘 headers: {reader.fieldnames}")
    for row in reader:
        cid = row.get('ID', '').strip()
        if not cid:
            continue
        count = int(row.get('商机', 0) or 0)
        amount = float(row.get('商机金额', 0) or 0)
        opp_by_id[cid]['count'] += count
        opp_by_id[cid]['amount'] += amount

print(f"商机复盘: {len(opp_by_id)} 个客户, 总计 {sum(v['count'] for v in opp_by_id.values())} 个商机, {sum(v['amount'] for v in opp_by_id.values()):.0f} 元")
print(f"  示例: {list(opp_by_id.items())[:3]}")

# ============================================================
# 6. 合并数据并更新SQLite
# ============================================================
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 先获取现有数据
existing = {}
for row in cur.execute("SELECT id, crm_account_id, customer_name FROM key_account_hardware").fetchall():
    existing[row['crm_account_id']] = {'row_id': row['id'], 'name': row['customer_name']}

print(f"\n数据库现有: {len(existing)} 条")

# 构建每个客户的聚合数据
merged = {}
for cid, info in customers.items():
    merged[cid] = {
        'customer_name': info['name'],
        'department': info['dept'],
        'owner_name': info['owner'],
        'created_date': info.get('created_date', ''),
        'classroom_count': info['classroom'],
        'ka_sme': info['ka_sme'],
        'lent_units': lent_by_id.get(cid, 0),
        'purchased_units': purchased_by_id.get(cid, 0),
        'visit_count': 0,
        'last_visit_date': None,
        'opportunity_count': opp_by_id.get(cid, {}).get('count', 0),
        'opportunity_amount': opp_by_id.get(cid, {}).get('amount', 0.0),
    }

# 匹配拜访数据 - 按客户名称
for name, vdata in visits_by_name.items():
    cid = customers_by_name.get(name)
    if cid and cid in merged:
        merged[cid]['visit_count'] = vdata['count']
        merged[cid]['last_visit_date'] = vdata['last_date']

# 更新数据库
updated = 0
created = 0
matched_visits = 0
auto_marked = 0
now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

for cid, data in merged.items():
    # 自动打点逻辑：借用或采购>0 → 默认已打点 + 阶段1
    auto_checked = 1 if (data['lent_units'] > 0 or data['purchased_units'] > 0) else 0

    if cid in existing:
        # 更新 CRM 同步字段；自动打点（不覆盖已有手动打点）
        cur.execute("""
            UPDATE key_account_hardware SET
                customer_name = ?, department = ?, owner_name = ?,
                created_date = ?, classroom_count = ?, lent_units = ?, purchased_units = ?,
                visit_count = ?, last_visit_date = ?, opportunity_count = ?,
                opportunity_amount = ?,
                is_checked_in = CASE WHEN is_checked_in=0 AND ?=1 THEN 1 ELSE is_checked_in END,
                checkin_stage  = CASE WHEN is_checked_in=0 AND checkin_stage IS NULL AND ?=1 THEN '1' ELSE checkin_stage END,
                synced_at = ?
            WHERE crm_account_id = ?
        """, (
            data['customer_name'], data['department'], data['owner_name'],
            data['created_date'],
            data['classroom_count'], data['lent_units'], data['purchased_units'],
            data['visit_count'], data['last_visit_date'], data['opportunity_count'],
            data['opportunity_amount'],
            auto_checked, auto_checked,
            now, cid
        ))
        updated += 1
        if data['visit_count'] > 0:
            matched_visits += 1
        if auto_checked:
            auto_marked += 1
    else:
        # 插入新记录
        auto_stage = '1' if auto_checked else None
        cur.execute("""
            INSERT INTO key_account_hardware
                (crm_account_id, customer_name, department, owner_name,
                 created_date, classroom_count, lent_units, purchased_units,
                 visit_count, last_visit_date, opportunity_count, opportunity_amount,
                 is_checked_in, checkin_stage, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cid, data['customer_name'], data['department'], data['owner_name'],
            data['created_date'],
            data['classroom_count'], data['lent_units'], data['purchased_units'],
            data['visit_count'], data['last_visit_date'], data['opportunity_count'],
            data['opportunity_amount'],
            auto_checked, auto_stage,
            now
        ))
        created += 1
        if data['visit_count'] > 0:
            matched_visits += 1
        if auto_checked:
            auto_marked += 1

conn.commit()

# 统计
total_lent = sum(d['lent_units'] for d in merged.values())
total_purchased = sum(d['purchased_units'] for d in merged.values())
total_visits = sum(d['visit_count'] for d in merged.values())
total_opps = sum(d['opportunity_count'] for d in merged.values())

print(f"\n=== 导入完成 ===")
print(f"更新: {updated} 条")
print(f"新增: {created} 条")
print(f"拜访匹配成功: {matched_visits} 个客户")
print(f"自动打点(借/采>0): {auto_marked} 个客户")
print(f"---")
print(f"借用总计: {total_lent} 台")
print(f"采购总计: {total_purchased} 台")
print(f"拜访总计: {total_visits} 次")
print(f"商机总计: {total_opps} 个")

# 显示几条示例数据验证
print(f"\n=== 示例数据验证 ===")
for row in cur.execute("""
    SELECT customer_name, department, owner_name, classroom_count,
           lent_units, purchased_units, visit_count, opportunity_count, opportunity_amount, last_visit_date
    FROM key_account_hardware
    WHERE lent_units > 0 OR purchased_units > 0 OR visit_count > 0 OR opportunity_count > 0
    ORDER BY classroom_count DESC LIMIT 10
""").fetchall():
    print(f"  {row['customer_name']} | {row['department']} | 教室{row['classroom_count']} | "
          f"借{row['lent_units']} 采{row['purchased_units']} "
          f"访{row['visit_count']} 商{row['opportunity_count']}(¥{row['opportunity_amount'] or 0:.0f}) | 最近拜访{row['last_visit_date'] or '无'}")

conn.close()
print("\nDone!")
