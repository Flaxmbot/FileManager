# 🚀 Telegram Bot Setup Guide

This comprehensive guide will walk you through setting up your Telegram bot from scratch using the automated setup scripts and configuration templates.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [BotFather Setup](#botfather-setup)
4. [Environment Configuration](#environment-configuration)
5. [Database Setup](#database-setup)
6. [Webhook Configuration](#webhook-configuration)
7. [Security Setup](#security-setup)
8. [API Integration](#api-integration)
9. [Testing and Validation](#testing-and-validation)
10. [Deployment](#deployment)
11. [Troubleshooting](#troubleshooting)

## 🎯 Prerequisites

Before starting the setup process, ensure you have:

### System Requirements
- **Python 3.11+** - Download from [python.org](https://python.org)
- **PostgreSQL 13+** - Database server
- **Redis 6+** (optional) - For session storage and caching
- **Git** - Version control system

### Development Tools
- **pip** - Python package manager
- **virtualenv** - Virtual environment manager
- **OpenSSL** - For SSL certificate generation

### Production Requirements
- **Domain name** - For webhook configuration
- **SSL certificate** - Let's Encrypt recommended
- **Server/VPS** - Linux-based server recommended

## 🚀 Quick Start

If you're in a hurry, here's the fastest way to get started:

```bash
# 1. Clone and setup project
git clone <your-repo-url>
cd telegram-bot

# 2. Run automated BotFather setup
python scripts/setup_botfather.py

# 3. Setup database
python scripts/init_database.py --environment development

# 4. Install dependencies
pip install -r requirements.txt

# 5. Start the bot
python -m src.main
```

For production deployment, continue with the detailed setup below.

## 🤖 BotFather Setup

The BotFather setup automation script guides you through creating and configuring your Telegram bot.

### Automated Setup

```bash
# Run the interactive BotFather setup
python scripts/setup_botfather.py

# Or run with specific parameters
python scripts/setup_botfather.py --bot-name "My FileManager Bot" --bot-username "myfilemanagerbot"
```

### What the Script Does

1. **Generates secure encryption keys** (RSA-4096 + Fernet)
2. **Guides you through BotFather conversation**
3. **Creates bot commands configuration**
4. **Generates environment-specific .env files**
5. **Creates setup summary and next steps**

### Manual BotFather Setup

If you prefer manual setup:

1. **Open Telegram** and search for `@BotFather`
2. **Send `/newbot` command**
3. **Enter bot display name** (e.g., "My FileManager Bot")
4. **Enter bot username** (must end with "bot", e.g., "myfilemanagerbot")
5. **Save the bot token** from BotFather's response

### Bot Configuration Commands

After creating your bot, configure it with these commands:

```
/setname - Set display name
/setdescription - Set bot description
/setabout - Set about text
/setcommands - Upload commands file
/setmenubutton - Configure menu button
```

## 🌍 Environment Configuration

The setup creates three environment configurations:

### Development Environment
- **Database**: `filemanager_dev`
- **Debug mode**: Enabled
- **Logging**: Verbose (DEBUG level)
- **Rate limiting**: Relaxed
- **SSL validation**: Disabled

### Staging Environment
- **Database**: `filemanager_staging`
- **Debug mode**: Disabled
- **Logging**: Balanced (INFO level)
- **Rate limiting**: Moderate
- **SSL validation**: Enabled

### Production Environment
- **Database**: `filemanager_prod`
- **Debug mode**: Disabled
- **Logging**: Minimal (WARNING level)
- **Rate limiting**: Strict
- **SSL validation**: Required
- **Monitoring**: Enabled

### Environment Variables

Key configuration variables in your `.env` files:

```bash
# Bot Configuration
BOT_TOKEN=your_bot_token_here
BOT_WEBHOOK_URL=https://your-domain.com/webhook

# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database

# Security
SECRET_KEY=your-secret-key
ENCRYPTION_KEY=your-encryption-key
RSA_PRIVATE_KEY_PATH=keys/private.pem

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
MAX_FILE_SIZE=52428800

# Rate Limiting
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW=60
```

## 🗄️ Database Setup

Set up PostgreSQL databases for each environment:

### Automated Database Setup

```bash
# Setup development database
python scripts/init_database.py --environment development

# Setup staging database
python scripts/init_database.py --environment staging

# Setup production database
python scripts/init_database.py --environment production

# Interactive setup
python scripts/init_database.py --interactive
```

### Manual Database Setup

```sql
-- Create database user
CREATE USER filemanager_dev WITH PASSWORD 'dev_password';

-- Create database
CREATE DATABASE filemanager_dev OWNER filemanager_dev;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE filemanager_dev TO filemanager_dev;

-- Connect and run schema
\c filemanager_dev;
\i sql/schema.sql;
```

### Database Schema

The setup creates these tables:

- **`users`** - Telegram users and authentication
- **`devices`** - Registered Android devices
- **`user_sessions`** - Active user sessions
- **`file_operations`** - File operation logs
- **`audit_log`** - Security audit trail
- **`user_agreements`** - Legal compliance tracking
- **`compliance_audits`** - Compliance audit records

## 🔗 Webhook Configuration

Configure webhooks for production deployment:

### Automated Webhook Setup

```bash
# Setup webhook for production
python scripts/setup_webhook.py --environment production --domain your-domain.com

# Setup webhook for staging
python scripts/setup_webhook.py --environment staging --ssl selfsigned

# Interactive setup
python scripts/setup_webhook.py --interactive
```

### SSL Certificate Options

1. **Let's Encrypt** (Recommended for production)
   ```bash
   python scripts/setup_webhook.py --ssl letsencrypt --domain your-domain.com
   ```

2. **Self-signed** (For development/testing)
   ```bash
   python scripts/setup_webhook.py --ssl selfsigned --domain dev.localhost
   ```

3. **Custom certificate**
   ```bash
   # Place your certificate files in ssl/ directory
   # Then run webhook setup
   python scripts/setup_webhook.py --environment production
   ```

### Webhook Security Features

- **IP validation** - Only allows Telegram's IP ranges
- **SSL certificate validation** - Ensures secure connection
- **Request signature validation** - Validates webhook authenticity
- **Rate limiting** - Prevents abuse and spam
- **Tor exit node blocking** - Enhanced security

## 🔒 Security Setup

Production security configuration includes:

### SSL/TLS Configuration

```bash
# Generate self-signed certificate for development
openssl req -x509 -newkey rsa:4096 -keyout ssl/dev.key -out ssl/dev.crt -days 365 -nodes -subj "/CN=dev.localhost"

# For production, use Let's Encrypt
sudo certbot certonly --standalone -d your-domain.com
```

### Security Headers

The setup includes comprehensive security headers:

```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: "1; mode=block"
Strict-Transport-Security: max-age=63072000
```

### Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw allow 22     # SSH
sudo ufw allow 80     # HTTP
sudo ufw allow 443    # HTTPS
sudo ufw allow 5432   # PostgreSQL (restrict to specific IPs)

# Allow Telegram webhook IPs only
sudo ufw insert 1 allow from 149.154.160.0/20 to any port 443
sudo ufw insert 2 allow from 91.108.4.0/22 to any port 443
# ... add other Telegram IP ranges
```

## 🔌 API Integration

The API configuration provides enhanced features:

### Rate Limiting

```python
# Automatic rate limiting with token bucket algorithm
# Configurable requests per second/minute
# Exponential backoff on rate limit hits
```

### Retry Logic

```python
# Automatic retry on:
# - Rate limiting (429 errors)
# - Server errors (5xx)
# - Network timeouts
# - Connection errors
```

### Error Handling

```python
# Comprehensive error handling with:
# - Structured logging
# - Health monitoring
# - Graceful degradation
# - Alert notifications
```

## 🧪 Testing and Validation

### Test Your Setup

```bash
# 1. Test bot token
python -c "
import requests
response = requests.get(f'https://api.telegram.org/bot{YOUR_TOKEN}/getMe')
print(response.json())
"

# 2. Test database connection
python -c "
import asyncpg
import asyncio

async def test():
    conn = await asyncpg.connect('postgresql://user:pass@localhost/db')
    result = await conn.fetchval('SELECT version()')
    print(f'Connected to: {result}')
    await conn.close()

asyncio.run(test())
"

# 3. Test webhook endpoint
curl -X POST https://your-domain.com/webhook \
  -H 'Content-Type: application/json' \
  -d '{"test": true}'
```

### Health Checks

```bash
# Check bot health
curl https://your-domain.com/health

# Check database health
python scripts/health_check.py

# Check webhook status
python -c "
import requests
response = requests.get(f'https://api.telegram.org/bot{YOUR_TOKEN}/getWebhookInfo')
print(response.json())
"
```

## 🚢 Deployment

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build manually
docker build -t telegram-bot .
docker run -d --name telegram-bot \
  -e BOT_TOKEN=your_token \
  -e DATABASE_URL=your_db_url \
  telegram-bot
```

### Systemd Service

```bash
# Copy service file
sudo cp config/telegram-bot.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot

# Check status
sudo systemctl status telegram-bot
```

### Nginx Configuration

```bash
# Copy nginx configuration
sudo cp config/nginx_webhook.conf /etc/nginx/sites-available/telegram-bot

# Enable site
sudo ln -s /etc/nginx/sites-available/telegram-bot /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

## 🔧 Monitoring and Maintenance

### Log Management

```bash
# View application logs
sudo journalctl -u telegram-bot -f

# View nginx logs
sudo tail -f /var/log/nginx/telegram-bot-access.log

# View security logs
sudo tail -f /var/log/telegram-bot/security_*.jsonl
```

### Backup Strategy

```bash
# Create database backup
python scripts/init_database.py --backup --database filemanager_prod

# Restore from backup
python scripts/init_database.py --restore backup_file.sql --database filemanager_prod
```

### Updates and Maintenance

```bash
# Update application
git pull origin main
pip install -r requirements.txt
sudo systemctl restart telegram-bot

# Update database schema
python -m alembic upgrade head

# Rotate encryption keys
python scripts/rotate_keys.py
```

## 📊 Monitoring Dashboard

Set up monitoring with:

### Prometheus Metrics

```yaml
# Add to prometheus.yml
scrape_configs:
  - job_name: 'telegram-bot'
    static_configs:
      - targets: ['your-server:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboard

Key metrics to monitor:
- **Request rate** - API calls per second
- **Error rate** - Failed requests percentage
- **Response time** - Average response latency
- **Active users** - Currently authenticated users
- **Database connections** - Pool usage
- **File operations** - Upload/download counts

### Alerting Rules

```yaml
# Example alerting rules
groups:
  - name: telegram-bot
    rules:
      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning

      - alert: WebhookDown
        expr: up{job="telegram-bot"} == 0
        for: 2m
        labels:
          severity: critical
```

## 🔍 Troubleshooting

### Common Issues

#### Bot Not Responding
```bash
# Check bot token
python -c "
import requests
response = requests.get(f'https://api.telegram.org/bot{YOUR_TOKEN}/getMe')
print('Status:', response.status_code)
print('Response:', response.json())
"

# Check application logs
sudo journalctl -u telegram-bot --since today
```

#### Database Connection Issues
```bash
# Test database connection
python -c "
import asyncpg
import asyncio

async def test():
    try:
        conn = await asyncpg.connect('your_database_url')
        print('✅ Database connection successful')
        await conn.close()
    except Exception as e:
        print(f'❌ Connection failed: {e}')

asyncio.run(test())
"
```

#### Webhook Not Working
```bash
# Check webhook configuration
python -c "
import requests
response = requests.get(f'https://api.telegram.org/bot{YOUR_TOKEN}/getWebhookInfo')
print(response.json())
"

# Test webhook endpoint
curl -k -X POST https://your-domain.com/webhook \
  -H 'Content-Type: application/json' \
  -d '{"message": "test"}'
```

#### SSL Certificate Issues
```bash
# Check certificate validity
openssl x509 -in ssl/bot.crt -text -noout

# Test SSL connection
curl -v -I https://your-domain.com/webhook

# Check nginx SSL configuration
sudo nginx -T | grep -A 10 -B 10 ssl
```

### Debug Mode

Enable debug logging:

```bash
# Set debug environment variables
export LOG_LEVEL=DEBUG
export DEBUG=true

# Run with debug output
python -m src.main 2>&1 | tee debug.log
```

### Performance Issues

```bash
# Check system resources
htop
df -h
free -h

# Check database performance
python scripts/analyze_performance.py

# Check API rate limits
python scripts/check_rate_limits.py
```

## 📞 Support

### Getting Help

1. **Check the logs** - Most issues are visible in application logs
2. **Review troubleshooting guide** - See `TROUBLESHOOTING.md`
3. **Check existing issues** - Search GitHub issues
4. **Create new issue** - Provide detailed error information

### Emergency Contacts

For critical production issues:
- **Primary**: Check monitoring dashboard
- **Secondary**: Review application logs
- **Tertiary**: Check system resources and database

### Maintenance Windows

Schedule maintenance during low-traffic periods:
- **Weekly**: Security updates and log rotation
- **Monthly**: Database optimization and cleanup
- **Quarterly**: Dependency updates and testing

---

## 🎯 Next Steps

1. ✅ Complete the setup using this guide
2. ⬜ Test your bot in development environment
3. ⬜ Deploy to staging for testing
4. ⬜ Set up monitoring and alerting
5. ⬜ Deploy to production
6. ⬜ Set up backup and disaster recovery
7. ⬜ Configure log aggregation
8. ⬜ Set up SSL certificate auto-renewal

## 📚 Additional Resources

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [aiogram Documentation](https://docs.aiogram.dev/)
- [PostgreSQL Documentation](https://postgresql.org/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)

---

**Happy botting! 🤖**

*This setup guide was generated on: {datetime.now().isoformat()}*