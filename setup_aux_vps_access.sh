#!/bin/bash

# Script to set up passwordless SSH access to aux-vps
# This script will guide you through setting up SSH key-based authentication

echo "Setting up passwordless SSH access to aux-vps (92.246.141.38)"

# Display the public key that needs to be added to the remote server
echo "Please add the following public key to ~/.ssh/authorized_keys on aux-vps:"
echo ""
cat ~/.ssh/id_rsa.pub
echo ""
echo "To do this manually:"
echo "1. Copy the above key"
echo "2. SSH to aux-vps with password: ssh root@92.246.141.38"
echo "3. Create .ssh directory if it doesn't exist: mkdir -p ~/.ssh"
echo "4. Append the key to authorized_keys: echo 'PASTE_KEY_HERE' >> ~/.ssh/authorized_keys"
echo "5. Set proper permissions: chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
echo ""
echo "After completing these steps, you should be able to connect without a password:"
echo "ssh -F /opt/taiger/ssh_config aux-vps"