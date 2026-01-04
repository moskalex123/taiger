#!/bin/bash

# Automated script to set up passwordless SSH access to aux-vps
# Requires sshpass to be installed

echo "Automated setup for passwordless SSH access to aux-vps (92.246.141.38)"

# Check if sshpass is installed
if ! command -v sshpass &> /dev/null; then
    echo "sshpass is not installed. Installing..."
    apt-get update && apt-get install -y sshpass
fi

# Prompt for password
read -s -p "Enter password for root@92.246.141.38: " PASSWORD
echo ""

if [ -z "$PASSWORD" ]; then
    echo "Password is required. Exiting."
    exit 1
fi

# Copy SSH public key to aux-vps
echo "Copying SSH public key to aux-vps..."
sshpass -p "$PASSWORD" ssh-copy-id -o StrictHostKeyChecking=no root@92.246.141.38

if [ $? -eq 0 ]; then
    echo "SSH key copied successfully!"
    echo "You should now be able to connect without a password:"
    echo "ssh -F /opt/taiger/ssh_config aux-vps"
else
    echo "Failed to copy SSH key. Please check the password and try again."
fi