# Development Setup

This document describes the current development setup for the Taiger application.

## Current Configuration

As per your instructions, the application is now running manually without systemd services:

- **Application**: Running manually via uvicorn
- **Port**: 8000
- **Process Management**: Manual (no systemd)
- **Nginx**: Proxying requests to port 8000

## Startup Process

To start the application in development mode:

```bash
# Stop any existing processes
/opt/taiger/stop_dev.sh

# Start the application
/opt/taiger/start_dev.sh
```

Or manually:

```bash
# Navigate to project directory
cd /opt/taiger

# Stop any existing processes
pkill -f "uvicorn.*main:app"

# Start the application
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/taiger-api.log 2>&1 &
```

## Stopping the Application

To stop the application:

```bash
/opt/taiger/stop_dev.sh
```

Or manually:

```bash
pkill -f "uvicorn.*main:app"
```

## Logs

Application logs are available at:
```
/tmp/taiger-api.log
```

To view logs in real-time:
```bash
tail -f /tmp/taiger-api.log
```

## Nginx Configuration

Nginx is configured to proxy requests to port 8000:
- Configuration file: `/etc/nginx/conf.d/taiger.conf`
- After any changes, restart Nginx: `sudo systemctl restart nginx`

## Verification

To verify the application is running correctly:

```bash
# Check local access
curl http://localhost:8000/api/health

# Check through Nginx
curl https://taiger.pro/api/health
```

## Important Notes

1. **No Systemd Services**: As requested, the application is not running as a systemd service
2. **Manual Process Management**: You have full control over the application process
3. **Development Mode**: This setup is intended for development and testing
4. **Port 8000**: The application must run on port 8000 for proper Nginx proxying

## Troubleshooting

### If you get 502 errors:
1. Check if the application is running: `pgrep -f "uvicorn.*main:app"`
2. Check application logs: `tail -f /tmp/taiger-api.log`
3. Verify Nginx configuration: `grep -n "8000" /etc/nginx/conf.d/taiger.conf`
4. Restart Nginx: `sudo systemctl restart nginx`

### If the application won't start:
1. Check for port conflicts: `netstat -tulnp | grep :8000`
2. Kill conflicting processes if needed
3. Check logs for error messages
4. Verify dependencies are installed

### If you need to restart everything:
```bash
# Stop application
/opt/taiger/stop_dev.sh

# Restart Nginx
sudo systemctl restart nginx

# Start application
/opt/taiger/start_dev.sh
```