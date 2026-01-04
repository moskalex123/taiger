# VPS Database Configuration Guide

This document describes the current setup using remote PostgreSQL and Redis databases on VPS.

## Current VPS Database Configuration

### PostgreSQL Database
- **Host**: `94.141.161.21` (VPS IP)
- **Port**: `5433` (external port, mapped from container)
- **Database**: `taigerdb`
- **User**: `taiger`
- **Password**: `Pp969291!`

### Redis Cache
- **Host**: `94.141.161.21` (VPS IP)
- **Port**: `6379` (external port, mapped from container)
- **Database**: `0` (default)

## Environment Configuration

The `.env` file has been updated with VPS database settings:

```env
# VPS Database Configuration
DB_USER=taiger
DB_PASSWORD=Pp969291!
DB_HOST=94.141.161.21
DB_PORT=5433
DB_NAME=taigerdb

# VPS Redis Configuration
REDIS_HOST=94.141.161.21
REDIS_PORT=6379
REDIS_DB=0
```

## Quick Start

1. **Start the Backend**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Start the Frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

## Health Check

Verify all services are running correctly:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-12T15:26:39.452042",
  "services": {
    "database": "healthy",
    "redis": "healthy"
  }
}
```

## Service URLs

- **Frontend**: http://localhost:3002/
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Migration Notes

- ✅ Successfully migrated from local Docker containers to VPS databases
- ✅ PostgreSQL connection working with credentials authentication
- ✅ Redis connection established and functional
- ✅ All background tasks and worker management operational
- ✅ Frontend-backend communication working properly

## Benefits of VPS Database Setup

1. **Persistent Data**: Data survives local development restarts
2. **Shared Access**: Multiple developers can work with the same dataset
3. **Production-like Environment**: Closer to real deployment scenario
4. **Centralized Management**: Single point for database administration
5. **Backup Strategy**: VPS-level backup and monitoring capabilities

## Troubleshooting

### Connection Issues
If you encounter connection problems:

1. Verify VPS database containers are running
2. Check firewall settings on VPS for ports 5433 and 6379
3. Confirm network connectivity to `94.141.161.21`
4. Verify credentials in `.env` file

### Performance Considerations
- Network latency may be slightly higher than local databases
- Monitor connection timeouts during high-load operations
- Consider connection pooling optimization if needed

---

**Date**: September 12, 2025
**Status**: ✅ Active and Operational