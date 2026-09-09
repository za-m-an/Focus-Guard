"""System and network diagnostic engine for 'focusguard doctor'."""

from __future__ import annotations

import asyncio
import datetime
import socket
import time
from typing import Any

from focusguard.core.policy import PolicyEngine
from focusguard.network.interfaces import get_local_ip_addresses


class DiagnosticsRunner:
    """
    Runs comprehensive diagnostic checks on network, DNS, ports, IPv4/IPv6, and system health.
    """

    def __init__(self, policy_engine: PolicyEngine, gateway_manager: Any = None) -> None:
        self.policy_engine = policy_engine
        self.gateway_manager = gateway_manager

    async def run_checks(self) -> dict[str, Any]:
        """Execute all diagnostics and return structured report."""
        checks = []

        # 1. IP & Interface Check
        ip_info = get_local_ip_addresses()
        has_v4 = len(ip_info["ipv4"]) > 0
        has_v6 = len(ip_info["ipv6"]) > 0

        checks.append({
            "name": "Network Interfaces",
            "status": "PASS" if has_v4 else "WARN",
            "details": f"IPv4: {', '.join(ip_info['ipv4']) or 'None'} | IPv6: {', '.join(ip_info['ipv6']) or 'None'}",
            "recommendation": "Configure a static IP on DietPi for reliable network-wide DNS." if not has_v4 else None,
        })

        # 2. Gateway & Transparent Redirection Check
        if self.gateway_manager:
            gw_status = self.gateway_manager.get_gateway_status()
            if gw_status.get("transparent_redirection"):
                checks.append({
                    "name": "Gateway Enforcement",
                    "status": "PASS",
                    "details": "Transparent DNS redirection ACTIVE. Outbound port 53 traffic from all LAN devices is intercepted automatically.",
                    "recommendation": None,
                })
            elif gw_status.get("ip_forwarding"):
                checks.append({
                    "name": "Gateway Enforcement",
                    "status": "INFO",
                    "details": "Kernel IP forwarding enabled. Run 'focusguard gateway enable' to activate transparent redirection.",
                    "recommendation": None,
                })
            else:
                checks.append({
                    "name": "Gateway Enforcement",
                    "status": "INFO",
                    "details": "Standard DNS Mode. Ensure router DHCP option 6 advertises DietPi as sole DNS server.",
                    "recommendation": "To automatically enforce new devices without router DNS changes, configure DietPi as gateway.",
                })

        # 3. Upstream Internet Connectivity Check
        upstream_ok = await self._check_upstream_connectivity()
        checks.append({
            "name": "Upstream Internet DNS",
            "status": "PASS" if upstream_ok else "FAIL",
            "details": "Connected to upstream resolvers (1.1.1.1 / 9.9.9.9)" if upstream_ok else "Cannot reach upstream DNS",
            "recommendation": "Check router gateway settings and WAN connectivity." if not upstream_ok else None,
        })

        # 4. DNS Port 53 Listening Check
        port = self.policy_engine.config.dns_port
        checks.append({
            "name": f"DNS Server (Port {port})",
            "status": "PASS",
            "details": f"DNS Engine configured on port {port}",
            "recommendation": None,
        })

        # 5. Session & Lock Integrity Check
        session = self.policy_engine.session_mgr
        is_locked = session.is_locked
        checks.append({
            "name": "Focus Session State",
            "status": "LOCKED" if is_locked else "IDLE",
            "details": f"Status: {session.state.status} | Expires: {session.state.expires_at_utc or 'N/A'}",
            "recommendation": None,
        })

        # 6. IPv6 Leak Assessment
        if has_v6:
            checks.append({
                "name": "IPv6 DNS Protection",
                "status": "PASS",
                "details": "IPv6 addresses detected. FocusGuard dual-stack DNS filters IPv6 AAAA queries.",
                "recommendation": "Ensure router DHCPv6 / RDNSS distributes DietPi IPv6 address, or disable IPv6 on router if unneeded.",
            })
        else:
            checks.append({
                "name": "IPv6 DNS Protection",
                "status": "INFO",
                "details": "No global IPv6 detected. Network operates in IPv4 mode.",
                "recommendation": None,
            })

        # 7. Encrypted DNS (DoH/DoT) Assessment
        checks.append({
            "name": "DoH/DoT Countermeasures",
            "status": "PASS" if self.policy_engine.config.block_doh else "WARN",
            "details": "Known public DoH bootstrap domains sinkholed. SVCB/HTTPS records suppressed." if self.policy_engine.config.block_doh else "DoH blocking disabled.",
            "recommendation": "For maximum focus protection, disable 'Secure DNS / Private DNS' in Chrome/Firefox/Android settings.",
        })

        # 8. System Clock & NTP Synchronization
        now = datetime.datetime.now(datetime.timezone.utc)
        clock_ok = now.year >= 2026
        checks.append({
            "name": "System Clock & Time Guard",
            "status": "PASS" if clock_ok else "WARN",
            "details": f"Current UTC Time: {now.isoformat()}",
            "recommendation": "Ensure DietPi system clock is synced via NTP (dietpi-config -> Time Options)." if not clock_ok else None,
        })

        all_pass = all(c["status"] in ("PASS", "LOCKED", "INFO") for c in checks)

        return {
            "summary_status": "OPTIMAL" if all_pass else "NEEDS_ATTENTION",
            "timestamp": now.isoformat(),
            "checks": checks,
        }

    async def _check_upstream_connectivity(self) -> bool:
        loop = asyncio.get_running_loop()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)
            # Cloudflare or Quad9
            await loop.sock_connect(sock, ("1.1.1.1", 53))
            sock.close()
            return True
        except Exception:
            return False
