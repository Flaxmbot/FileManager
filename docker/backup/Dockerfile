FROM alpine:latest

# Install necessary packages
RUN apk add --no-cache \
    postgresql-client \
    redis \
    bash \
    curl \
    gzip \
    aws-cli \
    && rm -rf /var/cache/apk/*

# Create backup directory
RUN mkdir -p /backup/postgres /backup/redis /backup/local

# Copy backup script
COPY backup.sh /usr/local/bin/backup.sh
RUN chmod +x /usr/local/bin/backup.sh

# Create backup user
RUN addgroup -g 1000 backup && \
    adduser -D -u 1000 -G backup backup

# Set ownership
RUN chown -R backup:backup /backup
USER backup

# Run backup script
CMD ["/usr/local/bin/backup.sh"]