# Git-Branch Based Deployment System

## Overview

This deployment system allows for safe development and testing without disrupting the production environment. It uses a Git-based workflow with separate branches for production and development.

## Branch Strategy

- **main**: Production branch - always stable and deployed
- **develop**: Development branch - for testing and development

## Deployment Scripts

### Core Deployment Scripts

#### `switch-to-develop.sh`
Switches production to use the develop branch for testing.

```bash
./switch-to-develop.sh
```

#### `switch-to-main.sh`
Switches back to the main branch (production).

```bash
./switch-to-main.sh
```

#### `deploy-to-production.sh`
Merges develop into main and deploys to production.

```bash
./deploy-to-production.sh
```

#### `rollback.sh`
Emergency rollback to previous version.

```bash
./rollback.sh
```

### Utility Scripts

#### `deployment-status.sh`
Shows current deployment status and branch synchronization.

```bash
./deployment-status.sh
```

#### `health-check.sh`
System health monitoring.

```bash
./health-check.sh
```

#### `pull-from-github.sh`
Pulls latest changes from GitHub.

```bash
./pull-from-github.sh [branch]
```

#### `push-to-github.sh`
Pushes changes to GitHub with confirmation.

```bash
./push-to-github.sh [branch]
```

#### `sync-with-github.sh`
Synchronizes all branches with GitHub.

```bash
./sync-with-github.sh
```

## Workflow

### Development Workflow

1. **Development on Local Machine**:
   ```bash
   # Work on develop branch locally
   git checkout develop
   # Make changes
   git add .
   git commit -m "Feature description"
   git push origin develop
   ```

2. **Test on VPS**:
   ```bash
   # Switch VPS to develop branch
   ./switch-to-develop.sh
   # Test changes
   ```

3. **Deploy to Production**:
   ```bash
   # When ready, deploy to production
   ./deploy-to-production.sh
   ```

4. **Rollback if Needed**:
   ```bash
   # Emergency rollback
   ./rollback.sh
   ```

### Daily Operations

#### Check Status
```bash
./deployment-status.sh
```

#### System Health
```bash
./health-check.sh
```

#### Sync with GitHub
```bash
./sync-with-github.sh
```

## Safety Features

- **Branch Protection**: Production always runs on main branch
- **Confirmation Prompts**: All destructive operations require confirmation
- **Rollback Capability**: Quick rollback to previous versions
- **Status Monitoring**: Real-time deployment status tracking
- **Health Monitoring**: System resource and service monitoring

## Best Practices

1. **Never commit directly to main** - Always use develop for testing
2. **Test thoroughly on develop** before deploying to production
3. **Use meaningful commit messages** for better tracking
4. **Monitor deployment status** regularly
5. **Keep sensitive files in .gitignore** (like README_for_AI.md)

## Troubleshooting

### Common Issues

1. **Branch out of sync**:
   ```bash
   ./sync-with-github.sh
   ```

2. **Service not running**:
   ```bash
   sudo systemctl restart taiger-api
   sudo systemctl restart taiger-worker
   ```

3. **Permission issues**:
   ```bash
   chmod +x *.sh
   ```

4. **Git conflicts**:
   ```bash
   git status
   git diff
   # Resolve conflicts manually
   git add .
   git commit
   ```

## Security

- SSH keys are used for GitHub authentication
- Sensitive files are excluded from repository
- All scripts have confirmation prompts for safety
- Regular health checks monitor system status

## Monitoring

The system provides comprehensive monitoring through:

- Deployment status tracking
- System health checks
- Service status monitoring
- Error log analysis
- Resource usage monitoring

This deployment system ensures safe, reliable, and efficient development and deployment workflows while maintaining production stability.