#!/usr/bin/env bash
# ==============================================================================
# FocusGuard Updater & Service Reinstaller
# Pulls latest changes, syncs files, and restarts the FocusGuard appliance.
# ==============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}"
echo "╔═══════════════════════════════════════════════════════╗"
echo "║          FocusGuard System & Service Updater          ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[ERROR] This update script must be run as root.${NC}"
    echo "Please execute: sudo ./scripts/update.sh"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 1. Pull latest git code if git repo exists
if [[ -d "${SCRIPT_DIR}/.git" ]]; then
    echo -e "${GREEN}[*] Pulling latest updates from GitHub...${NC}"
    git -C "${SCRIPT_DIR}" pull origin main || {
        echo -e "${YELLOW}[!] Git pull encountered a warning. Continuing with local files...${NC}"
    }
fi

# 2. Stop running service during file update
echo -e "${GREEN}[*] Stopping active focusguard service...${NC}"
systemctl stop focusguard.service 2>/dev/null || true

# 3. Synchronize application files to /opt/focusguard
echo -e "${GREEN}[*] Updating application files in /opt/focusguard...${NC}"
mkdir -p /opt/focusguard
cp -r "${SCRIPT_DIR}/focusguard" /opt/focusguard/
cp -r "${SCRIPT_DIR}/bin" /opt/focusguard/
cp -r "${SCRIPT_DIR}/scripts" /opt/focusguard/
cp "${SCRIPT_DIR}/pyproject.toml" /opt/focusguard/

# Set safe readable permissions
chmod -R 755 /opt/focusguard

# 4. Refresh binaries in /usr/local/bin
echo -e "${GREEN}[*] Updating wrapper binaries in /usr/local/bin...${NC}"
ln -sf /opt/focusguard/bin/focusguard /usr/local/bin/focusguard
ln -sf /opt/focusguard/bin/focusguardd /usr/local/bin/focusguardd
chmod +x /usr/local/bin/focusguard
chmod +x /usr/local/bin/focusguardd
chmod +x /opt/focusguard/bin/focusguard
chmod +x /opt/focusguard/bin/focusguardd
chmod +x /opt/focusguard/scripts/*.sh

# 5. Ensure Python module lookup via .pth file and pip fallback
echo -e "${GREEN}[*] Configuring Python path for focusguard...${NC}"
for py_site in $(python3 -c "import site; print(' '.join(site.getsitepackages()))" 2>/dev/null || echo "/usr/local/lib/python3/dist-packages"); do
    if [[ -d "$py_site" && -w "$py_site" ]]; then
        echo "/opt/focusguard" > "${py_site}/focusguard.pth" 2>/dev/null || true
    fi
done
python3 -m pip install -e /opt/focusguard --break-system-packages --no-deps 2>/dev/null || true

# 6. Update and reload systemd unit
echo -e "${GREEN}[*] Updating systemd service unit...${NC}"
cp "${SCRIPT_DIR}/systemd/focusguard.service" /etc/systemd/system/focusguard.service
systemctl daemon-reload
systemctl enable focusguard.service
systemctl restart focusguard.service

sleep 1

# 7. Verification
echo -e "${GREEN}[*] Verifying service status...${NC}"
if systemctl is-active --quiet focusguard.service; then
    echo -e "${GREEN}${BOLD}[✓] FocusGuard service is ACTIVE and running!${NC}"
else
    echo -e "${RED}[✗] Service failed to start. Recent service logs:${NC}"
    journalctl -u focusguard.service -n 25 --no-pager
    exit 1
fi

echo ""
/usr/local/bin/focusguard doctor || true

echo -e "\n${CYAN}${BOLD}[✓] FocusGuard has been successfully updated and reinstalled!${NC}\n"
