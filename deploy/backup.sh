#!/bin/bash
# 每日备份脚本
# 放到 cron: 0 2 * * * /opt/sales-workbench/deploy/backup.sh

BACKUP_DIR="/opt/sales-workbench/backups"
DB_FILE="/opt/sales-workbench/server/workbench.db"
KEEP_DAYS=30

mkdir -p "$BACKUP_DIR"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/workbench_${DATE}.db"

# 使用 SQLite 安全备份（不锁表）
sqlite3 "$DB_FILE" ".backup '${BACKUP_FILE}'"

# 压缩
gzip "$BACKUP_FILE"

# 清理旧备份
find "$BACKUP_DIR" -name "*.db.gz" -mtime +$KEEP_DAYS -delete

echo "$(date): 备份完成 -> ${BACKUP_FILE}.gz ($(du -h ${BACKUP_FILE}.gz | cut -f1))"
