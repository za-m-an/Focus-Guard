"""Network Gateway, Linux IP Forwarding, and Transparent DNS Interception Manager."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

from focusguard.network.interfaces import get_local_ip_addresses

logger = logging.getLogger("focusguard.gateway")

CHAIN_REDIRECT = "FOCUSGUARD_REDIRECT"
CHAIN_FILTER = "FOCUSGUARD_FILTER"


class NetworkGatewayManager:
    """
    Controls transparent network-level redirection and kernel routing.
    Redirects all client port 53 DNS traffic to local FocusGuard instance,
    allowing automatic enforcement on any device that joins the network.
    """

    def __init__(self, dns_port: int = 53) -> None:
        self.dns_port = dns_port
        self._has_iptables = shutil.which("iptables") is not None

    def is_ip_forwarding_enabled(self) -> bool:
        """Check if Linux IPv4 packet forwarding is enabled in kernel."""
        fwd_file = Path("/proc/sys/net/ipv4/ip_forward")
        if fwd_file.exists():
            try:
                return fwd_file.read_text().strip() == "1"
            except OSError:
                pass
        return False

    def enable_ip_forwarding(self) -> bool:
        """Enable Linux IPv4 packet forwarding."""
        try:
            fwd_file = Path("/proc/sys/net/ipv4/ip_forward")
            if fwd_file.exists():
                fwd_file.write_text("1")
                return True
        except OSError:
            pass

        if shutil.which("sysctl"):
            try:
                res = subprocess.run(
                    ["sysctl", "-w", "net.ipv4.ip_forward=1"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                return res.returncode == 0
            except Exception:
                pass
        return False

    def is_transparent_redirection_active(self) -> bool:
        """Check if FocusGuard iptables redirection chains are active."""
        if not self._has_iptables:
            return False
        try:
            res = subprocess.run(
                ["iptables", "-t", "nat", "-L", CHAIN_REDIRECT, "-n"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            return res.returncode == 0
        except Exception:
            return False

    def enable_transparent_redirection(self) -> tuple[bool, str]:
        """
        Configure dedicated iptables chains to intercept all outbound DNS (port 53)
        and reject DoT (port 853).
        """
        if not self._has_iptables:
            return False, "iptables utility not found on this system."

        try:
            self.enable_ip_forwarding()

            # 1. Create NAT PREROUTING chain if it does not exist
            subprocess.run(["iptables", "-t", "nat", "-N", CHAIN_REDIRECT], stderr=subprocess.PIPE, check=False)
            subprocess.run(["iptables", "-t", "nat", "-F", CHAIN_REDIRECT], check=False)

            # Redirect UDP 53 to local port
            subprocess.run([
                "iptables", "-t", "nat", "-A", CHAIN_REDIRECT,
                "-p", "udp", "--dport", "53",
                "-j", "REDIRECT", "--to-ports", str(self.dns_port)
            ], stderr=subprocess.PIPE, check=True)

            # Redirect TCP 53 to local port
            subprocess.run([
                "iptables", "-t", "nat", "-A", CHAIN_REDIRECT,
                "-p", "tcp", "--dport", "53",
                "-j", "REDIRECT", "--to-ports", str(self.dns_port)
            ], stderr=subprocess.PIPE, check=True)

            # Ensure jump from PREROUTING table exists
            check_nat = subprocess.run(
                ["iptables", "-t", "nat", "-C", "PREROUTING", "-j", CHAIN_REDIRECT],
                stderr=subprocess.PIPE, check=False
            )
            if check_nat.returncode != 0:
                subprocess.run(["iptables", "-t", "nat", "-I", "PREROUTING", "1", "-j", CHAIN_REDIRECT], stderr=subprocess.PIPE, check=True)

            # 2. Create FILTER chain for DoT (port 853) blocking
            subprocess.run(["iptables", "-N", CHAIN_FILTER], stderr=subprocess.PIPE, check=False)
            subprocess.run(["iptables", "-F", CHAIN_FILTER], check=False)
            subprocess.run([
                "iptables", "-A", CHAIN_FILTER,
                "-p", "tcp", "--dport", "853",
                "-j", "REJECT"
            ], stderr=subprocess.PIPE, check=True)

            # Ensure jump from FORWARD table exists
            check_fwd = subprocess.run(
                ["iptables", "-C", "FORWARD", "-j", CHAIN_FILTER],
                stderr=subprocess.PIPE, check=False
            )
            if check_fwd.returncode != 0:
                subprocess.run(["iptables", "-I", "FORWARD", "1", "-j", CHAIN_FILTER], stderr=subprocess.PIPE, check=True)

            logger.info("Transparent network redirection enabled successfully.")
            return True, "Transparent DNS interception and DoT blocking active."

        except subprocess.CalledProcessError as e:
            err_output = (e.stderr.decode().strip() if e.stderr else "").strip()
            if not err_output:
                err_output = str(e)
            if "permission denied" in err_output.lower() or "must be root" in err_output.lower():
                err_msg = "Enabling network gateway enforcement requires root privileges (run with sudo)."
            else:
                err_msg = f"Failed to apply iptables redirection: {err_output}"
            logger.error(err_msg)
            return False, err_msg
        except Exception as e:
            return False, str(e)

    def disable_transparent_redirection(self) -> tuple[bool, str]:
        """
        Safely dismantle FocusGuard iptables chains without affecting other system rules.
        """
        if not self._has_iptables:
            return False, "iptables utility not found."

        try:
            # 1. Clean NAT table jump & chain
            subprocess.run(["iptables", "-t", "nat", "-D", "PREROUTING", "-j", CHAIN_REDIRECT], stderr=subprocess.PIPE, check=False)
            subprocess.run(["iptables", "-t", "nat", "-F", CHAIN_REDIRECT], stderr=subprocess.PIPE, check=False)
            subprocess.run(["iptables", "-t", "nat", "-X", CHAIN_REDIRECT], stderr=subprocess.PIPE, check=False)

            # 2. Clean FILTER table jump & chain
            subprocess.run(["iptables", "-D", "FORWARD", "-j", CHAIN_FILTER], stderr=subprocess.PIPE, check=False)
            subprocess.run(["iptables", "-F", CHAIN_FILTER], stderr=subprocess.PIPE, check=False)
            subprocess.run(["iptables", "-X", CHAIN_FILTER], stderr=subprocess.PIPE, check=False)

            logger.info("Transparent network redirection disabled.")
            return True, "Transparent DNS interception removed cleanly."
        except subprocess.CalledProcessError as e:
            err_output = (e.stderr.decode().strip() if e.stderr else "").strip()
            if "permission denied" in err_output.lower() or "must be root" in err_output.lower():
                return False, "Disabling network gateway enforcement requires root privileges (run with sudo)."
            return False, f"Failed to disable iptables redirection: {err_output or e}"
        except Exception as e:
            return False, str(e)

    def get_gateway_status(self) -> dict[str, Any]:
        """Get summary of gateway and transparent interception state."""
        fwd_enabled = self.is_ip_forwarding_enabled()
        redir_active = self.is_transparent_redirection_active()
        ip_info = get_local_ip_addresses()

        return {
            "gateway_capable": self._has_iptables,
            "ip_forwarding": fwd_enabled,
            "transparent_redirection": redir_active,
            "dns_port": self.dns_port,
            "local_ips": ip_info,
            "mode": "TRANSPARENT_GATEWAY" if redir_active else "STANDARD_DNS",
        }
