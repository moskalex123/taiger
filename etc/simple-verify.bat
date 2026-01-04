@echo off
echo === Verifying TMA page access ===

echo Checking TMA page from remote viewing server 109.206.236.60 to service 94.141.161.21...
ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@109.206.236.60 "curl -s -o /dev/null -w '%{http_code}' http://94.141.161.21:8000/"
if %errorlevel% equ 0 (
    echo ✅ Successfully accessed TMA page from remote viewing server
) else (
    echo ⚠️ Failed to access TMA page from remote viewing server
)

echo === Verification completed ===