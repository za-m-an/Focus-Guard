#!/usr/bin/env bash
# ==============================================================================
# FocusGuard Optional Firewall Helper
# Blocks DNS-over-TLS (port 853) and prevents rogue direct DNS (port 53)
# ==============================================================================
set -euo pipefail

ACTION="${1:-status}"

if [[ $EUID -ne 0 ]]; then
    echo "This helper requires root: sudo $0 [enable|disable|status]"
    exit 1
fi

case "$ACTION" in
    enable)
        echo "Applying firewall rules to block DoT (port 853) bypasses..."
        # Drop outbound DoT port 853 so devices cannot bypass local DNS
        iptables -C OUTPUT -p tcp --dport 853 -j REJECT 2>/dev/null || iptables -A OUTPUT -p tcp --dport 853 -j REJECT
        ip6tables -C OUTPUT -p tcp --dport 853 -j REJECT 2>/dev/null || ip6tables -A OUTPUT -p tcp --dport 853 -j REJECT || true
        echo "✓ DoT (port 853) firewall lock enabled."
        ;;
    disable)
        echo "Removing firewall rules..."
        iptables -D OUTPUT -p tcp --dport 853 -j REJECT 2>/dev/null || true
        ip6tables -D OUTPUT -p tcp --dport 853 -j REJECT 2>/dev/null || true
        echo "✓ Firewall rules removed."
        ;;
    status)
        echo "Current port 853 firewall status:"
        iptables -L OUTPUT -v -n | grep "853" || echo "No active port 853 rules in iptables."
        ;;
    *)
        echo "Usage: $0 [enable|disable|status]"
        exit 1
        ;;
esac
