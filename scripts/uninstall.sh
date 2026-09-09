#!/usr/bin/env bash
# ==============================================================================
# FocusGuard Uninstaller & Safe Rollback
# ==============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${YELLOW}${BOLD}FocusGuard Safe Uninstaller & Network Rollback${NC}"

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[ERROR] This uninstallation script must be run as root.${NC}"
    echo "Please execute: sudo ./uninstall.sh"
    exit 1
fi

echo -e "${GREEN}[*] Stopping FocusGuard background service...${NC}"
systemctl stop focusguard.service 2>/dev/null || true
systemctl disable focusguard.service 2>/dev/null || true

echo -e "${GREEN}[*] Removing systemd service unit...${NC}"
rm -f /etc/systemd/system/focusguard.service
systemctl daemon-reload

echo -e "${GREEN}[*] Removing binary executables and application files...${NC}"
rm -f /usr/local/bin/focusguard
rm -f /usr/local/bin/focusguardd
rm -rf /opt/focusguard

read -rp "Do you also wish to permanently delete saved state and logs in /var/lib/focusguard? [y/N]: " CONFIRM
if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}[*] Purging /var/lib/focusguard and /var/log/focusguard...${NC}"
    rm -rf /var/lib/focusguard
    rm -rf /var/log/focusguard
fi

rm -rf /run/focusguard

echo -e "${GREEN}${BOLD}[✓] FocusGuard has been completely removed from this server.${NC}"
echo -e "${YELLOW}[IMPORTANT] Remember to revert your home router's DNS settings back to your ISP or 1.1.1.1 if you changed them!${NC}"
