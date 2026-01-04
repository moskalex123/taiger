# Taiger Project Configuration

## Configuration Files Overview

This document explains the configuration file structure for the Taiger project.

### Main Configuration Files

1. **[.env](file:///opt/taiger/.env)** - Main configuration file containing all environment variables
2. **[.env.prod](file:///opt/taiger/.env.prod)** - Symlink to [.env](file:///opt/taiger/.env) for backward compatibility
3. **[.secrets.env](file:///opt/taiger/.secrets.env)** - Auxiliary service credentials (not used by main services)
4. **[.env.telegram.example](file:///opt/taiger/.env.telegram.example)** - Template for Telegram configuration

### File Usage

- **API Service**: Loads [.env](file:///opt/taiger/.env) via [start_api.sh](file:///opt/taiger/start_api.sh)
- **Manual Workers**: Load [.env](file:///opt/taiger/.env) via [start_worker_manual.sh](file:///opt/taiger/start_worker_manual.sh)
- **Other Services**: Should all use [.env](file:///opt/taiger/.env) as the single source of truth

### Configuration Guidelines

1. **Single Source of Truth**: All active configuration should be in [.env](file:///opt/taiger/.env)
2. **Secrets Management**: Only auxiliary service credentials should be in [.secrets.env](file:///opt/taiger/.secrets.env)
3. **Backward Compatibility**: [.env.prod](file:///opt/taiger/.env.prod) exists as a symlink for scripts that reference it
4. **Templates**: [.env.telegram.example](file:///opt/taiger/.env.telegram.example) provides a template for new deployments

### Database Connection

The database connection is configured with these environment variables:
- `DB_USER=taiger`
- `DB_PASSWORD=Pp969291`
- `DB_HOST=94.141.161.21`
- `DB_PORT=5433`
- `DB_NAME=taigerdb`

These settings are consistent across all services that use the main [.env](file:///opt/taiger/.env) file.

### Troubleshooting

If you encounter database connection issues:
1. Verify that [.env](file:///opt/taiger/.env) contains the correct database credentials
2. Ensure services are loading [.env](file:///opt/taiger/.env) and not another configuration file
3. Check that PostgreSQL is running and accepting connections on port 5433
4. Confirm that the `taiger` user has proper permissions on `taigerdb`

### Making Configuration Changes

1. Edit [.env](file:///opt/taiger/.env) with your changes
2. Restart services to pick up the new configuration
3. Test that all services are working correctly