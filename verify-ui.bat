@echo off
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
)

echo === Verification completed ===