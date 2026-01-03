#!/bin/bash

# Script to fix DNS resolution issues on VPS
echo "Fixing DNS resolution issues on VPS..."

# Backup existing resolv.conf
sudo cp /etc/resolv.conf /etc/resolv.conf.backup

# Update resolv.conf with reliable DNS servers
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf > /dev/null
echo "nameserver 8.8.4.4" | sudo tee -a /etc/resolv.conf > /dev/null
echo "nameserver 1.1.1.1" | sudo tee -a /etc/resolv.conf > /dev/null
echo "nameserver 1.0.0.1" | sudo tee -a /etc/resolv.conf > /dev/null

echo "DNS resolution fixed. Current configuration:"
cat /etc/resolv.conf

# Test DNS resolution for all services used in the application
echo "Testing DNS resolution for application services..."
SERVICES=(
    "google.com"
    "api.telegram.org"
    "storage.yandexcloud.net"
    "tactically-healing-parrotfish.cloudpub.ru"  # Webhook URL host
)

for service in "${SERVICES[@]}"; do
    echo "Testing $service..."
    if nslookup "$service" > /dev/null 2>&1; then
        echo "✓ $service resolved successfully"
    else
        echo "✗ Failed to resolve $service"
    fi
done

# Check if systemd-resolved is running and configure it if needed
if systemctl is-active --quiet systemd-resolved; then
    echo "systemd-resolved is running. Configuring..."
    sudo systemctl stop systemd-resolved
    sudo systemctl disable systemd-resolved
    echo "Disabled systemd-resolved"
    
    # Create a symlink to the new resolv.conf
    sudo ln -sf /etc/resolv.conf /run/systemd/resolve/stub-resolv.conf
fi

# Ensure /etc/nsswitch.conf is properly configured
if [ -f /etc/nsswitch.conf ]; then
    echo "Checking /etc/nsswitch.conf..."
    if ! grep -q "hosts:.*files.*dns" /etc/nsswitch.conf; then
        sudo sed -i 's/hosts:.*/hosts: files dns/' /etc/nsswitch.conf
        echo "Updated /etc/nsswitch.conf"
    fi
fi

# Flush DNS cache if systemd-resolve is available
if command -v systemd-resolve &> /dev/null; then
    sudo systemd-resolve --flush-caches
    echo "Flushed DNS cache"
fi

# Final verification
echo "Final DNS resolution test..."
if nslookup api.telegram.org > /dev/null 2>&1; then
    echo "DNS resolution is working correctly!"
else
    echo "DNS resolution is still failing. Additional steps may be needed:"
    echo "1. Check if the VPS has proper network connectivity"
    echo "2. Verify firewall settings are not blocking DNS traffic (port 53)"
    echo "3. Check if the VPS provider has specific DNS requirements"
fi