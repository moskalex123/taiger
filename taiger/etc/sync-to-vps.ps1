#!/usr/bin/env pwsh

# Script to sync local changes to VPS via Git and restart project
Write-Host "Syncing code to VPS..." -ForegroundColor Green

# Add all changes
git add .

# Check if there are changes to commit
$changes = git status --porcelain
if ([string]::IsNullOrEmpty($changes)) {
    Write-Host "No changes to commit." -ForegroundColor Yellow
} else {
    # Commit changes
    $commitMessage = "Sync changes - $(Get-Date)"
    git commit -m "$commitMessage"
    Write-Host "Committed changes with message: $commitMessage" -ForegroundColor Green
}

# Push to VPS
Write-Host "Pushing to VPS..." -ForegroundColor Green
git push vps main

if ($LASTEXITCODE -eq 0) {
    Write-Host "Code successfully synced to VPS!" -ForegroundColor Green
    
    # Deploy DNS fix script to VPS (convert line endings for Linux compatibility)
    Write-Host "Deploying DNS fix script to VPS..." -ForegroundColor Yellow
    scp fix-vps-dns.sh new_vps:/opt/taiger/
    
    # Fix DNS resolution issues on VPS before restarting
    Write-Host "Fixing DNS resolution issues on VPS..." -ForegroundColor Yellow
    ssh new_vps 'cd /opt/taiger && sed -i "s/\r$//" fix-vps-dns.sh && chmod +x fix-vps-dns.sh && sudo ./fix-vps-dns.sh'
    
    # Deploy nginx configuration and restart nginx
    Write-Host "Deploying nginx configuration and restarting nginx..." -ForegroundColor Yellow
    ssh new_vps 'cd /opt/taiger && sudo cp nginx.conf /etc/nginx/sites-available/taiger.conf && sudo nginx -t && sudo systemctl reload nginx'
    
    # Restart the project on VPS
    Write-Host "Restarting project on VPS..." -ForegroundColor Yellow
    ssh new_vps 'cd /opt/taiger && systemctl restart taiger-app 2>/dev/null || supervisorctl restart taiger-app 2>/dev/null || pkill -f "python.*main.py" 2>/dev/null; echo "Project restart attempted"'
    
    Write-Host "Project restart command sent to VPS!" -ForegroundColor Green
    Write-Host "NOTE: If the project is not set up as a service, you may need to manually start it on the VPS" -ForegroundColor Yellow
} else {
    Write-Host "Failed to sync to VPS!" -ForegroundColor Red
    exit 1
}