"""
为"重点客户跟进"配置跨三级组织可见性：
  1) 企培沈阳三级负责人 姚秋智 可查看 企培长春 全部信息
  2) 薛希彤 从 南京KA 调整为 企培长春 三级负责人，汇报给 姚秋智，并可见长春全部信息

特点：
  - cross_dept_visibility 表独立于 org_hierarchy，花名册重导不会清除，长期有效。
  - 本脚本可重复执行（幂等）。

用法：
  python seed_cross_dept.py            # 作用于同目录 workbench.db
  DB_PATH=/path/to/workbench.db python seed_cross_dept.py
"""
import os
import sqlite3

DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), 'workbench.db'))

SHENYANG_L3 = '姚秋智'      # 企培沈阳三级组织负责人
CHANGCHUN_L3 = '薛希彤'     # 新任 企培长春三级负责人
CHANGCHUN_DEPT = '企培长春'


def main():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    c = db.cursor()

    # 确保表存在（防止直接跑本脚本而未重启服务）
    c.execute('''CREATE TABLE IF NOT EXISTS cross_dept_visibility (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        leader_name TEXT NOT NULL,
        view_dept_l3 TEXT NOT NULL,
        UNIQUE(leader_name, view_dept_l3)
    )''')

    # ---- 0. 前置校验 ----
    yao = c.execute("SELECT id, display_name, dept_l3, is_l3_leader FROM users WHERE display_name=?", (SHENYANG_L3,)).fetchone()
    xue = c.execute("SELECT id, username, display_name, dept_l3, is_l3_leader FROM users WHERE display_name=?", (CHANGCHUN_L3,)).fetchone()
    print(f"[校验] {SHENYANG_L3}: {dict(yao) if yao else '未找到!'}")
    print(f"[校验] {CHANGCHUN_L3}: {dict(xue) if xue else '未找到!'}")
    if not yao or not xue:
        print("❌ 关键人员缺失，终止。")
        return

    # 企培长春 全部成员（用户表）
    cc_members = [r['display_name'] for r in c.execute(
        "SELECT display_name FROM users WHERE dept_l3=?", (CHANGCHUN_DEPT,)).fetchall()]
    print(f"[企培长春成员] {cc_members}")

    # ---- 1. 跨三级组织可见性（核心、持久）----
    for leader in (SHENYANG_L3, CHANGCHUN_L3):
        c.execute("INSERT OR IGNORE INTO cross_dept_visibility (leader_name, view_dept_l3) VALUES (?, ?)",
                  (leader, CHANGCHUN_DEPT))
    print(f"[cross_dept] 已确保 {SHENYANG_L3} 与 {CHANGCHUN_L3} 可见 {CHANGCHUN_DEPT}")

    # ---- 2. 薛希彤 调整为 企培长春三级负责人，汇报给 姚秋智 ----
    c.execute("""
        UPDATE users SET
            dept_l3=?, dept_l4='', l3_leader=?, l4_leader='',
            is_l3_leader=1, is_l4_leader=0
        WHERE display_name=?
    """, (CHANGCHUN_DEPT, SHENYANG_L3, CHANGCHUN_L3))
    print(f"[users] 已更新 {CHANGCHUN_L3}: dept_l3={CHANGCHUN_DEPT}, is_l3_leader=1, l3_leader={SHENYANG_L3}")

    # ---- 3. org_hierarchy 组织关系（结构化，花名册重导前有效；cross_dept 仍保证可见性）----
    # 3a. 薛希彤 -> 企培长春各成员（L3）
    for m in cc_members:
        if m == CHANGCHUN_L3:
            continue
        c.execute("INSERT OR IGNORE INTO org_hierarchy (leader_name, level, subordinate_name, dept_l3, dept_l4) VALUES (?, 'L3', ?, ?, '')",
                  (CHANGCHUN_L3, m, CHANGCHUN_DEPT))
    # 3b. 姚秋智 -> 薛希彤（汇报线，L3）
    c.execute("INSERT OR IGNORE INTO org_hierarchy (leader_name, level, subordinate_name, dept_l3, dept_l4) VALUES (?, 'L3', ?, ?, '')",
              (SHENYANG_L3, CHANGCHUN_L3, CHANGCHUN_DEPT))
    print(f"[org_hierarchy] 已建立 {CHANGCHUN_L3}->企培长春成员 与 {SHENYANG_L3}->{CHANGCHUN_L3} 关系")

    db.commit()

    # ---- 4. 验证 ----
    print("\n=== 验证 ===")
    for leader in (SHENYANG_L3, CHANGCHUN_L3):
        owners = c.execute("""
            SELECT DISTINCT owner_name FROM key_account_hardware
            WHERE department IN (SELECT view_dept_l3 FROM cross_dept_visibility WHERE leader_name=?)
        """, (leader,)).fetchall()
        print(f"{leader} 可见 {CHANGCHUN_DEPT} owner 数: {len(owners)} -> {[o['owner_name'] for o in owners]}")
    db.close()
    print("\n✅ 完成。请重启服务使 init_db 与新权限逻辑生效（生产：sudo systemctl restart sales-workbench）。")


if __name__ == '__main__':
    main()
