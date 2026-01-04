# Local Development Setup Guide

This guide explains how to set up the taiger7 project with local PostgreSQL and Redis databases using native installation.

## Prerequisites

1. **PostgreSQL** - Download and install from [postgresql.org](https://www.postgresql.org/download/)
2. **Redis** - Download and install from [redis.io](https://redis.io/download/) or use [Memurai](https://www.memurai.com/) for Windows
3. **Python 3.11+**
4. **Node.js 24+** (for frontend)
5. **Git**

## Quick Start

### 1. Start System Services

**Option A: Using PowerShell (Windows)**
```powershell
.\start-local-db.ps1
```

**Option B: Manual Service Start**
```bash
# Start PostgreSQL
sudo systemctl start postgresql

# Start Redis
sudo systemctl start redis
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

> Tip: if you use nvm/asdf, run `nvm install && nvm use` (or equivalent) in the repo root. See [.nvmrc](../../.nvmrc) / [.node-version](../../.node-version).

### 4. Initialize Database
```bash
python init_db.py
alembic upgrade head
```

### 5. Start the Application

**Backend:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend (in a new terminal):**
```bash
cd frontend
npm run dev
```

## Environment Configuration

The `.env` file should be configured for your native installation:

```env
# Native Database Configuration
DB_USER=taiger_user
DB_PASSWORD=taiger_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=taiger_db

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

## Health Check

Once everything is running, you can check the health of all services:

```bash
curl http://localhost:8000/health
```

This will return the status of both PostgreSQL and Redis connections.

## Service URLs

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Database Management

### Connect to PostgreSQL
```bash
psql -U taiger_user -d taiger_db
```

### Connect to Redis
```bash
redis-cli
```

## Stopping Services

```bash
# Stop system services
sudo systemctl stop postgresql redis
```

## Troubleshooting

### Service Issues
1. Ensure PostgreSQL and Redis services are installed and running
2. Check if ports 5432 and 6379 are available
3. Try restarting the services

### Database Connection Issues
1. Wait a few seconds after starting services
2. Check service logs: `journalctl -u postgresql`
3. Verify environment variables in `.env`

### Redis Connection Issues
1. Check if Redis service is running: `systemctl status redis`
2. Test Redis connection: `redis-cli ping`

## Database Setup

If you need to set up the database and user manually:

### PostgreSQL Setup
```bash
# Connect as superuser
sudo -u postgres psql

# Create database and user
CREATE DATABASE taiger_db;
CREATE USER taiger_user WITH PASSWORD 'taiger_password' SUPERUSER CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE taiger_db TO taiger_user;
\q
```
