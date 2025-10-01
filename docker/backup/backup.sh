#!/bin/bash

set -e

# Configuration
BACKUP_DIR="/backup"
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-filemanager_prod}"
POSTGRES_USER="${POSTGRES_USER:-filemanager_prod}"
REDIS_HOST="${REDIS_HOST:-redis}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}"
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}"
S3_BUCKET="${S3_BUCKET:-}"

# Create timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="/var/log/backup.log"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "Starting backup process..."

# Create backup directories
mkdir -p $BACKUP_DIR/postgres $BACKUP_DIR/redis $BACKUP_DIR/local

# Backup PostgreSQL
log "Backing up PostgreSQL database: $POSTGRES_DB"
pg_dump \
    -h "$POSTGRES_HOST" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -F c \
    -f "$BACKUP_DIR/postgres/backup_$TIMESTAMP.dump"

# Backup Redis
log "Backing up Redis database"
redis-cli \
    -h "$REDIS_HOST" \
    -a "$REDIS_PASSWORD" \
    SAVE

# Copy Redis dump file
cp /data/dump.rdb "$BACKUP_DIR/redis/redis_$TIMESTAMP.rdb"

# Create local backup archive
log "Creating local backup archive"
tar -czf "$BACKUP_DIR/local/backup_$TIMESTAMP.tar.gz" \
    -C "$BACKUP_DIR" \
    postgres/backup_$TIMESTAMP.dump \
    redis/redis_$TIMESTAMP.rdb

# Upload to S3 if configured
if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ] && [ -n "$S3_BUCKET" ]; then
    log "Uploading backup to S3: s3://$S3_BUCKET/backup_$TIMESTAMP.tar.gz"
    aws s3 cp \
        "$BACKUP_DIR/local/backup_$TIMESTAMP.tar.gz" \
        "s3://$S3_BUCKET/backup_$TIMESTAMP.tar.gz"

    # Upload individual files as well
    aws s3 cp \
        "$BACKUP_DIR/postgres/backup_$TIMESTAMP.dump" \
        "s3://$S3_BUCKET/postgres/"

    aws s3 cp \
        "$BACKUP_DIR/redis/redis_$TIMESTAMP.rdb" \
        "s3://$S3_BUCKET/redis/"
fi

# Cleanup old backups
log "Cleaning up old backups (older than $BACKUP_RETENTION_DAYS days)"

# Local cleanup
find "$BACKUP_DIR/postgres" -name "*.dump" -type f -mtime +$BACKUP_RETENTION_DAYS -delete
find "$BACKUP_DIR/redis" -name "*.rdb" -type f -mtime +$BACKUP_RETENTION_DAYS -delete
find "$BACKUP_DIR/local" -name "*.tar.gz" -type f -mtime +$BACKUP_RETENTION_DAYS -delete

# S3 cleanup (if configured)
if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ] && [ -n "$S3_BUCKET" ]; then
    # List and delete old S3 backups
    OLD_BACKUPS=$(aws s3api list-objects-v2 \
        --bucket "$S3_BUCKET" \
        --prefix "backup_" \
        --query "Contents[?LastModified<=\`${TIMESTAMP}\`].Key" \
        --output text)

    if [ -n "$OLD_BACKUPS" ]; then
        for backup in $OLD_BACKUPS; do
            # Check if backup is older than retention period
            BACKUP_DATE=$(echo "$backup" | sed -n 's/backup_\([0-9]\{8\}_[0-9]\{6\}\).tar.gz/\1/p')
            if [ -n "$BACKUP_DATE" ]; then
                BACKUP_TIMESTAMP=$(date -d "${BACKUP_DATE:0:8} ${BACKUP_DATE:9:6}" +%s 2>/dev/null || echo "0")
                CURRENT_TIMESTAMP=$(date +%s)
                AGE_DAYS=$(( (CURRENT_TIMESTAMP - BACKUP_TIMESTAMP) / 86400 ))

                if [ "$AGE_DAYS" -gt "$BACKUP_RETENTION_DAYS" ]; then
                    log "Deleting old S3 backup: $backup"
                    aws s3 rm "s3://$S3_BUCKET/$backup"
                fi
            fi
        done
    fi
fi

# Verify backup integrity
log "Verifying backup integrity"
if [ -f "$BACKUP_DIR/local/backup_$TIMESTAMP.tar.gz" ]; then
    BACKUP_SIZE=$(stat -c%s "$BACKUP_DIR/local/backup_$TIMESTAMP.tar.gz")
    log "Backup created successfully: backup_$TIMESTAMP.tar.gz (${BACKUP_SIZE} bytes)"
else
    log "ERROR: Backup file not found!"
    exit 1
fi

log "Backup process completed successfully"