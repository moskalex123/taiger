#!/bin/bash

# Script to set up passwordless SSH access to aux-vps with extended timeout
# This script will prompt for the password and automatically set up key-based authentication

echo "Setting up passwordless SSH access to aux-vps (92.246.141.38)"
echo "Extended timeout for password input: 120 seconds"

# Prompt for password with extended timeout (120 seconds)
read -t 120 -s -p "Enter password for root@92.246.141.38: " PASSWORD
echo ""

if [ -z "$PASSWORD" ]; then
    echo "Password is required. Exiting."
    exit 1
fi

# Copy SSH public key to aux-vps with extended timeout settings
echo "Copying SSH public key to aux-vps..."
sshpass -p "$PASSWORD" ssh-copy-id -o StrictHostKeyChecking=no -o ConnectTimeout=60 root@92.246.141.38

if [ $? -eq 0 ]; then
    echo "SSH key copied successfully!"
    echo "Passwordless access to aux-vps is now configured."
    echo ""
    echo "You can now connect using:"
    echo "ssh -F /opt/taiger/ssh_config aux-vps"
    
    # Test the connection
    echo ""
    echo "Testing connection..."
    ssh -F /opt/taiger/ssh_config aux-vps "echo 'Connection successful!'"
else
    echo "Failed to copy SSH key. Please check the password and try again."
    exit 1
fi