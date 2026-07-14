"""CRM数据同步脚本 - 硬件打点跟进模块
从CRM刷新客户数据 + DB已有客户 + 本地导出JSON文件聚合数据，推送到Flask后端sync API
"""
import json
import sqlite3
import datetime as dt
import requests
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CRM_DIR = os.path.join(BASE_DIR, 'crm_exports')
DB_PATH = os.path.join(BASE_DIR, 'server', 'workbench.db')
API_BASE = 'http://localhost:5100'

def extract_id(val):
    """Extract ID from CRM lookup field (may be {id, name} dict or plain number)"""
    if isinstance(val, dict):
        return str(val.get('id', ''))
    elif val is not None:
        return str(val)
    return ''

def extract_name(val):
    """Extract name from CRM lookup field (may be {id, name} dict or plain string)"""
    if isinstance(val, dict):
        return val.get('name', '')
    elif val is not None:
        return str(val)
    return ''

def main():
    print(f"[{dt.datetime.now().isoformat()}] 开始CRM数据同步...")

    # ============================================================
    # 1. Load baseline accounts from DB, then overlay with CRM data
    # ============================================================
    # Step 1a: DB accounts (broader set, from previous syncs)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db_accounts = db.execute(
        'SELECT crm_account_id, customer_name, department, owner_name, classroom_count '
        'FROM key_account_hardware'
    ).fetchall()
    db.close()

    account_map = {}
    for a in db_accounts:
        aid = str(a['crm_account_id'])
        account_map[aid] = {
            'crm_account_id': aid,
            'customer_name': a['customer_name'] or '',
            'department': a['department'] or '',
            'owner_name': a['owner_name'] or '',
            'classroom_count': a['classroom_count'] or 0,
            'lent_units': 0,
            'purchased_units': 0,
            'visit_count': 0,
            'last_visit_date': '',
            'opportunity_count': 0,
        }
    print(f"  DB已有客户: {len(account_map)} 条")

    # Step 1b: Overlay fresh CRM accounts (update names/departments/owner/classroom)
    crm_accounts = []
    for f in sorted(os.listdir(CRM_DIR)):
        if f.startswith('accounts_p') and f.endswith('.json'):
            filepath = os.path.join(CRM_DIR, f)
            crm_accounts.extend(json.load(open(filepath, encoding='utf-8')))

    print(f"  CRM刷新客户: {len(crm_accounts)} 条")

    for a in crm_accounts:
        aid = extract_id(a.get('id'))
        account_map[aid] = {
            'crm_account_id': aid,
            'customer_name': a.get('accountName', a.get('name', '')),
            'department': extract_name(a.get('dimDepart')),
            'owner_name': extract_name(a.get('ownerId')),
            'classroom_count': a.get('ClassroomN__c', 0) or 0,
            'lent_units': 0,
            'purchased_units': 0,
            'visit_count': 0,
            'last_visit_date': '',
            'opportunity_count': 0,
        }

    print(f"  合并后客户总数: {len(account_map)} 条")

    # ============================================================
    # 2. Aggregate orders (lent_units / purchased_units)
    # ============================================================
    all_orders = []
    for f in ['orders_p1_5.json', 'orders_p6_10.json',
              'orders_p11_15.json', 'orders_p16_20.json']:
        filepath = os.path.join(CRM_DIR, f)
        if os.path.exists(filepath):
            all_orders.extend(json.load(open(filepath, encoding='utf-8')))
    # Also include fresh order page if available
    fresh_order_path = os.path.join(CRM_DIR, 'orders_p1.json')
    if os.path.exists(fresh_order_path):
        all_orders.extend(json.load(open(fresh_order_path, encoding='utf-8')))

    print(f"  订单数据源: {len(all_orders)} 条")

    lent_by_account = {}
    purchased_by_account = {}

    for o in all_orders:
        aid = extract_id(o.get('accountId'))
        hw = o.get('hardwareDevices__c', 0) or 0
        label = o.get('DeliveryMode__c_label', '')
        if not label:
            label = extract_name(o.get('OrderType__c', ''))
            if not label:
                delivery_mode = extract_name(o.get('DeliveryMode__c', ''))
                if delivery_mode:
                    label = delivery_mode

        if label == '借用':
            lent_by_account[aid] = lent_by_account.get(aid, 0) + hw
        elif label in ('销售', '赠送'):
            purchased_by_account[aid] = purchased_by_account.get(aid, 0) + hw

    for aid, val in lent_by_account.items():
        if aid in account_map:
            account_map[aid]['lent_units'] = val

    for aid, val in purchased_by_account.items():
        if aid in account_map:
            account_map[aid]['purchased_units'] = val

    # ============================================================
    # 3. Aggregate opportunities (opportunity_count)
    # ============================================================
    opp_path = os.path.join(CRM_DIR, 'opportunities.json')
    opportunities = []
    if os.path.exists(opp_path):
        opportunities = json.load(open(opp_path, encoding='utf-8'))

    print(f"  商机数据源: {len(opportunities)} 条")

    opp_by_account = {}
    for opp in opportunities:
        aid = extract_id(opp.get('accountId'))
        opp_by_account[aid] = opp_by_account.get(aid, 0) + 1

    for aid, cnt in opp_by_account.items():
        if aid in account_map:
            account_map[aid]['opportunity_count'] = cnt

    # ============================================================
    # 4. Aggregate visits (visit_count + last_visit_date)
    # ============================================================
    visit_path = os.path.join(CRM_DIR, 'visits.json')
    visits = []
    if os.path.exists(visit_path):
        visits = json.load(open(visit_path, encoding='utf-8'))

    print(f"  拜访数据源: {len(visits)} 条")

    visit_by_account = {}
    for v in visits:
        aid = extract_id(v.get('accountId'))
        ts = v.get('createdAt', 0) or 0
        if aid not in visit_by_account:
            visit_by_account[aid] = [0, 0]
        visit_by_account[aid][0] += 1
        if ts > visit_by_account[aid][1]:
            visit_by_account[aid][1] = ts

    for aid, (cnt, max_ts) in visit_by_account.items():
        if aid in account_map:
            account_map[aid]['visit_count'] = cnt
            if max_ts > 0:
                account_map[aid]['last_visit_date'] = dt.datetime.fromtimestamp(
                    max_ts / 1000).strftime('%Y-%m-%d')

    # ============================================================
    # 5. Login & Push to sync API
    # ============================================================
    login_resp = requests.post(f'{API_BASE}/api/login',
                               json={'username': 'admin', 'password': 'admin123'})
    if login_resp.status_code != 200:
        print(f"  登录失败: {login_resp.status_code}")
        sys.exit(1)
    token = login_resp.json()['token']
    print(f"  JWT token 已获取")

    items = list(account_map.values())
    print(f"  待同步客户: {len(items)} 条")

    batch_size = 50
    total_upserted = 0
    sync_time = dt.datetime.now().isoformat()

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        resp = requests.post(
            f'{API_BASE}/api/key-account/hardware/sync',
            headers={'Authorization': f'Bearer {token}'},
            json={'items': batch}
        )
        result = resp.json()
        print(f"  Batch {i // batch_size + 1}: {result.get('message', result)}")
        total_upserted += len(batch)

    # ============================================================
    # 6. Summary
    # ============================================================
    print()
    print("=" * 50)
    print(f"同步完成!")
    print(f"同步时间: {sync_time}")
    print(f"CRM刷新客户: {len(crm_accounts)} 条")
    print(f"DB已有客户: {len(db_accounts)} 条")
    print(f"合并后客户: {len(account_map)} 条")
    print(f"订单数据源: {len(all_orders)} 条")
    print(f"商机数据源: {len(opportunities)} 条")
    print(f"拜访数据源: {len(visits)} 条")
    print(f"更新客户数: {total_upserted} 条")
    print(f"借用台数(合计): {sum(a['lent_units'] for a in items)}")
    print(f"采购台数(合计): {sum(a['purchased_units'] for a in items)}")
    print(f"商机数(合计): {sum(a['opportunity_count'] for a in items)}")
    print(f"拜访数(合计): {sum(a['visit_count'] for a in items)}")

if __name__ == '__main__':
    main()
