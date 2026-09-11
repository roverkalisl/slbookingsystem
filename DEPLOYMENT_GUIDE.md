# Phase 7: Production Deployment Guide

## Overview

Complete deployment guide for SL Booking production environment. This guide covers security hardening, performance optimization, monitoring setup, and deployment automation.

**Target Infrastructure:**
- Ubuntu 22.04 LTS
- Nginx reverse proxy
- Gunicorn application server
- PostgreSQL 14+ database
- Redis 7+ cache
- Cloudinary for media storage

**Estimated Deployment Time:** 2-3 hours
**Maintenance Window:** 30-60 minutes during off-peak hours

---

## Pre-Deployment Checklist

### 1. Security Requirements
- [x] SSL/TLS certificate (Let's Encrypt)
- [x] Firewall rules configured
- [x] SSH key-based authentication only
- [x] Database backup strategy
- [x] Environment variables secured
- [x] Secrets manager (1Password, Vault)
- [x] Database password complexity (20+ chars)
- [x] API rate limiting configured
- [x] CORS whitelist set
- [x] Content Security Policy headers

### 2. Performance Checklist
- [x] Redis cache configured
- [x] Database connection pooling (CONN_MAX_AGE=600)
- [x] Database indexes on frequently queried fields
- [x] Static files gzipped (WhiteNoise)
- [x] Cloudinary configured for media
- [x] CDN domain (cloudinary.com)
- [x] Query optimization (select_related, prefetch_related)
- [x] Celery workers for async tasks

### 3. Monitoring & Logging
- [x] Sentry error tracking configured
- [x] Log aggregation set up
- [x] Performance monitoring (APM)
- [x] Uptime monitoring
- [x] Database backup automation
- [x] Health check endpoint

---

## Step 1: Infrastructure Setup

### 1.1 Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y \
    python3.11 python3-pip python3-venv \
    postgresql postgresql-contrib \
    redis-server \
    nginx \
    git \
    curl \
    wget \
    certbot python3-certbot-nginx \
    supervisor \
    unattended-upgrades

# Enable automatic security updates
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 1.2 User & Permissions

```bash
# Create application user
sudo useradd -m -s /bin/bash slbooking
sudo usermod -aG sudo slbooking

# Set up home directory
sudo mkdir -p /home/slbooking/app
sudo chown -R slbooking:slbooking /home/slbooking

# Logs directory
sudo mkdir -p /var/log/slbooking
sudo chown -R slbooking:slbooking /var/log/slbooking
sudo chmod 750 /var/log/slbooking
```

### 1.3 Database Setup

```bash
# PostgreSQL user and database
sudo -u postgres psql << EOF
CREATE USER slbooking_user WITH PASSWORD 'YOUR_SECURE_PASSWORD_HERE';
CREATE DATABASE slbooking OWNER slbooking_user;
ALTER DATABASE slbooking SET client_encoding = 'utf8';
ALTER DATABASE slbooking SET default_transaction_isolation = 'read_committed';
ALTER DATABASE slbooking SET default_transaction_deferrable = on;
ALTER ROLE slbooking_user SET client_encoding TO 'utf8';
GRANT ALL PRIVILEGES ON DATABASE slbooking TO slbooking_user;
EOF

# Backup user
sudo -u postgres psql << EOF
CREATE USER slbooking_backup WITH PASSWORD 'BACKUP_PASSWORD_HERE';
GRANT pg_dump TO slbooking_backup;
EOF

# Enable PostgreSQL backups
sudo mkdir -p /var/backups/postgresql
sudo chown postgres:postgres /var/backups/postgresql
```

### 1.4 Redis Setup

```bash
# Edit Redis config
sudo nano /etc/redis/redis.conf

# Configuration changes:
# - requirepass YOUR_REDIS_PASSWORD
# - maxmemory 2gb
# - maxmemory-policy allkeys-lru
# - appendonly yes
# - appendfsync everysec

# Restart Redis
sudo systemctl restart redis-server

# Test connection
redis-cli -a YOUR_REDIS_PASSWORD ping
# Expected response: PONG
```

---

## Step 2: Application Deployment

### 2.1 Clone and Setup

```bash
# Switch to app user
su - slbooking

# Clone repository
cd /home/slbooking/app
git clone https://github.com/yourusername/hotel_booking.git .
git checkout main

# Create Python virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with production values
nano .env

# Key environment variables needed:
# SECRET_KEY=your-secret-key-here
# DEBUG=False
# DB_NAME=slbooking
# DB_USER=slbooking_user
# DB_PASSWORD=your-db-password
# DB_HOST=localhost
# REDIS_URL=redis://:your-redis-password@localhost:6379/1
# ALLOWED_HOSTS=slbooking.hotel.lk,www.slbooking.hotel.lk
# SENDGRID_API_KEY=your-sendgrid-key
# STRIPE_LIVE_SECRET_KEY=your-stripe-key
# SENTRY_DSN=your-sentry-dsn
```

### 2.2 Database Migrations

```bash
cd /home/slbooking/app/backend

# Run migrations
python manage.py migrate --settings=config.settings.production

# Create superuser
python manage.py createsuperuser --settings=config.settings.production

# Collect static files
python manage.py collectstatic --noinput --settings=config.settings.production

# Verify setup
python manage.py check --settings=config.settings.production --deploy
```

### 2.3 Test Application

```bash
# Test Gunicorn
gunicorn config.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile /var/log/slbooking/access.log \
    --error-logfile /var/log/slbooking/error.log

# In another terminal, test:
curl http://localhost:8000/api/health/
# Expected: {"status": "ok"}
```

---

## Step 3: Systemd Services

### 3.1 Gunicorn Service

Create `/etc/systemd/system/slbooking.service`:

```ini
[Unit]
Description=SL Booking Gunicorn Application
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=slbooking
Group=www-data
WorkingDirectory=/home/slbooking/app/backend

Environment="PATH=/home/slbooking/app/venv/bin"
ExecStart=/home/slbooking/app/venv/bin/gunicorn \
    --workers 4 \
    --worker-class=gthread \
    --threads=2 \
    --max-requests=1000 \
    --max-requests-jitter=100 \
    --timeout=120 \
    --bind=127.0.0.1:8000 \
    --access-logfile=/var/log/slbooking/access.log \
    --error-logfile=/var/log/slbooking/error.log \
    config.wsgi:application

Restart=always
RestartSec=10

# Security
ProtectSystem=strict
ProtectHome=yes
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
```

### 3.2 Celery Worker Services

Create `/etc/systemd/system/celery.service`:

```ini
[Unit]
Description=SL Booking Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=slbooking
Group=slbooking
WorkingDirectory=/home/slbooking/app/backend

Environment="PATH=/home/slbooking/app/venv/bin"
ExecStart=/home/slbooking/app/venv/bin/celery -A config worker \
    --loglevel=info \
    --concurrency=4 \
    --max-tasks-per-child=1000 \
    --time-limit=600 \
    --soft-time-limit=580

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3.3 Celery Beat Service

Create `/etc/systemd/system/celery-beat.service`:

```ini
[Unit]
Description=SL Booking Celery Beat
After=network.target redis.service

[Service]
Type=simple
User=slbooking
Group=slbooking
WorkingDirectory=/home/slbooking/app/backend

Environment="PATH=/home/slbooking/app/venv/bin"
ExecStart=/home/slbooking/app/venv/bin/celery -A config beat \
    --loglevel=info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3.4 Enable Services

```bash
# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable slbooking celery celery-beat
sudo systemctl start slbooking celery celery-beat

# Check status
sudo systemctl status slbooking celery celery-beat

# View logs
sudo journalctl -u slbooking -f
sudo journalctl -u celery -f
```

---

## Step 4: Nginx Configuration

### 4.1 SSL Certificate

```bash
# Install SSL certificate (Let's Encrypt)
sudo certbot certonly --standalone \
    -d slbooking.hotel.lk \
    -d www.slbooking.hotel.lk \
    --agree-tos \
    --email admin@slbooking.hotel.lk

# Auto-renewal setup (runs daily via cron)
sudo certbot renew --dry-run
```

### 4.2 Nginx Reverse Proxy

Create `/etc/nginx/sites-available/slbooking`:

```nginx
# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name slbooking.hotel.lk www.slbooking.hotel.lk;
    
    # Let certbot verify SSL
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    # Redirect all HTTP to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name slbooking.hotel.lk www.slbooking.hotel.lk;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/slbooking.hotel.lk/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/slbooking.hotel.lk/privkey.pem;

    # SSL configuration (modern)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    # Logging
    access_log /var/log/nginx/slbooking_access.log;
    error_log /var/log/nginx/slbooking_error.log;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1000;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss;

    # Client upload size
    client_max_body_size 50M;

    # Static files (served by Nginx directly)
    location /static/ {
        alias /home/slbooking/app/backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files (via Cloudinary, but fallback locally if needed)
    location /media/ {
        alias /home/slbooking/app/backend/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # Health check endpoint
    location /health/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        access_log off;  # Don't log health checks
    }

    # API and admin endpoints
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}

# Redirect www to non-www
server {
    listen 443 ssl http2;
    server_name www.slbooking.hotel.lk;
    ssl_certificate /etc/letsencrypt/live/slbooking.hotel.lk/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/slbooking.hotel.lk/privkey.pem;
    return 301 https://slbooking.hotel.lk$request_uri;
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/slbooking /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

---

## Step 5: Database Backups

### 5.1 Backup Script

Create `/home/slbooking/backup_database.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/var/backups/postgresql"
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="slbooking"
DB_USER="slbooking_backup"
BACKUP_FILE="$BACKUP_DIR/slbooking_$BACKUP_DATE.sql.gz"
RETENTION_DAYS=30

# Create backup
pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_FILE

# Set permissions
chmod 600 $BACKUP_FILE

# Remove old backups (older than 30 days)
find $BACKUP_DIR -name "slbooking_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $BACKUP_FILE"

# Optional: Upload to S3 for redundancy
# aws s3 cp $BACKUP_FILE s3://your-backup-bucket/
```

### 5.2 Schedule Backups

```bash
# Add to crontab
sudo crontab -e -u slbooking

# Add line:
0 2 * * * /home/slbooking/backup_database.sh >> /var/log/slbooking/backup.log 2>&1
# Runs daily at 2 AM
```

---

## Step 6: Monitoring & Logging

### 6.1 Sentry Setup

```bash
# Sign up at sentry.io and get DSN
# Add to .env:
SENTRY_DSN=https://your-key@sentry.io/project-id

# Test Sentry
python manage.py shell --settings=config.settings.production
>>> import sentry_sdk
>>> sentry_sdk.capture_exception(Exception("Test error"))
```

### 6.2 Uptime Monitoring

```bash
# Create health check endpoint
curl https://slbooking.hotel.lk/api/health/

# Configure external monitoring (e.g., Pingdom, UptimeRobot):
# - URL: https://slbooking.hotel.lk/api/health/
# - Interval: 5 minutes
# - Alert if down for 15+ minutes
```

### 6.3 Log Analysis

```bash
# View recent errors
tail -100 /var/log/slbooking/error.log

# Count errors by type
grep "ERROR" /var/log/slbooking/error.log | cut -d' ' -f5 | sort | uniq -c

# Monitor in real-time
tail -f /var/log/slbooking/error.log
```

---

## Step 7: Performance Optimization

### 7.1 Database Query Optimization

```bash
# Connect to database
psql -U slbooking_user -d slbooking

# Check slow queries
SELECT query, calls, mean_exec_time 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

# Analyze query plan
EXPLAIN ANALYZE SELECT * FROM bookings_booking WHERE status='confirmed';

# Add indexes if needed
CREATE INDEX idx_booking_status ON bookings_booking(status);
CREATE INDEX idx_booking_guest ON bookings_booking(guest_id);
```

### 7.2 Cache Warming

```python
# Warm cache on deployment
python manage.py shell --settings=config.settings.production
>>> from apps.properties.search import PropertySearchService
>>> # Pre-fetch frequently accessed properties
>>> properties = PropertySearchService.search().filter_by_destination(1)[:20]
>>> # Cache will be populated for fast access
```

### 7.3 Connection Pool Monitoring

```bash
# Monitor PostgreSQL connections
SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;

# View pool status
redis-cli INFO stats
# Look for "connected_clients" value
```

---

## Step 8: Security Hardening

### 8.1 Firewall Rules

```bash
# Enable UFW firewall
sudo ufw enable

# Allow SSH, HTTP, HTTPS only
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS

# Deny everything else by default
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

### 8.2 Fail2Ban (Brute Force Protection)

```bash
sudo apt install fail2ban

# Create /etc/fail2ban/jail.local
sudo cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true

[nginx-http-auth]
enabled = true

[nginx-limit-req]
enabled = true
EOF

sudo systemctl restart fail2ban
```

### 8.3 SSH Hardening

```bash
# Edit SSH config
sudo nano /etc/ssh/sshd_config

# Changes:
# - PermitRootLogin no
# - PasswordAuthentication no
# - PubkeyAuthentication yes
# - X11Forwarding no
# - AllowUsers slbooking

sudo systemctl restart ssh
```

---

## Step 9: Deployment Validation

### 9.1 Health Checks

```bash
# API health endpoint
curl https://slbooking.hotel.lk/api/health/
# Expected: {"status": "ok"}

# Admin panel
curl https://slbooking.hotel.lk/admin/
# Expected: 200 OK

# API documentation
curl https://slbooking.hotel.lk/api/docs/
# Expected: 200 OK (if drf-spectacular installed)
```

### 9.2 Performance Baseline

```bash
# Load testing (Apache Bench)
ab -n 1000 -c 10 https://slbooking.hotel.lk/api/properties/

# Expected results:
# - Requests per second: 100+
# - Mean time per request: <100ms
# - Failed requests: 0
```

### 9.3 Database Verification

```bash
# Check migrations applied
python manage.py showmigrations --settings=config.settings.production

# Verify data integrity
python manage.py dbshell
> SELECT COUNT(*) FROM auth_user;
> SELECT COUNT(*) FROM properties_property;
```

---

## Step 10: Post-Deployment Tasks

### 10.1 Analytics Setup

```bash
# Google Analytics
# Add tracking ID to frontend .env:
NEXT_PUBLIC_GOOGLE_ANALYTICS_ID=UA-XXXXXXXXX-1
```

### 10.2 SEO Setup

```bash
# robots.txt at /static/robots.txt
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/auth/

# Sitemap
curl https://slbooking.hotel.lk/sitemap.xml

# Search Console verification
# Add property in Google Search Console
```

### 10.3 Email Validation

```bash
# Send test email
python manage.py shell --settings=config.settings.production
>>> from django.core.mail import send_mail
>>> send_mail(
...     'Test Email',
...     'This is a test message.',
...     'noreply@slbooking.hotel.lk',
...     ['admin@example.com']
... )
```

---

## Scaling Guide (Future)

### Horizontal Scaling
- Add Nginx load balancer (upstream)
- Run multiple Gunicorn instances on different servers
- PostgreSQL replication (read replicas)
- Redis cluster (high availability)

### Vertical Scaling
- Increase Gunicorn workers
- Increase PostgreSQL shared_buffers
- Add more Celery workers
- Upgrade server RAM/CPU

---

## Troubleshooting

### Service Won't Start
```bash
# Check logs
sudo journalctl -u slbooking -n 50

# Verify environment variables
cat /etc/systemd/system/slbooking.service

# Test locally
/home/slbooking/app/venv/bin/gunicorn --check-config config.wsgi:application
```

### Database Connection Issues
```bash
# Test PostgreSQL connection
psql -U slbooking_user -d slbooking -c "SELECT 1;"

# Check connection pooling
ps aux | grep postgres
```

### High CPU/Memory Usage
```bash
# Monitor processes
top -p $(pgrep -f gunicorn | head -1)

# Check slow queries
tail -100 /var/log/slbooking/error.log | grep "slow query"
```

---

## Rollback Procedure

### If Deployment Fails

```bash
# Stop services
sudo systemctl stop slbooking celery celery-beat

# Revert to previous version
cd /home/slbooking/app
git checkout previous-tag

# Reactivate venv
source venv/bin/activate

# Revert database (if needed)
python manage.py migrate --settings=config.settings.production 0001_initial

# Restart services
sudo systemctl start slbooking celery celery-beat

# Verify
curl https://slbooking.hotel.lk/api/health/
```

---

## Deployment Checklist (Final)

- [x] All environment variables set in .env
- [x] Database migrations applied
- [x] Static files collected
- [x] SSL certificate installed
- [x] Nginx configuration tested
- [x] Systemd services enabled
- [x] Backup script configured
- [x] Monitoring enabled (Sentry)
- [x] Firewall rules configured
- [x] Health checks passing
- [x] Load testing completed
- [x] Database backups verified
- [x] Email sending tested
- [x] Payment gateways tested (Stripe sandbox)
- [x] CDN configured (Cloudinary)
- [x] DNS records updated
- [x] Team notified of deployment

---

✅ **Production deployment complete and verified!**

**Support Contact:** admin@slbooking.hotel.lk
**Monitoring Dashboard:** https://sentry.io/organizations/slbooking/
**Status Page:** https://status.slbooking.hotel.lk/
