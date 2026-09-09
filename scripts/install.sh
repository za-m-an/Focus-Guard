#!/usr/bin/env bash
# ==============================================================================
# FocusGuard Installer for DietPi / Debian Linux
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
echo "║      FocusGuard DietPi Appliance Installer            ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 1. Require root execution
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[ERROR] This installation script must be run as root.${NC}"
    echo "Please execute: sudo ./install.sh"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo -e "${GREEN}[*] Source directory: ${SCRIPT_DIR}${NC}"

# 2. Check or install Python 3 (>= 3.10)
echo -e "${GREEN}[*] Checking Python environment...${NC}"
if ! command -v python3 &>/dev/null; then
    echo -e "${YELLOW}[!] Python 3 not found. Installing via apt...${NC}"
    apt-get update
    apt-get install -y python3 python3-pip python3-venv
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}[✓] Detected Python ${PY_VER}${NC}"

# 3. Handle Port 53 conflicts (e.g. systemd-resolved DNSStubListener)
echo -e "${GREEN}[*] Checking port 53 DNS availability...${NC}"
if ss -ulpn | grep -q ":53 "; then
    PORT_HOLDER=$(ss -ulpn | grep ":53 " | awk '{print $NF}' | head -n1)
    echo -e "${YELLOW}[!] Warning: Port 53 is currently occupied by: ${PORT_HOLDER}${NC}"
    if [[ "$PORT_HOLDER" == *"systemd-resolve"* ]]; then
        echo -e "${CYAN}[*] Disabling systemd-resolved DNSStubListener to free port 53...${NC}"
        sed -i 's/#DNSStubListener=yes/DNSStubListener=no/' /etc/systemd/resolved.conf || true
        sed -i 's/DNSStubListener=yes/DNSStubListener=no/' /etc/systemd/resolved.conf || true
        systemctl restart systemd-resolved || true
    fi
fi

# 4. Create dedicated service user and group
echo -e "${GREEN}[*] Configuring focusguard system user & group...${NC}"
if ! getent group focusguard >/dev/null; then
    groupadd -r focusguard
fi

if ! getent passwd focusguard >/dev/null; then
    useradd -r -g focusguard -d /var/lib/focusguard -s /usr/sbin/nologin -c "FocusGuard Service" focusguard
fi

# Add invoking user (e.g. dietpi) to focusguard group for passwordless CLI access
INVOKING_USER="${SUDO_USER:-$(logname 2>/dev/null || echo "")}"
if [[ -n "$INVOKING_USER" && "$INVOKING_USER" != "root" ]]; then
    echo -e "${GREEN}[*] Adding user '${INVOKING_USER}' to group 'focusguard' for CLI management...${NC}"
    usermod -aG focusguard "$INVOKING_USER"
fi

# 5. Create directories with safe permissions
echo -e "${GREEN}[*] Setting up state and log directories...${NC}"
mkdir -p /var/lib/focusguard
mkdir -p /var/log/focusguard
mkdir -p /run/focusguard
mkdir -p /opt/focusguard

chown -R focusguard:focusguard /var/lib/focusguard
chown -R focusguard:focusguard /var/log/focusguard
chown -R focusguard:focusguard /run/focusguard
chmod 0770 /var/lib/focusguard
chmod 0775 /var/log/focusguard
chmod 0775 /run/focusguard

# 6. Copy application code to /opt/focusguard
echo -e "${GREEN}[*] Installing application files to /opt/focusguard...${NC}"
cp -r "${SCRIPT_DIR}/focusguard" /opt/focusguard/
cp -r "${SCRIPT_DIR}/bin" /opt/focusguard/
cp -r "${SCRIPT_DIR}/scripts" /opt/focusguard/
cp "${SCRIPT_DIR}/pyproject.toml" /opt/focusguard/

chmod -R 755 /opt/focusguard

# Create symlinks in /usr/local/bin
ln -sf /opt/focusguard/bin/focusguard /usr/local/bin/focusguard
ln -sf /opt/focusguard/bin/focusguardd /usr/local/bin/focusguardd
chmod +x /usr/local/bin/focusguard
chmod +x /usr/local/bin/focusguardd
chmod +x /opt/focusguard/bin/focusguard
chmod +x /opt/focusguard/bin/focusguardd
chmod +x /opt/focusguard/scripts/*.sh

# Configure Python path so focusguard module is discovered globally
echo -e "${GREEN}[*] Registering focusguard in Python path...${NC}"
for py_site in $(python3 -c "import site; print(' '.join(site.getsitepackages()))" 2>/dev/null || echo "/usr/local/lib/python3/dist-packages"); do
    if [[ -d "$py_site" && -w "$py_site" ]]; then
        echo "/opt/focusguard" > "${py_site}/focusguard.pth" 2>/dev/null || true
    fi
done
python3 -m pip install -e /opt/focusguard --break-system-packages --no-deps 2>/dev/null || true

# 7. Install and enable systemd service
echo -e "${GREEN}[*] Installing systemd unit...${NC}"
cp "${SCRIPT_DIR}/systemd/focusguard.service" /etc/systemd/system/focusguard.service
systemctl daemon-reload
systemctl enable focusguard.service
systemctl restart focusguard.service

sleep 1

# 8. Verification & Health Check
echo -e "${GREEN}[*] Verifying service operation...${NC}"
if systemctl is-active --quiet focusguard.service; then
    echo -e "${GREEN}${BOLD}[✓] FocusGuard service is ACTIVE and running!${NC}"
else
    echo -e "${RED}[✗] Service failed to start. Check: journalctl -u focusguard.service${NC}"
    exit 1
fi

echo ""
/usr/local/bin/focusguard doctor || true

echo -e "${CYAN}${BOLD}"
echo "═════════════════════════════════════════════════════════════"
echo "        FocusGuard Installation Complete!                    "
echo "═════════════════════════════════════════════════════════════"
echo -e "${NC}"
echo -e "To configure network-wide blocking on your home network:"
echo -e " 1. Run: ${BOLD}focusguard network${NC} to view your server IP and router instructions."
echo -e " 2. Set your router's DHCP DNS server to this DietPi server."
echo -e " 3. Start a focus session anytime over SSH with:"
echo -e "    ${BOLD}focusguard start --duration 4h${NC}"
echo -e "    or"
echo -e "    ${BOLD}focusguard start --until 23:30${NC}"
echo ""
echo -e "${YELLOW}Note: If you were just added to group 'focusguard', log out and back in to refresh SSH permissions.${NC}"
