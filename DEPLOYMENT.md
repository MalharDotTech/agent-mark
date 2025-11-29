# 🚀 Deployment Guide

Production deployment guide for the Meta Ads Analytics Dashboard system.

## 🎯 Deployment Options

### Option 1: Single Server Deployment (Recommended)

**Architecture:**
```
[Load Balancer] → [Server] → [FastAPI + Marimo + SQLite]
```

**Pros:**
- Simple setup and maintenance
- SQLite handles thousands of concurrent readers
- Single point of configuration

**Cons:**
- Single point of failure
- Limited to SQLite scaling constraints

### Option 2: Microservices Deployment

**Architecture:**
```
[Load Balancer] → [FastAPI Service] → [Database]
                → [Marimo Dashboards] → [Database]
```

**Pros:**
- Independent scaling of components
- Better fault isolation
- Can use PostgreSQL for higher concurrency

**Cons:**
- More complex setup and maintenance
- Network latency between services

## 🏗️ Single Server Setup

### Prerequisites

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.13 python3.13-venv nginx supervisor

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 1. Application Setup

```bash
# Create application user
sudo useradd -m -s /bin/bash metaads
sudo su - metaads

# Clone and setup application
git clone <repository> meta-ads-analytics
cd meta-ads-analytics

# Install dependencies and setup
uv sync
uv run python scripts/setup_system.py

# Configure environment
cp .env.example .env
# Edit .env with production values
```

### 2. Database Setup

```bash
# Initialize production database
uv run python scripts/init_database.py

# Set proper permissions
chmod 644 data/meta_ads.db
chown metaads:metaads data/meta_ads.db
```

### 3. Service Configuration

**FastAPI Service** (`/etc/supervisor/conf.d/metaads-api.conf`):
```ini
[program:metaads-api]
command=/home/metaads/meta-ads-analytics/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
directory=/home/metaads/meta-ads-analytics
user=metaads
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/metaads-api.log
environment=PATH="/home/metaads/meta-ads-analytics/.venv/bin"
```

**Marimo Dashboard** (`/etc/supervisor/conf.d/metaads-dashboard.conf`):
```ini
[program:metaads-dashboard]
command=/home/metaads/meta-ads-analytics/.venv/bin/marimo run notebooks/index.py --host 0.0.0.0 --port 2718
directory=/home/metaads/meta-ads-analytics
user=metaads
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/metaads-dashboard.log
environment=PATH="/home/metaads/meta-ads-analytics/.venv/bin"
```

### 4. Nginx Configuration

**Main Config** (`/etc/nginx/sites-available/metaads`):
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Dashboard (main interface)
    location / {
        proxy_pass http://127.0.0.1:2718;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for Marimo
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # API endpoints
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000;
    }
    
    # Static files (if needed)
    location /static/ {
        alias /home/metaads/meta-ads-analytics/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 5. SSL Configuration (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 6. Start Services

```bash
# Enable and start services
sudo systemctl enable supervisor
sudo systemctl start supervisor

# Reload supervisor configuration
sudo supervisorctl reread
sudo supervisorctl update

# Start applications
sudo supervisorctl start metaads-api
sudo supervisorctl start metaads-dashboard

# Enable and start nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

## 🔧 Environment Configuration

### Production Environment Variables

```bash
# .env file
# Meta API Configuration
META_ACCESS_TOKENS=token1,token2,token3,token4
META_API_VERSION=v23.0

# Database Configuration
SQLITE_DB_PATH=/home/metaads/meta-ads-analytics/data/meta_ads.db

# Application Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false

# Security
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Rate Limiting
MAX_CONCURRENT_REQUESTS=10
BASE_BACKOFF_SECONDS=2
MAX_BACKOFF_SECONDS=300

# Dashboard Configuration
MARIMO_HOST=0.0.0.0
MARIMO_PORT=2718
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
```

## 📊 Monitoring and Logging

### Log Configuration

**Application Logs:**
```bash
# API logs
tail -f /var/log/metaads-api.log

# Dashboard logs  
tail -f /var/log/metaads-dashboard.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

**Log Rotation** (`/etc/logrotate.d/metaads`):
```
/var/log/metaads-*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 metaads metaads
    postrotate
        supervisorctl restart metaads-api metaads-dashboard
    endscript
}
```

### Health Monitoring

**Health Check Script** (`scripts/health_check.py`):
```python
#!/usr/bin/env python3
import requests
import sys

def check_health():
    try:
        # Check API health
        api_response = requests.get('http://localhost:8000/health', timeout=5)
        api_healthy = api_response.status_code == 200
        
        # Check dashboard
        dashboard_response = requests.get('http://localhost:2718', timeout=5)
        dashboard_healthy = dashboard_response.status_code == 200
        
        if api_healthy and dashboard_healthy:
            print("✅ All services healthy")
            return 0
        else:
            print("❌ Service health check failed")
            return 1
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(check_health())
```

**Cron Health Check:**
```bash
# Add to crontab
*/5 * * * * /home/metaads/meta-ads-analytics/scripts/health_check.py || echo "Health check failed" | mail -s "MetaAds Health Alert" admin@your-domain.com
```

## 🔒 Security Configuration

### Firewall Setup

```bash
# UFW configuration
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# Only allow local access to application ports
sudo ufw deny 8000
sudo ufw deny 2718
```

### Database Security

```bash
# Set proper file permissions
chmod 600 /home/metaads/meta-ads-analytics/.env
chmod 644 /home/metaads/meta-ads-analytics/data/meta_ads.db
chown -R metaads:metaads /home/metaads/meta-ads-analytics/
```

### Application Security

**Rate Limiting** (in nginx):
```nginx
# Add to server block
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=dashboard:10m rate=5r/s;

location /api/ {
    limit_req zone=api burst=20 nodelay;
    # ... rest of config
}

location / {
    limit_req zone=dashboard burst=10 nodelay;
    # ... rest of config
}
```

## 📈 Performance Optimization

### Database Optimization

```sql
-- Enable performance optimizations
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
PRAGMA temp_store=memory;
PRAGMA mmap_size=268435456; -- 256MB
```

### Application Optimization

**FastAPI Configuration:**
```python
# app/main.py
app = FastAPI(
    title="Meta Ads Analytics API",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# Add middleware for production
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

**Nginx Optimization:**
```nginx
# Add to server block
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

# Enable caching
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## 🔄 Backup and Recovery

### Database Backup

**Backup Script** (`scripts/backup_database.py`):
```python
#!/usr/bin/env python3
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

def backup_database():
    db_path = Path("data/meta_ads.db")
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"meta_ads_backup_{timestamp}.db"
    
    # Create backup
    shutil.copy2(db_path, backup_path)
    
    # Compress backup
    import gzip
    with open(backup_path, 'rb') as f_in:
        with gzip.open(f"{backup_path}.gz", 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    backup_path.unlink()  # Remove uncompressed backup
    print(f"✅ Database backed up to {backup_path}.gz")

if __name__ == "__main__":
    backup_database()
```

**Automated Backups:**
```bash
# Add to crontab
0 2 * * * /home/metaads/meta-ads-analytics/scripts/backup_database.py
0 2 * * 0 find /home/metaads/meta-ads-analytics/backups -name "*.gz" -mtime +30 -delete
```

### Recovery Procedure

```bash
# Stop services
sudo supervisorctl stop metaads-api metaads-dashboard

# Restore database
gunzip -c backups/meta_ads_backup_YYYYMMDD_HHMMSS.db.gz > data/meta_ads.db

# Set permissions
chown metaads:metaads data/meta_ads.db
chmod 644 data/meta_ads.db

# Start services
sudo supervisorctl start metaads-api metaads-dashboard
```

## 🔧 Maintenance

### Regular Maintenance Tasks

**Weekly:**
```bash
# Update dashboards
sudo -u metaads bash -c "cd /home/metaads/meta-ads-analytics && uv run python scripts/generate_dashboards.py"

# Check disk space
df -h /home/metaads/meta-ads-analytics/

# Review logs
sudo supervisorctl tail -f metaads-api
```

**Monthly:**
```bash
# Update dependencies
sudo -u metaads bash -c "cd /home/metaads/meta-ads-analytics && uv sync --upgrade"

# Restart services
sudo supervisorctl restart metaads-api metaads-dashboard

# Clean old logs
sudo logrotate -f /etc/logrotate.d/metaads
```

### Troubleshooting

**Common Issues:**

| Issue | Diagnosis | Solution |
|-------|-----------|----------|
| Dashboard not loading | Check Marimo service | `sudo supervisorctl restart metaads-dashboard` |
| API errors | Check FastAPI logs | `sudo supervisorctl tail metaads-api` |
| Database locked | Check SQLite connections | Restart both services |
| High memory usage | Check process stats | `htop`, consider adding swap |

**Debug Commands:**
```bash
# Check service status
sudo supervisorctl status

# Check port usage
sudo netstat -tlnp | grep -E ':(8000|2718)'

# Check application health
curl http://localhost:8000/health
curl http://localhost:2718

# Check database
sqlite3 data/meta_ads.db ".tables"
```

## 📞 Support

### Monitoring Alerts

Set up monitoring for:
- Service availability (API and dashboard)
- Database size and performance
- Disk space usage
- Memory and CPU usage
- SSL certificate expiration

### Log Analysis

Use tools like:
- **Logwatch** for daily log summaries
- **Fail2ban** for security monitoring
- **Grafana + Prometheus** for advanced monitoring

### Backup Verification

Regularly test backup restoration:
```bash
# Test backup integrity
gunzip -t backups/meta_ads_backup_latest.db.gz

# Test restoration in staging environment
# ... restoration commands ...
```