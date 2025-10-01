# FileManager Telegram Bot - Deployment Guide

## 🚀 Quick Start

1. **Connect your repository** to Render
2. **Set environment variables** in Render dashboard
3. **Deploy** automatically

## 📋 Prerequisites

- Telegram Bot Token from [@BotFather](https://t.me/botfather)
- Render account
- Git repository with this codebase

## 🔧 Environment Variables Setup

### Required Secrets (Set in Render Dashboard)

Navigate to your Render service → **Environment** → **Secret Files**

| Variable | Description | Example |
|----------|-------------|---------|
| `bot-token` | Your Telegram bot token | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `postgres-password` | PostgreSQL password | `your-secure-password` |

### Optional Environment Variables

Add these in **Environment Variables** section:

```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
ADMIN_USER_IDS=123456789,987654321
MAX_FILE_SIZE=52428800
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW=60
```

## 🏗️ Deployment Steps

### 1. Connect Repository

1. Log into [Render Dashboard](https://dashboard.render.com)
2. Click **New** → **Blueprint**
3. Connect your Git repository
4. Select **render.yaml** as configuration file

### 2. Configure Services

The `render.yaml` defines three services:

- **filemanager-bot**: Main application service
- **filemanager-postgres**: PostgreSQL database
- **filemanager-redis**: Redis cache

### 3. Set Environment Variables

#### Bot Token (Secret)
- **Key**: `bot-token`
- **Value**: Your bot token from BotFather

#### Database Password (Secret)
- **Key**: `postgres-password`
- **Value**: Secure random password

#### Additional Variables (Optional)
```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
ADMIN_USER_IDS=your_telegram_user_id
```

### 4. Deploy

1. Click **Apply** to create services
2. Wait for deployment to complete
3. Check service logs for any issues

## 🔍 Health Checks

The deployment includes comprehensive health monitoring:

- **Basic Health**: `https://your-service.render.com/health`
- **Detailed Health**: `https://your-service.render.com/health/detailed`
- **Metrics**: `https://your-service.render.com/metrics`
- **Readiness**: `https://your-service.render.com/ready`
- **Liveness**: `https://your-service.render.com/live`

## 📊 Monitoring

### Logs

- **Application Logs**: Available in Render dashboard
- **Database Logs**: PostgreSQL service logs
- **Redis Logs**: Redis service logs

### Metrics

Prometheus-style metrics available at `/metrics` endpoint:

```
filemanager_bot_uptime_seconds 123.45
filemanager_bot_status{status="healthy"} 1
filemanager_bot_cpu_percent 15.2
filemanager_bot_memory_percent 67.8
```

### Alerts

Pre-configured alerts for:
- High CPU usage (>80%)
- High memory usage (>85%)
- Database connection failures

## 🛠️ Troubleshooting

### Common Issues

#### Bot Not Responding
1. Check bot token is correct
2. Verify webhook URL is accessible
3. Check application logs for errors

#### Database Connection Issues
1. Verify PostgreSQL service is running
2. Check database credentials
3. Review connection logs

#### High Memory Usage
1. Monitor active connections
2. Check for memory leaks in logs
3. Consider scaling up service tier

### Debug Commands

```bash
# Check service status
curl https://your-service.render.com/health

# View detailed metrics
curl https://your-service.render.com/health/detailed

# Check database connectivity
curl https://your-service.render.com/metrics
```

### Log Analysis

Key log patterns to monitor:

```
# Successful startup
INFO - Bot started successfully
INFO - Database connected successfully
INFO - Redis connected successfully

# Errors to watch for
ERROR - Database connection failed
ERROR - Redis connection timeout
WARNING - High memory usage
```

## 🔒 Security

### Secrets Management
- Bot tokens stored as Render secrets
- Database passwords encrypted
- RSA keys generated automatically

### Network Security
- Redis accessible only within project
- PostgreSQL not publicly accessible
- Webhook validation enabled

### Best Practices
- Rotate secrets regularly
- Monitor access logs
- Use strong passwords
- Enable 2FA on Render account

## 📈 Scaling

### Automatic Scaling
- Configured for 1-5 instances
- Based on CPU/memory usage
- Automatic load balancing

### Manual Scaling
1. Go to service dashboard
2. Adjust **Instance Count**
3. Monitor performance impact

### Database Scaling
- High availability enabled
- Automatic failover
- Point-in-time recovery

## 🔄 Updates and Rollbacks

### Deploying Updates
1. Push changes to repository
2. Render auto-deploys on push
3. Monitor deployment logs
4. Verify health checks pass

### Manual Deployment
```bash
# Trigger manual deploy via Render API
curl -X POST https://api.render.com/v1/services/{service-id}/deploys \
  -H "Authorization: Bearer {api-token}"
```

### Rollback
1. Go to service dashboard
2. Click **Deployments**
3. Select previous deployment
4. Click **Rollback**

## 💾 Backups

### Automatic Backups
- PostgreSQL: Daily at 2 AM UTC
- Retention: 30 days
- Point-in-time recovery enabled

### Manual Backup
```bash
# Create manual backup via Render dashboard
# Go to PostgreSQL service → Backups → Create Backup
```

## 🚨 Emergency Procedures

### Service Down
1. Check health endpoints
2. Review service logs
3. Check Render status page
4. Contact Render support if needed

### Data Recovery
1. Use point-in-time recovery
2. Restore from automated backups
3. Manual intervention if required

## 📞 Support

### Getting Help
1. Check this documentation
2. Review service logs
3. Check Render dashboard
4. Community forums
5. Render support

### Useful Links
- [Render Documentation](https://render.com/docs)
- [Render Status Page](https://status.render.com)
- [Render Community](https://community.render.com)

## 🔧 Advanced Configuration

### Custom Domains
Add to `render.yaml`:
```yaml
customDomains:
  - name: your-domain.com
    service: filemanager-bot
```

### SSL/TLS
- Automatic HTTPS via Render
- Custom certificates supported
- Security headers configured

### Performance Tuning
- Adjust instance sizes based on load
- Monitor resource usage
- Optimize database queries
- Implement caching strategies

## 📋 Checklist

- [ ] Bot token configured
- [ ] Database password set
- [ ] Environment variables added
- [ ] Repository connected
- [ ] Services deployed successfully
- [ ] Health checks passing
- [ ] Bot responding to messages
- [ ] Backups configured
- [ ] Monitoring alerts set up
- [ ] Documentation reviewed

---

**Deployment completed successfully!** 🎉

Your FileManager Telegram Bot is now running on Render with production-grade configuration including monitoring, backups, and scaling capabilities.