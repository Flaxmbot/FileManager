# 🔧 Troubleshooting Guide

Comprehensive troubleshooting guide for common Telegram bot setup and runtime issues.

## 📋 Table of Contents

1. [Bot Creation Issues](#bot-creation-issues)
2. [Database Problems](#database-problems)
3. [Webhook Issues](#webhook-issues)
4. [SSL/TLS Problems](#ssltls-problems)
5. [API Integration Issues](#api-integration-issues)
6. [Performance Problems](#performance-problems)
7. [Security Issues](#security-issues)
8. [Deployment Issues](#deployment-issues)
9. [Runtime Errors](#runtime-errors)
10. [Monitoring and Alerts](#monitoring-and-alerts)

## 🤖 Bot Creation Issues

### "Bot token not valid" Error

**Symptoms:**
- Bot doesn't respond to commands
- API returns 401 Unauthorized
- BotFather shows token as invalid

**Troubleshooting Steps:**

1. **Verify token format**
   ```bash
   # Check if token starts with bot ID and has correct length
   echo "YOUR_TOKEN" | grep -E "^[0-9]+:[A-Za-z0-9_-]{35}$"
   ```

2. **Test token with Telegram API**
   ```bash
   curl -s "https://api.telegram.org/botYOUR_TOKEN/getMe" | jq .
   ```

3. **Recreate bot token**
   - Go to @BotFather
   - Send `/token` command
   - Select your bot
   - Use new token

4. **Check bot status**
   ```bash
   # Verify bot is not deleted or banned
   curl -s "https://api.telegram.org/botYOUR_TOKEN/getWebhookInfo" | jq .
   ```

### Bot Not Appearing in Search

**Symptoms:**
- Bot doesn't appear when users search for it
- Bot username shows as unavailable

**Solutions:**

1. **Wait for propagation** - May take up to 24 hours
2. **Check username format** - Must end with "bot"
3. **Verify uniqueness** - Username must be globally unique
4. **Contact Telegram support** - If issues persist

## 🗄️ Database Problems

### Connection Refused Errors

**Symptoms:**
- `asyncpg.exceptions.InvalidCatalogNameError`
- `Connection refused` messages
- Database connection timeouts

**Troubleshooting Steps:**

1. **Check PostgreSQL status**
   ```bash
   # Linux/macOS
   sudo systemctl status postgresql
   brew services list | grep postgresql

   # Windows
   netstat -an | findstr 5432
   ```

2. **Verify connection parameters**
   ```bash
   # Test basic connection
   psql -h localhost -p 5432 -U postgres -d postgres
   ```

3. **Check database exists**
   ```sql
   \l  -- List databases
   SELECT datname FROM pg_database WHERE datname = 'filemanager_dev';
   ```

4. **Verify user permissions**
   ```sql
   \du filemanager_dev  -- Check user exists and permissions
   ```

5. **Test with Python**
   ```python
   import asyncpg
   import asyncio

   async def test():
       try:
           conn = await asyncpg.connect(
               host='localhost',
               port=5432,
               user='filemanager_dev',
               password='dev_password',
               database='filemanager_dev'
           )
           print("✅ Connection successful")
           await conn.close()
       except Exception as e:
           print(f"❌ Connection failed: {e}")

   asyncio.run(test())
   ```

### Migration Failures

**Symptoms:**
- `alembic.util.exc.CommandError`
- Schema mismatch errors
- Migration rollback issues

**Solutions:**

1. **Check current migration state**
   ```bash
   python -c "
   from src.database.session import engine
   import asyncio

   async def check():
       async with engine.begin() as conn:
           result = await conn.execute('SELECT version FROM schema_migrations')
           print(await result.fetchall())

   asyncio.run(check())
   "
   ```

2. **Manual migration rollback**
   ```bash
   # Downgrade one migration
   alembic downgrade -1

   # Check migration history
   alembic history
   ```

3. **Fix schema conflicts**
   ```sql
   -- Check for constraint conflicts
   SELECT conname, conrelid::regclass
   FROM pg_constraint
   WHERE conname LIKE '%duplicate%';
   ```

### Performance Issues

**Symptoms:**
- Slow query execution
- High CPU usage
- Connection pool exhaustion

**Optimization Steps:**

1. **Check slow queries**
   ```sql
   -- Enable query logging
   SET log_min_duration_statement = 1000;
   SET log_statement = 'all';

   -- Check query performance
   EXPLAIN ANALYZE SELECT * FROM users WHERE telegram_id = 123;
   ```

2. **Database maintenance**
   ```sql
   -- Reindex tables
   REINDEX TABLE users;
   REINDEX TABLE devices;

   -- Update statistics
   ANALYZE users;
   ANALYZE devices;

   -- Check table sizes
   SELECT schemaname, tablename, attname, n_distinct
   FROM pg_stats
   WHERE tablename IN ('users', 'devices');
   ```

## 🔗 Webhook Issues

### Webhook Not Receiving Updates

**Symptoms:**
- Bot doesn't receive messages
- Webhook endpoint returns errors
- Telegram shows "webhook was deleted"

**Troubleshooting Steps:**

1. **Check webhook configuration**
   ```bash
   curl -s "https://api.telegram.org/botYOUR_TOKEN/getWebhookInfo" | jq .
   ```

2. **Test webhook endpoint**
   ```bash
   # Test webhook accessibility
   curl -k -X POST https://your-domain.com/webhook \
     -H "Content-Type: application/json" \
     -d '{"test": true}'

   # Check SSL certificate
   curl -v -I https://your-domain.com/webhook
   ```

3. **Verify server configuration**
   ```bash
   # Check if port is open
   netstat -tlnp | grep :443

   # Check nginx error logs
   sudo tail -f /var/log/nginx/error.log

   # Check application logs
   sudo journalctl -u telegram-bot -f
   ```

4. **Validate SSL certificate**
   ```bash
   # Check certificate validity
   openssl x509 -in /etc/ssl/certs/bot.crt -text -noout

   # Test SSL connection
   openssl s_client -connect your-domain.com:443 -servername your-domain.com
   ```

### IP Whitelist Issues

**Symptoms:**
- Webhook requests blocked
- "Forbidden" errors in logs
- Telegram cannot reach webhook

**Solutions:**

1. **Check current IP restrictions**
   ```bash
   # Check nginx configuration
   sudo nginx -T | grep -A 5 -B 5 "allow\|deny"

   # Check firewall rules
   sudo ufw status
   ```

2. **Update allowed IPs**
   ```nginx
   # Add current Telegram IP ranges to nginx config
   location /webhook {
       allow 149.154.160.0/20;
       allow 91.108.4.0/22;
       allow 91.108.56.0/22;
       allow 91.108.8.0/22;
       allow 95.161.64.0/20;
       allow 149.154.164.0/22;
       allow 149.154.168.0/22;
       allow 149.154.172.0/22;
       deny all;
   }
   ```

3. **Test IP accessibility**
   ```bash
   # Test from different IPs
   curl -H "X-Forwarded-For: 149.154.161.1" https://your-domain.com/webhook
   ```

## 🔒 SSL/TLS Problems

### Certificate Verification Errors

**Symptoms:**
- `SSL: CERTIFICATE_VERIFY_FAILED`
- `certificate verify failed` errors
- Webhook setup fails

**Troubleshooting Steps:**

1. **Check certificate validity**
   ```bash
   # Check expiration date
   openssl x509 -in ssl/bot.crt -noout -dates

   # Verify certificate chain
   openssl verify -CAfile chain.pem ssl/bot.crt
   ```

2. **Test SSL connection**
   ```bash
   # Test SSL handshake
   openssl s_client -connect your-domain.com:443 -servername your-domain.com

   # Check for common issues
   curl -v -I --cacert ca.pem https://your-domain.com/webhook
   ```

3. **Fix common certificate issues**
   ```bash
   # Regenerate certificate with correct SAN
   openssl req -x509 -newkey rsa:4096 \
     -keyout ssl/bot.key \
     -out ssl/bot.crt \
     -days 365 \
     -nodes \
     -subj "/CN=your-domain.com" \
     -addext "subjectAltName=DNS:your-domain.com,DNS:*.your-domain.com"
   ```

### Let's Encrypt Issues

**Symptoms:**
- Certbot fails to generate certificate
- Certificate renewal fails
- Domain validation errors

**Solutions:**

1. **Check domain configuration**
   ```bash
   # Verify domain points to correct IP
   nslookup your-domain.com

   # Check if port 80/443 are accessible
   curl -I http://your-domain.com
   curl -I https://your-domain.com
   ```

2. **Fix firewall issues**
   ```bash
   # Allow HTTP/HTTPS for Let's Encrypt
   sudo ufw allow 80
   sudo ufw allow 443

   # Check if ports are actually open
   sudo netstat -tlnp | grep -E ':(80|443)'
   ```

3. **Manual certificate generation**
   ```bash
   # Use standalone plugin
   sudo certbot certonly --standalone -d your-domain.com --agree-tos -m admin@your-domain.com

   # Use webroot plugin
   sudo certbot certonly --webroot -w /var/www/html -d your-domain.com
   ```

## 🔌 API Integration Issues

### Rate Limiting Problems

**Symptoms:**
- `429 Too Many Requests` errors
- API calls being throttled
- Slow response times

**Troubleshooting Steps:**

1. **Check current rate limits**
   ```bash
   # Monitor API usage
   curl -s "https://api.telegram.org/botYOUR_TOKEN/getMe" -w "%{time_total}\n"

   # Check rate limit headers
   curl -v "https://api.telegram.org/botYOUR_TOKEN/sendMessage" \
     -H "Content-Type: application/json" \
     -d '{"chat_id": 123, "text": "test"}' 2>&1 | grep -i "retry-after\|x-rate-limit"
   ```

2. **Implement exponential backoff**
   ```python
   import time
   import random

   def make_api_call():
       for attempt in range(3):
           try:
               response = api_call()
               if response.status_code != 429:
                   return response
           except RateLimitError:
               wait_time = (2 ** attempt) + random.random()
               time.sleep(wait_time)
       raise Exception("Max retries exceeded")
   ```

3. **Optimize API usage**
   ```python
   # Batch multiple requests
   # Use appropriate polling intervals
   # Cache frequently requested data
   ```

### Authentication Errors

**Symptoms:**
- `401 Unauthorized` responses
- Session timeout errors
- Invalid token messages

**Solutions:**

1. **Verify token validity**
   ```bash
   # Test token with getMe
   curl -s "https://api.telegram.org/botYOUR_TOKEN/getMe" | jq .ok
   ```

2. **Check token permissions**
   ```bash
   # Verify bot has necessary permissions
   curl -s "https://api.telegram.org/botYOUR_TOKEN/getMyCommands" | jq .
   ```

3. **Handle token expiration**
   ```python
   # Implement token refresh logic
   def refresh_token():
       # Request new token from BotFather
       # Update stored token
       # Retry failed requests
       pass
   ```

## ⚡ Performance Problems

### High Memory Usage

**Symptoms:**
- Application consumes excessive RAM
- OutOfMemory errors
- System becomes unresponsive

**Troubleshooting Steps:**

1. **Monitor memory usage**
   ```bash
   # Check process memory
   ps aux | grep python

   # Monitor system memory
   free -h
   htop

   # Check for memory leaks
   python -m tracemalloc -c "
   import src.main
   # Run for some time, then check top stats
   "
   ```

2. **Optimize memory usage**
   ```python
   # Use connection pooling
   # Implement proper cleanup
   # Use streaming for large files
   # Cache frequently accessed data
   ```

3. **Database optimization**
   ```sql
   -- Check for unused indexes
   SELECT schemaname, tablename, indexname, idx_scan
   FROM pg_stat_user_indexes
   ORDER BY idx_scan;

   -- Remove unused indexes
   DROP INDEX IF EXISTS unused_index_name;
   ```

### Slow Response Times

**Symptoms:**
- API calls take too long
- Users experience delays
- Timeout errors

**Optimization Steps:**

1. **Database query optimization**
   ```sql
   -- Check slow queries
   SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   ORDER BY mean_time DESC;

   -- Add missing indexes
   CREATE INDEX idx_users_last_seen ON users(last_seen);
   CREATE INDEX idx_file_operations_status ON file_operations(operation_status);
   ```

2. **Connection pool tuning**
   ```python
   # Optimize connection pool settings
   pool = await asyncpg.create_pool(
       database_url,
       min_size=5,
       max_size=20,
       command_timeout=30,
       server_settings={
           'jit': 'off',  # Disable JIT for faster simple queries
           'application_name': 'telegram-bot'
       }
   )
   ```

3. **Caching implementation**
   ```python
   # Cache frequently accessed data
   from functools import lru_cache

   @lru_cache(maxsize=1000)
   def get_user_info(user_id):
       # Cache user data for 5 minutes
       return fetch_user_from_db(user_id)
   ```

## 🔐 Security Issues

### Unauthorized Access

**Symptoms:**
- Unknown users accessing bot
- Suspicious IP addresses in logs
- Unusual API activity

**Security Measures:**

1. **Implement IP whitelisting**
   ```nginx
   # Restrict to Telegram IPs only
   location /webhook {
       allow 149.154.160.0/20;
       allow 91.108.4.0/22;
       deny all;
   }
   ```

2. **Add request validation**
   ```python
   def validate_webhook_request(request):
       # Validate Telegram signature
       # Check request timestamp
       # Verify user permissions
       pass
   ```

3. **Monitor access logs**
   ```bash
   # Check for suspicious activity
   sudo tail -f /var/log/nginx/access.log | grep -v "149.154"

   # Monitor failed authentication attempts
   sudo tail -f /var/log/telegram-bot/security.jsonl | jq 'select(.severity=="warning")'
   ```

### Data Breach Prevention

**Symptoms:**
- Sensitive data exposure
- Unauthorized file access
- Database breaches

**Prevention Steps:**

1. **Encrypt sensitive data**
   ```python
   from cryptography.fernet import Fernet

   def encrypt_sensitive_data(data):
       key = Fernet.generate_key()
       f = Fernet(key)
       return f.encrypt(data.encode())

   def decrypt_sensitive_data(token):
       return f.decrypt(token).decode()
   ```

2. **Implement access controls**
   ```sql
   -- Create role-based permissions
   CREATE ROLE bot_user;
   GRANT SELECT ON users TO bot_user;
   GRANT INSERT, UPDATE ON file_operations TO bot_user;
   REVOKE ALL ON sensitive_table FROM bot_user;
   ```

3. **Regular security audits**
   ```bash
   # Check file permissions
   find /opt/telegram-bot -type f -name "*.pem" -exec ls -la {} \;

   # Audit database permissions
   SELECT grantee, privilege_type
   FROM information_schema.role_table_grants
   WHERE table_name IN ('users', 'devices');
   ```

## 🚢 Deployment Issues

### Docker Problems

**Symptoms:**
- Container fails to start
- Volume mount issues
- Network connectivity problems

**Troubleshooting Steps:**

1. **Check container logs**
   ```bash
   docker logs telegram-bot
   docker logs postgres
   docker logs redis
   ```

2. **Verify container status**
   ```bash
   docker ps -a
   docker stats telegram-bot
   ```

3. **Check resource usage**
   ```bash
   # Container resource usage
   docker system df

   # Network configuration
   docker network ls
   docker network inspect bridge
   ```

4. **Fix common Docker issues**
   ```bash
   # Clean up unused containers
   docker system prune -a

   # Rebuild container
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

### Service Management Issues

**Symptoms:**
- Service fails to start
- Service stops unexpectedly
- Configuration not loading

**Solutions:**

1. **Check systemd status**
   ```bash
   sudo systemctl status telegram-bot
   sudo systemctl show telegram-bot
   ```

2. **Examine service logs**
   ```bash
   sudo journalctl -u telegram-bot --since today
   sudo journalctl -u telegram-bot -f
   ```

3. **Verify environment variables**
   ```bash
   # Check if environment file is loaded
   sudo systemctl show-environment

   # Test service configuration
   sudo systemd-analyze verify /etc/systemd/system/telegram-bot.service
   ```

## 🐛 Runtime Errors

### Common Python Errors

#### ImportError/ModuleNotFoundError

**Symptoms:**
- `ModuleNotFoundError: No module named 'aiogram'`
- `ImportError: cannot import name 'something'`

**Solutions:**

1. **Check Python environment**
   ```bash
   # Verify Python version
   python --version
   which python

   # Check installed packages
   pip list | grep aiogram
   ```

2. **Fix virtual environment**
   ```bash
   # Recreate virtual environment
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Check import paths**
   ```python
   import sys
   print(sys.path)

   # Add project root to path
   sys.path.insert(0, '/path/to/telegram-bot')
   ```

#### AsyncIO Event Loop Issues

**Symptoms:**
- `RuntimeError: Event loop is closed`
- `RuntimeError: Cannot run the event loop while another loop is running`

**Solutions:**

1. **Fix event loop usage**
   ```python
   # Don't create new event loops in threads
   # Use asyncio.run() instead of asyncio.get_event_loop()
   # Avoid nested event loops
   ```

2. **Proper async context management**
   ```python
   async def main():
       # Use async context managers
       async with aiohttp.ClientSession() as session:
           async with session.get(url) as response:
               return await response.text()

   # Run with asyncio.run()
   result = asyncio.run(main())
   ```

### Database Runtime Errors

#### Connection Pool Issues

**Symptoms:**
- `asyncpg.exceptions.InterfaceError`
- Connection pool exhausted
- Connection timeout errors

**Solutions:**

1. **Monitor connection pool**
   ```python
   # Check pool statistics
   print(f"Pool size: {pool.get_size()}")
   print(f"Free connections: {pool.get_free_size()}")
   ```

2. **Optimize pool settings**
   ```python
   # Adjust pool configuration
   pool = await asyncpg.create_pool(
       database_url,
       min_size=5,
       max_size=20,
       timeout=30,
       command_timeout=30
   )
   ```

3. **Handle connection errors**
   ```python
   async def safe_db_operation():
       try:
           async with pool.acquire() as conn:
               return await conn.fetch("SELECT 1")
       except asyncpg.exceptions.InterfaceError:
           # Reconnect or retry
           await pool.close()
           # Recreate pool
           pass
   ```

## 📊 Monitoring and Alerts

### Setting Up Monitoring

1. **Install monitoring tools**
   ```bash
   # Install Prometheus
   sudo apt install prometheus

   # Install Grafana
   sudo apt install grafana

   # Install alerting tools
   sudo apt install prometheus-alertmanager
   ```

2. **Configure metrics collection**
   ```yaml
   # prometheus.yml
   scrape_configs:
     - job_name: 'telegram-bot'
       static_configs:
         - targets: ['localhost:8000']
       scrape_interval: 15s
   ```

3. **Set up dashboards**
   - Import Telegram bot dashboard template
   - Configure custom metrics
   - Set up alerting rules

### Common Alert Conditions

```yaml
# Alert rules
groups:
  - name: telegram-bot-alerts
    rules:
      - alert: BotDown
        expr: up{job="telegram-bot"} == 0
        for: 2m
        labels:
          severity: critical

      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning

      - alert: DatabaseConnectionErrors
        expr: increase(db_connection_errors[5m]) > 0
        for: 1m
        labels:
          severity: critical
```

### Log Analysis

1. **Set up log aggregation**
   ```bash
   # Install ELK stack or similar
   sudo apt install elasticsearch logstash kibana

   # Configure log shipping
   sudo apt install filebeat
   ```

2. **Create log analysis queries**
   ```bash
   # Search for errors
   sudo journalctl -u telegram-bot --since "1 hour ago" | grep ERROR

   # Find slow operations
   sudo journalctl -u telegram-bot | grep "took " | awk '{print $NF}' | sort -n
   ```

## 🚨 Emergency Procedures

### Service Recovery

1. **Immediate actions**
   ```bash
   # Check service status
   sudo systemctl status telegram-bot

   # View recent logs
   sudo journalctl -u telegram-bot --since "5 minutes ago"

   # Restart service if needed
   sudo systemctl restart telegram-bot
   ```

2. **Database recovery**
   ```bash
   # Check database status
   sudo systemctl status postgresql

   # Restore from backup if needed
   python scripts/init_database.py --restore /path/to/backup.sql
   ```

3. **Webhook recovery**
   ```bash
   # Check webhook status
   curl -s "https://api.telegram.org/botYOUR_TOKEN/getWebhookInfo"

   # Reset webhook if needed
   curl -X POST "https://api.telegram.org/botYOUR_TOKEN/deleteWebhook"
   ```

### Data Recovery

1. **From backups**
   ```bash
   # List available backups
   ls -la backups/

   # Restore specific backup
   python scripts/init_database.py --restore backups/filemanager_prod_backup.sql
   ```

2. **From file system**
   ```bash
   # Check data directory
   ls -la /opt/telegram-bot/data/

   # Restore configuration
   cp config/backup/.env.production .env
   ```

### Communication Plan

1. **Internal notification**
   - Notify development team
   - Update status page
   - Escalate to on-call engineer

2. **User communication**
   - Update bot status message
   - Send notification to admin users
   - Post updates in support channels

## 📞 Getting Help

### Support Channels

1. **Primary**: Check application logs
2. **Secondary**: Review monitoring dashboard
3. **Tertiary**: Check system resources
4. **Escalation**: Contact development team

### Useful Commands

```bash
# Quick health check
curl -f https://your-domain.com/health && echo "✅ Bot is healthy"

# Check all services
sudo systemctl status telegram-bot postgresql redis nginx

# View recent errors
sudo journalctl -u telegram-bot --since "1 hour ago" | grep -i error

# Monitor resource usage
htop -p $(pgrep -f telegram-bot)

# Check database performance
psql -h localhost -U filemanager_prod -d filemanager_prod -c "SELECT * FROM pg_stat_activity;"
```

### Debug Scripts

Create these helpful debug scripts:

```bash
#!/bin/bash
# debug.sh - Comprehensive debugging script

echo "=== Telegram Bot Debug Information ==="
echo

echo "1. Service Status:"
sudo systemctl status telegram-bot --no-pager -l
echo

echo "2. Recent Logs:"
sudo journalctl -u telegram-bot --since "10 minutes ago" | tail -20
echo

echo "3. Webhook Info:"
curl -s "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo" | jq .
echo

echo "4. Database Connection:"
python -c "
import asyncpg, asyncio
async def test():
    try:
        conn = await asyncpg.connect('postgresql://filemanager_prod:pass@localhost/filemanager_prod')
        result = await conn.fetchval('SELECT COUNT(*) FROM users')
        print(f'✅ Database OK - {result} users')
        await conn.close()
    except Exception as e:
        print(f'❌ Database error: {e}')
asyncio.run(test())
"
echo

echo "5. SSL Certificate:"
openssl x509 -in /etc/ssl/certs/bot.crt -noout -dates 2>/dev/null || echo "❌ No SSL certificate found"
```

## 📈 Performance Tuning

### Database Optimization

1. **Query optimization**
   ```sql
   -- Add composite indexes
   CREATE INDEX idx_users_active_last_seen ON users(is_active, last_seen);

   -- Optimize frequently used queries
   EXPLAIN ANALYZE SELECT * FROM file_operations WHERE user_id = $1 ORDER BY created_at DESC LIMIT 10;
   ```

2. **Connection pool tuning**
   ```python
   # Optimal pool settings for production
   pool = await asyncpg.create_pool(
       database_url,
       min_size=10,
       max_size=50,
       timeout=30,
       command_timeout=30,
       server_settings={
           'effective_cache_size': '2GB',
           'work_mem': '256MB',
           'maintenance_work_mem': '512MB',
           'checkpoint_segments': '32',
           'shared_buffers': '1GB'
       }
   )
   ```

### Application Optimization

1. **Caching strategy**
   ```python
   # Implement Redis caching
   import redis
   import json

   cache = redis.Redis(host='localhost', port=6379, db=0)

   def get_cached_user(user_id):
       cached = cache.get(f"user:{user_id}")
       if cached:
           return json.loads(cached)
       # Fetch from database and cache
       user = fetch_user_from_db(user_id)
       cache.setex(f"user:{user_id}", 300, json.dumps(user))
       return user
   ```

2. **Async optimization**
   ```python
   # Use proper async patterns
   async def handle_multiple_users(user_ids):
       # Create tasks for concurrent processing
       tasks = [process_user(user_id) for user_id in user_ids]

       # Process with controlled concurrency
       semaphore = asyncio.Semaphore(10)  # Max 10 concurrent

       async def bounded_process(user_id):
           async with semaphore:
               return await process_user(user_id)

       results = await asyncio.gather(*[bounded_process(uid) for uid in user_ids])
       return results
   ```

## 🔄 Maintenance Tasks

### Regular Maintenance

1. **Daily tasks**
   ```bash
   # Check service health
   sudo systemctl status telegram-bot

   # Monitor error rates
   sudo journalctl -u telegram-bot --since "1 day ago" | grep -c ERROR

   # Check disk usage
   df -h /opt/telegram-bot
   ```

2. **Weekly tasks**
   ```bash
   # Database maintenance
   psql -h localhost -U filemanager_prod -d filemanager_prod -c "VACUUM ANALYZE;"

   # Log rotation
   sudo logrotate -f /etc/logrotate.d/telegram-bot

   # Security updates
   sudo apt update && sudo apt upgrade
   ```

3. **Monthly tasks**
   ```bash
   # Full database backup
   python scripts/init_database.py --backup --database filemanager_prod

   # Clean old logs
   find /var/log/telegram-bot -name "*.log" -mtime +90 -delete

   # SSL certificate renewal
   sudo certbot renew
   ```

### Automated Maintenance

Create cron jobs for automated maintenance:

```bash
# Add to crontab
crontab -e

# Daily health check at 2 AM
0 2 * * * /opt/telegram-bot/scripts/health_check.sh

# Weekly database maintenance on Sunday at 3 AM
0 3 * * 0 /opt/telegram-bot/scripts/weekly_maintenance.sh

# Monthly backup on 1st of month at 4 AM
0 4 1 * * /opt/telegram-bot/scripts/monthly_backup.sh
```

---

## 🎯 Quick Reference

### Most Common Issues

1. **Bot not responding** → Check token validity and webhook configuration
2. **Database errors** → Verify connection parameters and permissions
3. **SSL issues** → Check certificate validity and nginx configuration
4. **Performance problems** → Monitor resource usage and optimize queries
5. **Security alerts** → Review access logs and validate IP restrictions

### Essential Commands

```bash
# Service management
sudo systemctl status telegram-bot
sudo systemctl restart telegram-bot
sudo journalctl -u telegram-bot -f

# Database operations
python scripts/init_database.py --environment production
psql -h localhost -U filemanager_prod -d filemanager_prod

# Webhook testing
curl -s "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo"
curl -X POST https://your-domain.com/webhook -H "Content-Type: application/json" -d '{"test": true}'

# SSL verification
openssl x509 -in /etc/ssl/certs/bot.crt -noout -dates
curl -v -I https://your-domain.com/webhook
```

### Emergency Contacts

- **Logs**: `/var/log/telegram-bot/`
- **Config**: `/opt/telegram-bot/.env`
- **Database**: `postgresql://filemanager_prod:pass@localhost/filemanager_prod`
- **Webhook**: `https://your-domain.com/webhook`

---

*This troubleshooting guide was last updated: {datetime.now().isoformat()}*