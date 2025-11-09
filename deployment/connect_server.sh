#!/bin/bash

# SSH Connection Helper Script
# Update the variables below with your server details

# Server Configuration - UPDATE THESE VALUES
SERVER_IP="173.242.49.209"
SERVER_USER="root"
SSH_KEY_PATH="~/.ssh/id_rsa"  # Path to your SSH private key
SSH_PORT="22"

echo "🔌 Connecting to upgrade-studio-bot VPS server..."
echo "Server: $SERVER_USER@$SERVER_IP:$SSH_PORT"
echo

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Available commands after connection:${NC}"
echo "- Check services: sudo systemctl status upgrade-bot upgrade-api upgrade-admin"
echo "- View logs: sudo journalctl -u upgrade-bot -f"
echo "- Deploy updates: cd /opt/upgrade-studio-bot/deployment && sudo ./deploy.sh"
echo "- Health check: cd /opt/upgrade-studio-bot/deployment && ./health_check.sh"
echo

if [ -f "$SSH_KEY_PATH" ]; then
    echo -e "${GREEN}Connecting with SSH key...${NC}"
    ssh -i "$SSH_KEY_PATH" -p "$SSH_PORT" "$SERVER_USER@$SERVER_IP"
else
    echo -e "${GREEN}Connecting with password...${NC}"
    ssh -p "$SSH_PORT" "$SERVER_USER@$SERVER_IP"
fi