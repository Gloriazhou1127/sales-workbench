"""
离职处理脚本（幂等、可重跑）。
用途：将指定员工标记为离职 —— 禁用登录、清除其在组织层级中的上级/下属关系、
      并把原下属的 L3/L4 归属转移到现任负责人。

本脚本只处理"组织关系与账号状态"，不删除任何数据行，保留历史可追溯。

用法：
    python seed_leave.py            # 默认处理李泽霖
    python seed_leave.py 张三 李四   # 可指定其他离职人名
"""
import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), 'workbench.db')

# 离职员工 -> 其原 L3 下属的新 L3 负责人 / 原 L4 下属的新 L4 负责人
# 李泽霖：企培长春 L3/L4 负责人，继任 L3 = 薛希彤，组内 L4 负责人 = 胥沛弛
LEAVE_PLAN = {
    '李泽霖': {'new_l3_leader': '薛希彤', 'new_l4_leader': '胥沛弛'},
}


def main():
    targets = sys.argv[1:] or list(LEAVE_PLAN.keys())
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    c = db.cursor()

    for name in targets:
        plan = LEAVE_PLAN.get(name)
        if not plan:
            print(f'  ⚠ 未配置 {name} 的接任方案，跳过（可在 LEAVE_PLAN 中补充）')
            continue

        existing = c.execute("SELECT id, username, enabled FROM users WHERE display_name=?", (name,)).fetchone()
        if not existing:
            print(f'  ⚠ 未找到用户 {name}，跳过')
            continue

        # 1) 读取其原 L3 / L4 下属（先于删除，避免读不到）
        l3_subs = [r['subordinate_name'] for r in c.execute(
            "SELECT subordinate_name FROM org_hierarchy WHERE leader_name=? AND level='L3'", (name,))]
        l4_subs = [r['subordinate_name'] for r in c.execute(
            "SELECT subordinate_name FROM org_hierarchy WHERE leader_name=? AND level='L4'", (name,))]

        # 2) 禁用账号
        c.execute("UPDATE users SET enabled=0 WHERE display_name=?", (name,))
        print(f'  ✓ 禁用账号 {name}（{existing["username"]}）')

        # 3) 原下属的 L3 负责人 -> 新 L3 负责人；原 L4 负责人=离职人 的 -> 新 L4 负责人
        new_l3 = plan['new_l3_leader']
        new_l4 = plan['new_l4_leader']
        for sub in l3_subs:
            c.execute("UPDATE users SET l3_leader=? WHERE display_name=?", (new_l3, sub))
        for sub in l4_subs:
            c.execute("UPDATE users SET l4_leader=? WHERE display_name=? AND l4_leader=?", (new_l4, sub, name))
        print(f'  ✓ 转移 L3 下属 {len(l3_subs)} 人 -> {new_l3}；L4 下属 {len(l4_subs)} 人 -> {new_l4}')

        # 4) 清除其组织层级关系（作为 leader 与作为 subordinate）
        c.execute("DELETE FROM org_hierarchy WHERE leader_name=?", (name,))
        c.execute("DELETE FROM org_hierarchy WHERE subordinate_name=?", (name,))
        print(f'  ✓ 清除 {name} 在 org_hierarchy 的全部关系')

        # 5) 把原 L4 下属补回新 L4 负责人的组织关系（保持新 L4 负责人可见）
        for sub in l4_subs:
            c.execute(
                "INSERT OR IGNORE INTO org_hierarchy (leader_name, level, subordinate_name, dept_l3, dept_l4) "
                "VALUES (?, 'L4', ?, '', '')", (new_l4, sub))
        if l4_subs:
            print(f'  ✓ 已为 {new_l4} 补回 L4 组织关系 {len(l4_subs)} 条')

        # 6) 同步其本人 is_l3_leader / is_l4_leader 标记（停用后不再担任负责人）
        c.execute("UPDATE users SET is_l3_leader=0, is_l4_leader=0 WHERE display_name=?", (name,))

    db.commit()
    db.close()
    print('\n离职处理完成。')


if __name__ == '__main__':
    main()
