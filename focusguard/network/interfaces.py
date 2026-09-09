"""Network interface inspection and IP address discovery for DietPi/Linux."""

from __future__ import annotations

import socket
import subprocess
from typing import Any


def get_local_ip_addresses() -> dict[str, list[str]]:
    """
    Detect local IPv4 and IPv6 addresses across active network interfaces.
    """
    results: dict[str, list[str]] = {"ipv4": [], "ipv6": []}

    # Primary method: use socket getaddrinfo on hostname
    try:
        hostname = socket.gethostname()
        for res in socket.getaddrinfo(hostname, None):
            family, _, _, _, sockaddr = res
            ip = sockaddr[0]
            if family == socket.AF_INET:
                if not ip.startswith("127.") and ip not in results["ipv4"]:
                    results["ipv4"].append(ip)
            elif family == socket.AF_INET6:
                if ip != "::1" and not ip.startswith("fe80:") and ip not in results["ipv6"]:
                    results["ipv6"].append(ip)
    except Exception:
        pass

    # Secondary method: connect probe to internet IP without sending packets
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("1.1.1.1", 53))
            primary_v4 = s.getsockname()[0]
            if primary_v4 not in results["ipv4"]:
                results["ipv4"].insert(0, primary_v4)
    except Exception:
        pass

    if socket.has_ipv6:
        try:
            with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as s:
                s.connect(("2606:4700:4700::1111", 53))
                primary_v6 = s.getsockname()[0]
                if primary_v6 not in results["ipv6"]:
                    results["ipv6"].insert(0, primary_v6)
        except Exception:
            pass

    return results


def check_port_in_use(port: int = 53, host: str = "127.0.0.1") -> bool:
    """Check if UDP port 53 is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True
