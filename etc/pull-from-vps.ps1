#!/usr/bin/env pwsh

# Script to pull code from VPS to local machine via Git
Write-Host "Pulling latest changes from VPS..." -ForegroundColor Green

# Fetch changes from VPS
git fetch vps

# Check if there are changes to merge
$localCommit = git rev-parse HEAD
$remoteCommit = git rev-parse vps/main

if ($localCommit -eq $remoteCommit) {
    Write-Host "Already up to date." -ForegroundColor Yellow
} else {
    # Pull changes
    git pull vps main
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Successfully pulled changes from VPS!" -ForegroundColor Green
    } else {
        Write-Host "Failed to pull changes from VPS!" -ForegroundColor Red
        exit 1
    }
}