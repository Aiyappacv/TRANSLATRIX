# TRANSLATRIX PRO - Production Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Database Configuration](#database-configuration)
4. [Environment Variables](#environment-variables)
5. [Application Deployment](#application-deployment)
6. [Background Workers](#background-workers)
7. [Monitoring & Logging](#monitoring--logging)
8. [Security Hardening](#security-hardening)
9. [Backup & Recovery](#backup--recovery)
10. [Scaling](#scaling)

---

## Prerequisites

### Required Software
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Celery 5+
- Docker & Docker Compose (optional but recommended)
- Nginx (for reverse proxy)

### Cloud Services
- AWS S3 / Azure Blob Storage / MinIO (object storage)
- SAP S/4HANA system (optional)
- SMTP server for email notifications
- Monitoring tools (Prometheus, Grafana, Sentry)

---

## Infrastructure Setup

### Option 1: Docker Deployment (Recommended)

```bash
# Build Docker image
docker build -t translatrix-pro:latest .

# Run with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

### Option 2: Manual Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start application with Gunicorn
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --keep-alive 5 \
  --access-logfile - \
  --error-logfile -
```

---

## Database Configuration

### PostgreSQL Setup

```sql
-- Create database
CREATE DATABASE translatrix_pro;

-- Create user
CREATE USER translatrix_user WITH PASSWORD 'strong_password_here';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE translatrix_pro TO translatrix_user;

-- Enable required extensions
\c translatrix_pro
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

### Database Migrations

```bash
# Initialize Alembic (if not done)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

---

## Environment Variables

Create `.env` file in production:

```bash
# Application
APP_NAME=TRANSLATRIX PRO
APP_ENV=production
DEBUG=false
API_V1_PREFIX=/api/v1

# Security
SECRET_KEY=<64-char-random-string>
JWT_SECRET_KEY=<64-char-random-string>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/translatrix_pro
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Object Storage (AWS S3)
STORAGE_PROVIDER=s3
AWS_ACCESS_KEY_ID=<your-access-key>
AWS_SECRET_ACCESS_KEY=<your-secret-key>
AWS_REGION=us-east-1
S3_BUCKET_NAME=translatrix-files

# OCR Services
OCR_PRIMARY_PROVIDER=mistral
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=<optional>
AZURE_DOCUMENT_INTELLIGENCE_KEY=<optional>

# Translation
TRANSLATION_PROVIDER=openai
OPENAI_API_KEY=<your-openai-key>
OPENAI_MODEL=gpt-4-turbo-preview

# SAP S/4HANA
SAP_ENABLED=true
SAP_BASE_URL=https://your-sap-instance.com
SAP_CLIENT=100
SAP_USERNAME=<sap-user>
SAP_PASSWORD=<sap-password>

# Monitoring
LOG_LEVEL=INFO
SENTRY_DSN=<your-sentry-dsn>
PROMETHEUS_PORT=9090

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<email>
SMTP_PASSWORD=<password>
SMTP_FROM_EMAIL=noreply@translatrix.pro

# Super Admin
SUPER_ADMIN_EMAIL=admin@translatrix.pro
SUPER_ADMIN_PASSWORD=<strong-password>

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
```

---

## Application Deployment

### Systemd Service (Linux)

Create `/etc/systemd/system/translatrix.service`:

```ini
[Unit]
Description=TRANSLATRIX PRO API
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=translatrix
Group=translatrix
WorkingDirectory=/opt/translatrix-pro
Environment="PATH=/opt/translatrix-pro/venv/bin"
ExecStart=/opt/translatrix-pro/venv/bin/gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
sudo systemctl enable translatrix
sudo systemctl start translatrix
sudo systemctl status translatrix
```

---

## Background Workers

### Celery Workers

Start Celery workers:

```bash
# Main worker
celery -A app.workers.celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  --pool=prefork

# Beat scheduler (for periodic tasks)
celery -A app.workers.celery_app beat \
  --loglevel=info
```

### Systemd Service for Celery

Create `/etc/systemd/system/celery.service`:

```ini
[Unit]
Description=TRANSLATRIX Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=translatrix
Group=translatrix
WorkingDirectory=/opt/translatrix-pro
Environment="PATH=/opt/translatrix-pro/venv/bin"
ExecStart=/opt/translatrix-pro/venv/bin/celery -A app.workers.celery_app worker --detach
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Monitoring & Logging

### Prometheus Metrics

Configure Prometheus to scrape metrics:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'translatrix'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/v1/monitoring/metrics'
```

### Structured Logging

Logs are output in JSON format for easy parsing:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "app.modules.sap.service",
  "event": "sap_posting_successful",
  "entry_id": "uuid-here",
  "document_number": "SAP-12345"
}
```

### Sentry Integration

Errors are automatically reported to Sentry when `SENTRY_DSN` is configured.

---

## Security Hardening

### 1. Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

### 2. Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name api.translatrix.pro;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.translatrix.pro;

    ssl_certificate /etc/letsencrypt/live/api.translatrix.pro/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.translatrix.pro/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. SSL/TLS with Let's Encrypt

```bash
sudo certbot --nginx -d api.translatrix.pro
```

### 4. Rate Limiting

Rate limiting is built-in using Redis. Configure in `.env`:

```bash
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
```

---

## Backup & Recovery

### Database Backups

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR=/backups/postgres
DATE=$(date +%Y%m%d_%H%M%S)

pg_dump -U translatrix_user translatrix_pro | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -type f -mtime +30 -delete
```

### File Storage Backups

Use S3 versioning and lifecycle policies for object storage.

---

## Scaling

### Horizontal Scaling

1. **Load Balancer**: Use AWS ALB, Nginx, or HAProxy
2. **Multiple API Instances**: Run multiple Gunicorn/Uvicorn instances
3. **Database Read Replicas**: Use PostgreSQL replication
4. **Redis Cluster**: Use Redis Sentinel or Cluster mode

### Vertical Scaling

- Increase Gunicorn workers: `--workers $((2 * CPU_CORES + 1))`
- Optimize database connection pool
- Increase Redis memory

---

## Health Checks

### Endpoints

- **Basic Health**: `GET /health`
- **Detailed Health**: `GET /api/v1/monitoring/health/detailed`
- **Readiness**: `GET /ready`
- **Metrics**: `GET /api/v1/monitoring/metrics`

### Kubernetes Liveness & Readiness Probes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

---

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check PostgreSQL is running
   - Verify credentials in `.env`
   - Check firewall rules

2. **High Memory Usage**
   - Reduce Gunicorn workers
   - Optimize database queries
   - Check for memory leaks

3. **Slow API Response**
   - Enable query logging
   - Check database indexes
   - Review Celery task queues

### Logs Location

- Application logs: `/var/log/translatrix/app.log`
- Celery logs: `/var/log/translatrix/celery.log`
- Nginx logs: `/var/log/nginx/access.log`

---

## Support

For production support:
- Email: support@translatrix.pro
- Documentation: https://docs.translatrix.pro
- GitHub: https://github.com/translatrix/translatrix-pro

---

**Last Updated**: June 2024
**Version**: 1.0.0
