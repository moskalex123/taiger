# Git Operations Guide

This directory contains all scripts for Git operations and deployment management for the Taiger project.

## 📁 Directory Structure

```
git/
├── pull-from-github.sh      # Pull changes from GitHub
├── push-to-github.sh        # Push changes to GitHub with confirmation
├── sync-with-github.sh      # Synchronize all branches with GitHub
├── deployment-status.sh     # Check deployment status
├── health-check.sh          # System health monitoring
└── README.md               # This file
```

## 🚀 Quick Start

### Basic Operations

#### Pull Changes from GitHub
```bash
./pull-from-github.sh [branch]
```
- Pulls latest changes from GitHub
- Optional branch parameter (defaults to current branch)

#### Push Changes to GitHub
```bash
./push-to-github.sh [branch]
```
- Pushes changes to GitHub with confirmation prompt
- Optional branch parameter (defaults to current branch)

#### Synchronize with GitHub
```bash
./sync-with-github.sh
```
- Fetches all changes from GitHub
- Shows status of all branches

### Deployment Operations

#### Check Deployment Status
```bash
./deployment-status.sh
```
Shows:
- Current active branch
- Branch synchronization status
- Service status (taiger-api, taiger-worker)
- Recent commits

#### System Health Check
```bash
./health-check.sh
```
Monitors:
- Disk usage
- Memory usage
- CPU load
- Service status
- Recent errors

## 🔄 Deployment Workflow

### 1. Development Workflow

```bash
# 1. Work on develop branch locally
git checkout develop
# Make changes
git add .
git commit -m "Feature description"
git push origin develop

# 2. Test on VPS
cd /opt/taiger
./switch-to-develop.sh
# Test changes

# 3. Deploy to production
./deploy-to-production.sh
```

### 2. Daily Operations

```bash
# Check deployment status
./deployment-status.sh

# System health check
./health-check.sh

# Sync with GitHub
./sync-with-github.sh
```

### 3. Emergency Operations

```bash
# Emergency rollback
./rollback.sh

# Switch back to production
./switch-to-main.sh
```

## 🛡️ Safety Features

- **Confirmation Prompts**: All destructive operations require confirmation
- **Branch Protection**: Production always runs on main branch
- **Rollback Capability**: Quick rollback to previous versions
- **Status Monitoring**: Real-time deployment status tracking
- **Health Monitoring**: System resource and service monitoring

## 📋 Best Practices

1. **Never commit directly to main** - Always use develop for testing
2. **Test thoroughly on develop** before deploying to production
3. **Use meaningful commit messages** for better tracking
4. **Monitor deployment status** regularly
5. **Keep sensitive files in .gitignore** (like README_for_AI.md)

## 🔧 Troubleshooting

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

## 📞 Support

For issues with Git operations or deployment scripts:
1. Check the health status: `./health-check.sh`
2. Check deployment status: `./deployment-status.sh`
3. Review system logs: `journalctl -u taiger-api`
4. Contact the development team

## 📝 Notes

- All scripts are executable and tested
- GitHub integration uses SSH keys for authentication
- Sensitive files are excluded from repository via .gitignore
- Regular monitoring ensures system stability