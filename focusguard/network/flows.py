"""Flow Correlation and Bidirectional Connection Tracking.

Aggregates individual packets into bidirectional network connection flows,
tracking packet counts, byte volumes, connection durations, and policy classifications.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading
import time
from typing import Any

from focusguard.network.packets import PacketMetadata, is_private_ip


@dataclass
class PacketFlow:
    """Represents an active bidirectional network flow between two endpoints."""
    flow_id: str
    protocol: str
    client_ip: str
    client_port: int | None
    server_ip: str
    server_port: int | None
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    packets_client_to_server: int = 0
    packets_server_to_client: int = 0
    bytes_client_to_server: int = 0
    bytes_server_to_client: int = 0
    tcp_state: str = "ESTABLISHED"
    policy_tag: str | None = None
    device_name: str | None = None

    @property
    def total_packets(self) -> int:
        return self.packets_client_to_server + self.packets_server_to_client

    @property
    def total_bytes(self) -> int:
        return self.bytes_client_to_server + self.bytes_server_to_client

    @property
    def duration_seconds(self) -> float:
        return max(0.0, self.last_seen - self.first_seen)

    def to_dict(self) -> dict[str, Any]:
        return {
            "flow_id": self.flow_id,
            "protocol": self.protocol,
            "client_ip": self.client_ip,
            "client_port": self.client_port,
            "server_ip": self.server_ip,
            "server_port": self.server_port,
            "first_seen_iso": datetime.fromtimestamp(self.first_seen, tz=timezone.utc).isoformat(),
            "last_seen_iso": datetime.fromtimestamp(self.last_seen, tz=timezone.utc).isoformat(),
            "duration_sec": round(self.duration_seconds, 2),
            "packets": self.total_packets,
            "bytes": self.total_bytes,
            "bytes_in": self.bytes_server_to_client,
            "bytes_out": self.bytes_client_to_server,
            "tcp_state": self.tcp_state,
            "policy_tag": self.policy_tag,
            "device_name": self.device_name,
        }


def make_flow_key(proto: str, ip1: str, port1: int | None, ip2: str, port2: int | None) -> tuple[str, str, int, str, int]:
    """
    Generate an order-independent canonical 5-tuple key for bidirectional tracking.
    """
    p1 = port1 or 0
    p2 = port2 or 0
    ep1 = (ip1, p1)
    ep2 = (ip2, p2)
    if ep1 <= ep2:
        return (proto, ip1, p1, ip2, p2)
    return (proto, ip2, p2, ip1, p1)


class FlowTracker:
    """
    Thread-safe, bounded-capacity connection flow tracking engine.
    Automatically correlates observed packets into flows and evicts stale connections.
    """

    def __init__(self, max_flows: int = 5000, idle_timeout: float = 300.0) -> None:
        self.max_flows = max_flows
        self.idle_timeout = idle_timeout
        self._lock = threading.Lock()
        self._flows: dict[tuple[str, str, int, str, int], PacketFlow] = {}
        self._last_prune = time.time()

    def record_packet(self, pkt: PacketMetadata) -> PacketFlow | None:
        """Update or create flow state based on observed packet."""
        # Non-transport packets (ARP / raw without ports) are not tracked in 5-tuple flows
        if not pkt.src_ip or not pkt.dst_ip:
            return None

        proto = pkt.protocol.split()[0]
        src_port = pkt.src_port or 0
        dst_port = pkt.dst_port or 0

        # Flow key
        key = make_flow_key(proto, pkt.src_ip, src_port, pkt.dst_ip, dst_port)
        now = time.time()

        with self._lock:
            # Periodic pruning every 60 seconds
            if now - self._last_prune > 60.0:
                self._prune_stale_locked(now)

            # Cap size protection
            if len(self._flows) >= self.max_flows and key not in self._flows:
                self._prune_oldest_locked()

            if key not in self._flows:
                # Client is typically the private LAN IP or ephemeral port
                is_src_client = is_private_ip(pkt.src_ip) or (src_port > 1024 and dst_port in (80, 443, 53, 853))
                if is_src_client:
                    client_ip, client_port = pkt.src_ip, pkt.src_port
                    server_ip, server_port = pkt.dst_ip, pkt.dst_port
                else:
                    client_ip, client_port = pkt.dst_ip, pkt.dst_port
                    server_ip, server_port = pkt.src_ip, pkt.src_port

                flow_id = f"{proto}_{client_ip}:{client_port}->{server_ip}:{server_port}"
                flow = PacketFlow(
                    flow_id=flow_id,
                    protocol=proto,
                    client_ip=client_ip,
                    client_port=client_port,
                    server_ip=server_ip,
                    server_port=server_port,
                    first_seen=now,
                    last_seen=now,
                    policy_tag=pkt.policy_match,
                    device_name=pkt.device_name,
                )
                self._flows[key] = flow
            else:
                flow = self._flows[key]

            flow.last_seen = now
            if pkt.policy_match and not flow.policy_tag:
                flow.policy_tag = pkt.policy_match
            if pkt.device_name and not flow.device_name:
                flow.device_name = pkt.device_name

            # Increment packet & byte counts based on direction
            if pkt.src_ip == flow.client_ip:
                flow.packets_client_to_server += 1
                flow.bytes_client_to_server += pkt.length
            else:
                flow.packets_server_to_client += 1
                flow.bytes_server_to_client += pkt.length

            # Track TCP states
            if "FIN" in pkt.tcp_flags or "RST" in pkt.tcp_flags:
                flow.tcp_state = "CLOSING" if "FIN" in pkt.tcp_flags else "RESET"
            elif "SYN" in pkt.tcp_flags and "ACK" not in pkt.tcp_flags:
                flow.tcp_state = "SYN_SENT"

            return flow

    def _prune_stale_locked(self, now: float) -> None:
        """Evict flows that have been idle longer than idle_timeout."""
        self._last_prune = now
        stale_keys = [
            k for k, flow in self._flows.items()
            if (now - flow.last_seen) > self.idle_timeout
        ]
        for k in stale_keys:
            del self._flows[k]

    def _prune_oldest_locked(self) -> None:
        """Evict the oldest 10% of flows when table hits capacity."""
        if not self._flows:
            return
        sorted_keys = sorted(self._flows.keys(), key=lambda k: self._flows[k].last_seen)
        num_to_drop = max(1, len(sorted_keys) // 10)
        for k in sorted_keys[:num_to_drop]:
            del self._flows[k]

    def get_active_flow_count(self) -> int:
        with self._lock:
            return len(self._flows)

    def get_flows(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return list of active flows sorted by most recently active."""
        with self._lock:
            flows = [f.to_dict() for f in self._flows.values()]
        flows.sort(key=lambda x: x["last_seen_iso"], reverse=True)
        return flows[:limit]
