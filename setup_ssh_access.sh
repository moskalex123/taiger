#!/bin/bash

# Script to set up passwordless SSH access to 109.206.236.60

# Variables
REMOTE_HOST="109.206.236.60"
REMOTE_USER="root"
PUBLIC_KEY="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC2T4m1tGhbk1/CA6+cCcVPoHL4QPk6PTKk/FJ6vN4d32YFtj8MRg+5ZDN3Gg171ib4o44sHYdae5I++eB+xMBSTC+JZpoMwqjUr0i+/gVE+g01CoBCGAK9klxrd9KdElVDfqedbTFrXFJ2XsMy5egPbcaIUstwnXA4HhFxCN+g4WvOwv+DroWdKAAUTecMN1wZ5UI1G6sf6cjRB78IodN2yeeF8zJW4kBaPQD2hkUQrUG9gL98hZ5CyTqFoIwFMGjckUgkSkXi/yIno4Adx46NXhxxcDtYG6Q/M44hzqOd5z4fyRCTa4mfHBRN0PG+trDFu8KfbzcZtRK5jtchoWV2N0FL7MJc88NkBk+hW11fJh1COc2ztMoF9CJ6lU8D2+np5SrHUpEly95nVjECk0nFXndcEtebGJaKkMj7EJUIJYKDYeGmIIisVwF0p9GKUz+2Ku/fig0ImkECFP7OI4f4TGeRvPU2lkQ+2jCkUlqf3Brvx39sxQIN4tV2E//i+HMeleK7w8WWGmG/8T+dusb8++A28N6xFGUnTsLTlYzNe5BFdA+SbHe7nzmZiktyBhzxU8CW4TlReXDBpVQhk64wy3e/dpOZc1xWIQD60wQEMt4zd3cUfQMPy8UqBigbm9k049Bkj1zN7sS5EzU3Z0zBcc/MtW7j1EJCkCBocqrlEw== root@taiger.pro"

echo "Setting up passwordless SSH access to $REMOTE_HOST"

# Create .ssh directory if it doesn't exist
ssh -o StrictHostKeyChecking=no $REMOTE_USER@$REMOTE_HOST "mkdir -p ~/.ssh"

# Add public key to authorized_keys
ssh -o StrictHostKeyChecking=no $REMOTE_USER@$REMOTE_HOST "echo '$PUBLIC_KEY' >> ~/.ssh/authorized_keys"

# Set proper permissions
ssh -o StrictHostKeyChecking=no $REMOTE_USER@$REMOTE_HOST "chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"

echo "Setup complete. You should now be able to SSH to $REMOTE_HOST without a password."#!/bin/bash

# Script to set up passwordless SSH access to 109.206.236.60

# Variables
REMOTE_HOST="109.206.236.60"
REMOTE_USER="root"
PUBLIC_KEY="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC2T4m1tGhbk1/CA6+cCcVPoHL4QPk6PTKk/FJ6vN4d32YFtj8MRg+5ZDN3Gg171ib4o44sHYdae5I++eB+xMBSTC+JZpoMwqjUr0i+/gVE+g01CoBCGAK9klxrd9KdElVDfqedbTFrXFJ2XsMy5egPbcaIUstwnXA4HhFxCN+g4WvOwv+DroWdKAAUTecMN1wZ5UI1G6sf6cjRB78IodN2yeeF8zJW4kBaPQD2hkUQrUG9gL98hZ5CyTqFoIwFMGjckUgkSkXi/yIno4Adx46NXhxxcDtYG6Q/M44hzqOd5z4fyRCTa4mfHBRN0PG+trDFu8KfbzcZtRK5jtchoWV2N0FL7MJc88NkBk+hW11fJh1COc2ztMoF9CJ6lU8D2+np5SrHUpEly95nVjECk0nFXndcEtebGJaKkMj7EJUIJYKDYeGmIIisVwF0p9GKUz+2Ku/fig0ImkECFP7OI4f4TGeRvPU2lkQ+2jCkUlqf3Brvx39sxQIN4tV2E//i+HMeleK7w8WWGmG/8T+dusb8++A28N6xFGUnTsLTlYzNe5BFdA+SbHe7nzmZiktyBhzxU8CW4TlReXDBpVQhk64wy3e/dpOZc1xWIQD60wQEMt4zd3cUfQMPy8UqBigbm9k049Bkj1zN7sS5EzU3Z0zBcc/MtW7j1EJCkCBocqrlEw== root@taiger.pro"

echo "Setting up passwordless SSH access to $REMOTE_HOST"

# Create .ssh directory if it doesn't exist
ssh -o StrictHostKeyChecking=no $REMOTE_USER@$REMOTE_HOST "mkdir -p ~/.ssh"

# Add public key to authorized_keys
ssh -o StrictHostKeyChecking=no $REMOTE_USER@$REMOTE_HOST "echo '$PUBLIC_KEY' >> ~/.ssh/authorized_keys"

# Set proper permissions
ssh -o StrictHostKeyChecking=no $REMOTE_USER@$REMOTE_HOST "chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"

echo "Setup complete. You should now be able to SSH to $REMOTE_HOST without a password."