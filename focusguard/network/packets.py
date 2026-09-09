"""Packet Header Inspection, Parsing, and Normalization Subsystem.

Provides zero-dependency binary parsing of Ethernet, IPv4, IPv6, TCP, UDP,
ICMP, ICMPv6, and ARP headers, transforming raw wire frames into structured
and normalized PacketMetadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import ipaddress
import struct
from typing import Any


@dataclass
class PacketMetadata:
    """Normalized metadata extracted from observed network packet headers."""
    id: int
    timestamp: str
    interface: str
    direction: str                     # "LAN → WAN", "WAN → LAN", "INBOUND", "OUTBOUND", "LOCAL", "FORWARDED"
    ip_version: str                    # "IPv4", "IPv6", "ARP", "OTHER"
    src_ip: str
    dst_ip: str
    protocol: str                      # "TCP", "UDP", "ICMP", "ICMPv6", "ARP", "OTHER"
    src_port: int | None = None
    dst_port: int | None = None
    length: int = 0
    ttl: int | None = None
    tcp_flags: list[str] = field(default_factory=list)
    device_name: str | None = None
    policy_match: str | None = None
    policy_action: str = "OBSERVED"    # "OBSERVED", "MATCH", "ALLOWED"
    raw_preview: str | None = None     # Safe hex preview for verbose inspection

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "interface": self.interface,
            "direction": self.direction,
            "ip_version": self.ip_version,
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "protocol": self.protocol,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "length": self.length,
            "ttl": self.ttl,
            "tcp_flags": self.tcp_flags,
            "device_name": self.device_name,
            "policy_match": self.policy_match,
            "policy_action": self.policy_action,
            "raw_preview": self.raw_preview,
        }


def format_hex_preview(data: bytes, max_bytes: int = 32) -> str:
    """Safely format raw packet bytes into hex + ASCII representation."""
    sample = data[:max_bytes]
    hex_str = " ".join(f"{b:02x}" for b in sample)
    ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in sample)
    return f"{hex_str:<{max_bytes * 3}} | {ascii_str}"


def is_private_ip(ip_str: str) -> bool:
    """Check if an IPv4 or IPv6 address is within private/local subnets."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False


def determine_direction(src_ip: str, dst_ip: str, local_ips: list[str] | None = None) -> str:
    """
    Determine packet direction relative to local appliance and LAN/WAN topology.
    """
    src_priv = is_private_ip(src_ip)
    dst_priv = is_private_ip(dst_ip)
    locals_set = set(local_ips or [])

    if src_ip in locals_set:
        return "OUTBOUND (LOCAL)"
    if dst_ip in locals_set:
        return "INBOUND (LOCAL)"

    if src_priv and not dst_priv:
        return "LAN → WAN"
    elif not src_priv and dst_priv:
        return "WAN → LAN"
    elif src_priv and dst_priv:
        return "LAN (LOCAL)"
    else:
        return "FORWARDED"


class PacketParser:
    """
    High-performance, pure-Python binary packet decoder.
    Parses Ethernet frames and raw IP datagrams safely without external libraries.
    """

    @classmethod
    def parse(
        cls,
        raw_data: bytes,
        packet_id: int,
        interface: str = "eth0",
        local_ips: list[str] | None = None,
        has_ethernet_header: bool = True,
    ) -> PacketMetadata | None:
        """
        Parse raw bytes into normalized PacketMetadata.
        Returns None if frame is malformed or smaller than minimum length.
        """
        if not raw_data:
            return None

        total_length = len(raw_data)
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
        payload = raw_data
        offset = 0

        # Optional Ethernet Header (14 bytes)
        ethertype = 0x0800  # Default IPv4
        if has_ethernet_header:
            if total_length < 14:
                return None
            # Dest MAC (6), Src MAC (6), EtherType (2)
            ethertype = struct.unpack("!H", raw_data[12:14])[0]
            offset = 14
            payload = raw_data[14:]

        # 1. ARP Protocol (EtherType 0x0806)
        if ethertype == 0x0806:
            return cls._parse_arp(payload, packet_id, timestamp, interface, total_length)

        # 2. IPv4 Protocol (EtherType 0x0800)
        elif ethertype == 0x0800 or (not has_ethernet_header and (raw_data[0] >> 4) == 4):
            return cls._parse_ipv4(payload, packet_id, timestamp, interface, total_length, local_ips, raw_data)

        # 3. IPv6 Protocol (EtherType 0x86DD)
        elif ethertype == 0x86DD or (not has_ethernet_header and (raw_data[0] >> 4) == 6):
            return cls._parse_ipv6(payload, packet_id, timestamp, interface, total_length, local_ips, raw_data)

        # 4. Other Ethernet Frames
        return PacketMetadata(
            id=packet_id,
            timestamp=timestamp,
            interface=interface,
            direction="LOCAL",
            ip_version="OTHER",
            src_ip="unknown",
            dst_ip="unknown",
            protocol=f"EtherType:0x{ethertype:04x}",
            length=total_length,
            raw_preview=format_hex_preview(raw_data),
        )

    @classmethod
    def _parse_ipv4(
        cls,
        data: bytes,
        packet_id: int,
        timestamp: str,
        interface: str,
        total_length: int,
        local_ips: list[str] | None,
        raw_full: bytes,
    ) -> PacketMetadata | None:
        if len(data) < 20:
            return None

        # Byte 0: Version (4 bits) + IHL (4 bits)
        v_ihl = data[0]
        version = v_ihl >> 4
        ihl = (v_ihl & 0x0F) * 4
        if version != 4 or len(data) < ihl:
            return None

        # Byte 8: TTL, Byte 9: Protocol
        ttl = data[8]
        protocol_num = data[9]
        src_ip = socket_inet_ntoa(data[12:16])
        dst_ip = socket_inet_ntoa(data[16:20])

        transport_data = data[ihl:]
        proto_name, src_port, dst_port, tcp_flags = cls._parse_transport(protocol_num, transport_data)
        direction = determine_direction(src_ip, dst_ip, local_ips)

        return PacketMetadata(
            id=packet_id,
            timestamp=timestamp,
            interface=interface,
            direction=direction,
            ip_version="IPv4",
            src_ip=src_ip,
            dst_ip=dst_ip,
            protocol=proto_name,
            src_port=src_port,
            dst_port=dst_port,
            length=total_length,
            ttl=ttl,
            tcp_flags=tcp_flags,
            raw_preview=format_hex_preview(raw_full),
        )

    @classmethod
    def _parse_ipv6(
        cls,
        data: bytes,
        packet_id: int,
        timestamp: str,
        interface: str,
        total_length: int,
        local_ips: list[str] | None,
        raw_full: bytes,
    ) -> PacketMetadata | None:
        if len(data) < 40:
            return None

        # IPv6 Fixed Header: 40 bytes
        # Byte 6: Next Header (protocol), Byte 7: Hop Limit (TTL)
        next_header = data[6]
        hop_limit = data[7]
        src_ip = socket_inet_ntop6(data[8:24])
        dst_ip = socket_inet_ntop6(data[24:40])

        transport_data = data[40:]
        proto_name, src_port, dst_port, tcp_flags = cls._parse_transport(next_header, transport_data)
        direction = determine_direction(src_ip, dst_ip, local_ips)

        return PacketMetadata(
            id=packet_id,
            timestamp=timestamp,
            interface=interface,
            direction=direction,
            ip_version="IPv6",
            src_ip=src_ip,
            dst_ip=dst_ip,
            protocol=proto_name,
            src_port=src_port,
            dst_port=dst_port,
            length=total_length,
            ttl=hop_limit,
            tcp_flags=tcp_flags,
            raw_preview=format_hex_preview(raw_full),
        )

    @classmethod
    def _parse_arp(
        cls,
        data: bytes,
        packet_id: int,
        timestamp: str,
        interface: str,
        total_length: int,
    ) -> PacketMetadata | None:
        if len(data) < 28:
            return None

        # Operation (Request=1, Reply=2)
        opcode = struct.unpack("!H", data[6:8])[0]
        src_ip = socket_inet_ntoa(data[14:18])
        dst_ip = socket_inet_ntoa(data[24:28])
        proto_label = "ARP (Req)" if opcode == 1 else ("ARP (Rep)" if opcode == 2 else "ARP")

        return PacketMetadata(
            id=packet_id,
            timestamp=timestamp,
            interface=interface,
            direction="LOCAL",
            ip_version="ARP",
            src_ip=src_ip,
            dst_ip=dst_ip,
            protocol=proto_label,
            length=total_length,
            raw_preview=format_hex_preview(data),
        )

    @classmethod
    def _parse_transport(
        cls, protocol_num: int, data: bytes
    ) -> tuple[str, int | None, int | None, list[str]]:
        """Parse transport layer header (TCP, UDP, ICMP, ICMPv6)."""
        tcp_flags: list[str] = []

        # 6: TCP
        if protocol_num == 6:
            if len(data) >= 20:
                src_port, dst_port = struct.unpack("!HH", data[0:4])
                # Byte 13: Flags (CWR, ECE, URG, ACK, PSH, RST, SYN, FIN)
                flags_byte = data[13]
                if flags_byte & 0x02:
                    tcp_flags.append("SYN")
                if flags_byte & 0x10:
                    tcp_flags.append("ACK")
                if flags_byte & 0x01:
                    tcp_flags.append("FIN")
                if flags_byte & 0x04:
                    tcp_flags.append("RST")
                if flags_byte & 0x08:
                    tcp_flags.append("PSH")
                if flags_byte & 0x20:
                    tcp_flags.append("URG")
                return "TCP", src_port, dst_port, tcp_flags
            return "TCP", None, None, []

        # 17: UDP
        elif protocol_num == 17:
            if len(data) >= 8:
                src_port, dst_port = struct.unpack("!HH", data[0:4])
                return "UDP", src_port, dst_port, []
            return "UDP", None, None, []

        # 1: ICMP
        elif protocol_num == 1:
            if len(data) >= 2:
                icmp_type = data[0]
                label = "ICMP Echo" if icmp_type in (0, 8) else f"ICMP ({icmp_type})"
                return label, None, None, []
            return "ICMP", None, None, []

        # 58: ICMPv6
        elif protocol_num == 58:
            if len(data) >= 2:
                icmp6_type = data[0]
                label = "ICMPv6 Echo" if icmp6_type in (128, 129) else f"ICMPv6 ({icmp6_type})"
                return label, None, None, []
            return "ICMPv6", None, None, []

        return f"Proto:{protocol_num}", None, None, []


def socket_inet_ntoa(raw_bytes: bytes) -> str:
    """Safe pure-python conversion of 4 bytes into IPv4 dotted quad."""
    return f"{raw_bytes[0]}.{raw_bytes[1]}.{raw_bytes[2]}.{raw_bytes[3]}"


def socket_inet_ntop6(raw_bytes: bytes) -> str:
    """Safe pure-python conversion of 16 bytes into normalized IPv6 hex string."""
    try:
        return str(ipaddress.IPv6Address(raw_bytes))
    except Exception:
        # Fallback raw hex grouping
        hextets = [f"{raw_bytes[i]:02x}{raw_bytes[i+1]:02x}" for i in range(0, 16, 2)]
        return ":".join(hextets)
