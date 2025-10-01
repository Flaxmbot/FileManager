# PostgreSQL Dockerfile for FileManager Bot
FROM postgres:15-alpine

# Set environment variables for PostgreSQL optimization
ENV POSTGRES_DB=filemanager \
    POSTGRES_USER=filemanager_user \
    PGDATA=/var/lib/postgresql/data/pgdata \
    POSTGRES_HOST_AUTH_METHOD=trust

# Install additional packages for monitoring and backup
RUN apk add --no-cache \
    curl \
    gzip \
    pigz \
    && rm -rf /var/cache/apk/*

# Create necessary directories
RUN mkdir -p /var/lib/postgresql/data \
    /var/lib/postgresql/backups \
    /var/lib/postgresql/wal-archive \
    /docker-entrypoint-initdb.d

# Set proper permissions
RUN chown -R postgres:postgres /var/lib/postgresql \
    && chmod 700 /var/lib/postgresql/data

# Copy initialization scripts
COPY docker/postgres/init-scripts/ /docker-entrypoint-initdb.d/

# Copy configuration files
COPY docker/postgres/conf/ /etc/postgresql/

# Set proper permissions for init scripts
RUN chmod +x /docker-entrypoint-initdb.d/*.sh 2>/dev/null || true

# Create health check script
RUN echo '#!/bin/bash\n\
set -eo pipefail\n\
\n\
# Check if PostgreSQL is ready\n\
if ! pg_isready -U $POSTGRES_USER -d $POSTGRES_DB -h localhost; then\n\
    echo "PostgreSQL is not ready"\n\
    exit 1\n\
fi\n\
\n\
# Check if we can connect and run a simple query\n\
if ! psql -U $POSTGRES_USER -d $POSTGRES_DB -h localhost -c "SELECT 1;" > /dev/null; then\n\
    echo "Cannot execute queries on PostgreSQL"\n\
    exit 1\n\
fi\n\
\n\
echo "PostgreSQL is healthy"\n\
exit 0' > /usr/local/bin/healthcheck.sh && \
    chmod +x /usr/local/bin/healthcheck.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Create backup script
RUN echo '#!/bin/bash\n\
set -eo pipefail\n\
\n\
BACKUP_DIR="/var/lib/postgresql/backups"\n\
TIMESTAMP=$(date +%Y%m%d_%H%M%S)\n\
BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.sql.gz"\n\
\n\
echo "Creating backup: $BACKUP_FILE"\n\
\n\
# Create backup using pg_dump\n\
pg_dump -U $POSTGRES_USER -h localhost -d $POSTGRES_DB | gzip > "$BACKUP_FILE"\n\
\n\
# Clean up old backups (keep last 7 days)\n\
find "$BACKUP_DIR" -name "backup_*.sql.gz" -type f -mtime +7 -delete\n\
\n\
echo "Backup completed successfully"\n\
' > /usr/local/bin/backup.sh && \
    chmod +x /usr/local/bin/backup.sh

# Create WAL archive script for PITR
RUN echo '#!/bin/bash\n\
set -eo pipefail\n\
\n\
WAL_FILE="$1"\n\
WAL_ARCHIVE_DIR="/var/lib/postgresql/wal-archive"\n\
\n\
# Copy WAL file to archive directory\n\
cp "$WAL_FILE" "$WAL_ARCHIVE_DIR/"\n\
\n\
echo "WAL file archived: $(basename $WAL_FILE)"\n\
' > /usr/local/bin/archive-wal.sh && \
    chmod +x /usr/local/bin/archive-wal.sh

# Set proper permissions for scripts
RUN chown postgres:postgres /usr/local/bin/*.sh && \
    chmod 755 /usr/local/bin/*.sh

# Switch to postgres user
USER postgres

# Expose PostgreSQL port
EXPOSE 5432

# Set default command
CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]