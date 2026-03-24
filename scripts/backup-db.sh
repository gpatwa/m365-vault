#!/bin/bash
# PostgreSQL backup script for Shieldio
# Run via cron: 0 2 * * * /path/to/backup-db.sh
#
# For Azure: Azure Flexible Server has built-in automated backups (7-35 days).
# This script is for local/self-hosted deployments.

set -euo pipefail

# Configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-m365vault}"
DB_USER="${DB_USER:-m365vault}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/m365vault}"
RETAIN_DAYS="${RETAIN_DAYS:-30}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate timestamped filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"

echo "[$TIMESTAMP] Starting PostgreSQL backup..."

# Dump and compress
PGPASSWORD="${DB_PASSWORD:-}" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-acl \
    --clean \
    --if-exists \
    | gzip > "$BACKUP_FILE"

FILESIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "[$TIMESTAMP] Backup complete: $BACKUP_FILE ($FILESIZE)"

# Cleanup old backups
DELETED=$(find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -mtime +"$RETAIN_DAYS" -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
    echo "[$TIMESTAMP] Cleaned up $DELETED backup(s) older than ${RETAIN_DAYS} days"
fi

# List current backups
echo ""
echo "Current backups:"
ls -lh "$BACKUP_DIR"/${DB_NAME}_*.sql.gz 2>/dev/null | tail -5
echo ""
echo "Total: $(ls "$BACKUP_DIR"/${DB_NAME}_*.sql.gz 2>/dev/null | wc -l) backup(s)"
