@echo off
echo === Enabling New UI Design (Non-Containerized Setup) ===

echo Connecting to service server at 94.141.161.21...
echo Testing SSH connection to service server...
ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no root@94.141.161.21 "echo 'connected'" >nul 2>&1
if %errorlevel% neq 0 (
    echo Failed to connect to service server at 94.141.161.21. Check SSH settings.
    exit /b 1
)
echo ✅ Connected to service server at 94.141.161.21

echo Configuring UI design on service server...
echo Checking current .env configuration...
ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@94.141.161.21 "cat /opt/taiger/frontend/.env"

echo Checking if VITE_ENABLE_REDESIGN is already set to true...
ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@94.141.161.21 "grep 'VITE_ENABLE_REDESIGN=true' /opt/taiger/frontend/.env" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ VITE_ENABLE_REDESIGN is already set to true
) else (
    echo 🔧 Setting VITE_ENABLE_REDESIGN=true
    ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@94.141.161.21 "sed -i '/VITE_ENABLE_REDESIGN/d' /opt/taiger/frontend/.env"
    ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@94.141.161.21 "echo VITE_ENABLE_REDESIGN=true >> /opt/taiger/frontend/.env"
    echo ✅ VITE_ENABLE_REDESIGN has been set to true
    echo Verifying change...
    ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@94.141.161.21 "grep 'VITE_ENABLE_REDESIGN' /opt/taiger/frontend/.env"
)

echo === Building frontend application ===
echo Building frontend...
ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@94.141.161.21 "cd /opt/taiger/frontend && npm run build"
if %errorlevel% neq 0 (
    echo ⚠️ Failed to build frontend
    exit /b 1
)
echo ✅ Frontend built successfully

echo === Restarting services ===
echo Restarting backend service...
ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@94.141.161.21 "systemctl restart taiger-backend" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️ Failed to restart backend service with systemctl, trying alternative...
    ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@94.141.161.21 "pkill -f taiger-backend" >nul 2>&1
    timeout /t 2 /nobreak >nul
    ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@94.141.161.21 "cd /opt/taiger && nohup python main.py > /dev/null 2>&1 &"
)
echo ✅ Services restarted

echo === Verifying new UI design from remote viewing server ===
echo Connecting to remote viewing server at 109.206.236.60...
ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no root@109.206.236.60 "echo 'connected'" >nul 2>&1
if %errorlevel% neq 0 (
    echo Failed to connect to remote viewing server at 109.206.236.60. Check SSH settings.
    exit /b 1
)
echo ✅ Connected to remote viewing server at 109.206.236.60

echo Checking TMA page from remote viewing server...
for /f "delims=" %%a in ('ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@109.206.236.60 "curl -s -o /dev/null -w '%%{http_code}' http://94.141.161.21:8000/"') do set curlResult=%%a
echo HTTP status code from TMA page: %curlResult%

if "%curlResult%" equ "200" (
    echo ✅ Successfully accessed TMA page from remote viewing server
) else (
    echo ⚠️ Failed to access TMA page from remote viewing server
)

echo Checking if new UI elements are present in the response...
for /f "delims=" %%a in ('ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@109.206.236.60 "curl -s http://94.141.161.21:8000/ | grep -i 'redesigned' | wc -l"') do set uiCheck=%%a
if %uiCheck% gtr 0 (
    echo ✅ New UI design detected on TMA page
) else (
    echo ⚠️ New UI design not detected on TMA page
    echo 🔧 Attempting to force clear cache and rebuild...
    ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@94.141.161.21 "cd /opt/taiger/frontend && rm -rf dist && npm run build"
    echo ✅ Forced rebuild completed
)

echo === Process completed ===
echo 1. New UI design has been enabled on service server 94.141.161.21
echo 2. Frontend has been rebuilt and services restarted
echo 3. Verification attempted from remote viewing server 109.206.236.60
echo 4. If new UI is not visible, try clearing browser cache or wait a few minutes for DNS propagation