#!/bin/bash
# Shieldio — PostgreSQL backup script
# Run via cron: 0 2 * * * /path/to/db-backup.sh
#
# Supports:
# - Local Docker Compose (default)
# - Azure Flexible Server (set PGHOST, PGUSER, PGPASSWORD)
#
# Retention: keeps last 7 daily backups

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/m365vault}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/m365vault_${TIMESTAMP}.sql.gz"

# Database connection (defaults for Docker Compose)
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-m365vault}"
PGPASSWORD="${PGPASSWORD:-m365vault_dev}"
PGDATABASE="${PGDATABASE:-m365vault}"

export PGPASSWORD

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting database backup..."

# For Docker Compose: use docker exec
if [ "${USE_DOCKER:-false}" = "true" ]; then
    docker compose exec -T postgres pg_dump -U "$PGUSER" "$PGDATABASE" | gzip > "$BACKUP_FILE"
else
    pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$PGDATABASE" | gzip > "$BACKUP_FILE"
fi

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "[$(date)] Backup completed: $BACKUP_FILE ($BACKUP_SIZE)"

# Clean up old backups
DELETED=$(find "$BACKUP_DIR" -name "m365vault_*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
    echo "[$(date)] Cleaned up $DELETED old backup(s)"
fi

# List current backups
echo "[$(date)] Current backups:"
ls -lh "$BACKUP_DIR"/m365vault_*.sql.gz 2>/dev/null | awk '{print "  " $NF " (" $5 ")"}'

echo "[$(date)] Done."
