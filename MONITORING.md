# 📊 Monitoring Guide - GN Manager

## Overview

GN Manager includes comprehensive monitoring capabilities to enable proactive issue detection, performance tracking, and operational visibility.

## Components

### 1. Structured Logging

**Location**: `logging_config.py`

#### Features
- **JSON logs** in production for structured parsing
- **Console logs** in development for readability
- **Log rotation**: Daily rotation with 7-day retention (30 days for errors)
- **Separate error log**: `logs/error.log` for errors and above
- **Request tracing**: Optional request ID tracking

#### Log Files
- `logs/app.log` - All application logs (rotated daily)
- `logs/error.log` - Errors only (rotated daily, kept 30 days)

#### Configuration
Set log level via environment variable:
```bash
export LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

---

### 2. Health Check Endpoints

**Location**: `routes/health_routes.py`

#### Endpoints

##### `/health` - Liveness Probe
Basic health check - returns 200 if app is running.

```bash
curl http://localhost:5000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-28T00:00:00Z"
}
```

##### `/health/ready` - Readiness Probe  
Checks if app is ready to serve traffic (database connection OK).

```bash
curl http://localhost:5000/health/ready
```

Response:
```json
{
  "status": "ready",
  "timestamp": "2026-01-28T00:00:00Z",
  "checks": {
    "database": "connected"
  }
}
```

Returns 503 if not ready.

##### `/health/metrics` - Metrics
Basic application metrics.

```bash
curl http://localhost:5000/health/metrics
```

Response:
```json
{
  "timestamp": "2026-01-28T00:00:00Z",
  "uptime_seconds": 3600.5,
  "python_version": "3.12.0",
  "flask_debug": false,
  "database": {
    "size_bytes": 1048576,
    "size_mb": 1.0
  },
  "logs": {
    "directory": "/app/logs",
    "file_count": 5
  }
}
```

---

### 3. Error Tracking

**Location**: `error_handler.py`

#### Features
- **Structured error logging** with full context
- **Error categorization** (4xx vs 5xx)
- **Context capture**: User ID, IP, request details, stack traces
- **JSON API responses** for API endpoints
- **HTML error pages** for browser requests

#### Error Handlers
- `404 Not Found` - Logged as WARNING
- `403 Forbidden` - Logged as WARNING
- `500 Internal Server Error` - Logged as ERROR with full traceback
- `Unhandled exceptions` - Logged as CRITICAL with full context

---

### 4. Database Backups

**Location**: `scripts/backup_db.py`

#### Features
- **Compressed backups** (gzip) to save space
- **Retention policy**: Keep last 7 daily + 4 weekly backups
- **Backup verification**: Checks file size after creation
- **Detailed logging**: All operations logged to `scripts/backup.log`

#### Manual Backup
```bash
cd /path/to/gnmanager
python scripts/backup_db.py
```

#### Automated Backups with Cron
Add to crontab (`crontab -e`):

```cron
# Daily backup at 2 AM
0 2 * * * /path/to/gnmanager/scripts/backup_db.sh
```

#### Restore from Backup
```bash
# List available backups
ls -lh backups/

# Restore a backup (CAUTION: overwrites current database!)
gunzip -c backups/gnmanager_backup_20260128_020000.db.gz > gnmanager.db
```

---

## Integration with External Tools

### Sentry (Error Tracking)
To integrate Sentry for error tracking:

1. Install Sentry SDK:
```bash
pip install sentry-sdk[flask]
```

2. Add to `app.py`:
```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN'),
    integrations=[FlaskIntegration()],
    traces_sample_rate=0.1  # 10% of transactions
)
```

### Prometheus (Metrics)
To expose metrics for Prometheus:

1. Install prometheus-flask-exporter:
```bash
pip install prometheus-flask-exporter
```

2. Add to `app.py`:
```python
from prometheus_flask_exporter import PrometheusMetrics

metrics = PrometheusMetrics(app)
```

3. Metrics available at `/metrics`

---

## Monitoring Best Practices

### Development
- Use `DEBUG` log level
- Monitor console output
- Check `logs/app.log` for issues

### Production
- Use `INFO` or `WARNING` log level
- Set up log aggregation (ELK, Loki, etc.)
- Monitor `/health/ready` for availability
- Set up alerts on error rate spikes
- Review `logs/error.log` daily
- Verify backups are running

### Alerts to Configure
1. **Availability**: `/health/ready` returns non-200
2. **Error rate**: >10 errors/hour in `logs/error.log`
3. **Database size**: >90% of disk space
4. **Backup failures**: Check `scripts/backup.log`

---

## Troubleshooting

### No logs appearing
- Check `logs/` directory exists and is writable
- Verify `LOG_LEVEL` environment variable
- Check Flask app is calling `configure_logging(app)`

### Health endpoint returns 503
- Check database connection
- Verify `gnmanager.db` file exists and is accessible
- Check database file permissions

### Backup script fails
- Verify `gnmanager.db` path in script is correct
- Check disk space (`df -h`)
- Review `scripts/backup.log` for error details
- Verify `backups/` directory exists and is writable

---

## Log Format Examples

### Development (Console)
```
[2026-01-28 00:00:00,123] INFO in app: Application started
[2026-01-28 00:00:01,456] WARNING in auth: Failed login attempt for user@example.com
```

### Production (JSON)
```json
{
  "timestamp": "2026-01-28T00:00:00.123Z",
  "level": "INFO",
  "logger": "gnmanager",
  "message": "Application started",
  "module": "app",
  "function": "create_app",
  "line": 123
}
```

### Error with Context (JSON)
```json
{
  "timestamp": "2026-01-28T00:00:00.123Z",
  "level": "ERROR",
  "logger": "gnmanager",
  "message": "500 Internal Server Error: GET /event/123",
  "module": "error_handler",
  "function": "internal_error",
  "line": 67,
  "user_id": 42,
  "ip_address": "192.168.1.100",
  "exception": "ValueError('Invalid event ID')",
  "traceback": "..."
}
```

---

## Support

For issues or questions about monitoring:
- Check this guide first
- Review log files in `logs/`
- Enable `DEBUG` logging temporarily
- Contact system administrator
