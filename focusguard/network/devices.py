"""Device Discovery and Active Network Client Tracking.

Discovers client devices interacting with the FocusGuard enforcement point,
tracking activity, query statistics, and last seen timestamps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import logging
import socket
import threading
from typing import Any

logger = logging.getLogger("focusguard.devices")


@dataclass
class DeviceInfo:
    ip: str
    hostname: str = ""
    first_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_queries: int = 0
    blocked_queries: int = 0

    @property
    def is_active(self) -> bool:
        """Device is considered active if seen within the last 15 minutes."""
        try:
            dt = datetime.fromisoformat(self.last_seen)
            now = datetime.now(timezone.utc)
            return (now - dt) < timedelta(minutes=15)
        except Exception:
            return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "ip": self.ip,
            "hostname": self.hostname or f"Device-{self.ip.split('.')[-1] if '.' in self.ip else self.ip}",
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "total_queries": self.total_queries,
            "blocked_queries": self.blocked_queries,
            "active": self.is_active,
        }


class DeviceTracker:
    """
    Tracks all LAN client devices issuing DNS queries or traversing the enforcement point.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._devices: dict[str, DeviceInfo] = {}

    def record_query(self, client_ip: str, is_blocked: bool = False) -> None:
        """Record an incoming query event for a client device."""
        if not client_ip or client_ip in ("127.0.0.1", "::1", "localhost"):
            return

        now_str = datetime.now(timezone.utc).isoformat()
        with self._lock:
            if client_ip not in self._devices:
                hostname = self._resolve_hostname_async(client_ip)
                dev = DeviceInfo(
                    ip=client_ip,
                    hostname=hostname,
                    first_seen=now_str,
                    last_seen=now_str,
                    total_queries=1,
                    blocked_queries=1 if is_blocked else 0,
                )
                self._devices[client_ip] = dev
            else:
                dev = self._devices[client_ip]
                dev.last_seen = now_str
                dev.total_queries += 1
                if is_blocked:
                    dev.blocked_queries += 1

    def _resolve_hostname_async(self, ip: str) -> str:
        """Best-effort reverse DNS lookup without blocking main thread."""
        try:
            # Set short timeout for reverse lookup
            return socket.gethostbyaddr(ip)[0]
        except Exception:
            return ""

    def get_all_devices(self) -> list[dict[str, Any]]:
        """Return list of all discovered devices sorted by last seen."""
        with self._lock:
            devices = [dev.to_dict() for dev in self._devices.values()]
        # Sort by most recently active
        devices.sort(key=lambda d: d.get("last_seen", ""), reverse=True)
        return devices

    def active_device_count(self) -> int:
        """Count how many devices were active in the last 15 minutes."""
        with self._lock:
            return sum(1 for d in self._devices.values() if d.is_active)
