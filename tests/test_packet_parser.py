"""Unit tests for binary packet decoding and metadata normalization."""

import struct
import pytest
from focusguard.network.packets import (
    PacketParser,
    PacketMetadata,
    determine_direction,
    is_private_ip,
    format_hex_preview,
)


def make_eth_header(src_mac: bytes = b"\x00" * 6, dst_mac: bytes = b"\xff" * 6, ethertype: int = 0x0800) -> bytes:
    """Build 14-byte Ethernet header."""
    return dst_mac + src_mac + struct.pack("!H", ethertype)


def make_ipv4_packet(
    src_ip: str,
    dst_ip: str,
    protocol: int,
    payload: bytes,
    ttl: int = 64,
) -> bytes:
    """Construct a minimal valid IPv4 packet with standard 20-byte header."""
    v_ihl = (4 << 4) | 5
    tos = 0
    total_length = 20 + len(payload)
    pkt_id = 54321
    flags_frag = 0x4000  # DF set
    checksum = 0
    src_bytes = bytes(map(int, src_ip.split(".")))
    dst_bytes = bytes(map(int, dst_ip.split(".")))

    ip_hdr = struct.pack(
        "!BBHHHBBH4s4s",
        v_ihl,
        tos,
        total_length,
        pkt_id,
        flags_frag,
        ttl,
        protocol,
        checksum,
        src_bytes,
        dst_bytes,
    )
    return ip_hdr + payload


def make_tcp_header(
    src_port: int,
    dst_port: int,
    flags: int = 0x02,  # SYN
    payload: bytes = b"",
) -> bytes:
    """Construct 20-byte TCP header."""
    seq = 1000
    ack = 0
    offset_reserved = (5 << 4)
    window = 65535
    checksum = 0
    urg_ptr = 0
    tcp_hdr = struct.pack(
        "!HHIIBBHHH",
        src_port,
        dst_port,
        seq,
        ack,
        offset_reserved,
        flags,
        window,
        checksum,
        urg_ptr,
    )
    return tcp_hdr + payload


def make_udp_header(
    src_port: int,
    dst_port: int,
    payload: bytes = b"",
) -> bytes:
    """Construct 8-byte UDP header."""
    length = 8 + len(payload)
    checksum = 0
    udp_hdr = struct.pack("!HHHH", src_port, dst_port, length, checksum)
    return udp_hdr + payload


def test_parse_ipv4_tcp_syn():
    tcp_payload = make_tcp_header(src_port=52341, dst_port=443, flags=0x02)  # SYN
    ip_pkt = make_ipv4_packet(src_ip="192.168.1.15", dst_ip="142.250.190.46", protocol=6, payload=tcp_payload)
    eth_frame = make_eth_header(ethertype=0x0800) + ip_pkt

    pkt = PacketParser.parse(eth_frame, packet_id=1, interface="eth0")
    assert pkt is not None
    assert pkt.id == 1
    assert pkt.ip_version == "IPv4"
    assert pkt.protocol == "TCP"
    assert pkt.src_ip == "192.168.1.15"
    assert pkt.dst_ip == "142.250.190.46"
    assert pkt.src_port == 52341
    assert pkt.dst_port == 443
    assert pkt.ttl == 64
    assert "SYN" in pkt.tcp_flags
    assert pkt.direction == "LAN → WAN"


def test_parse_ipv4_tcp_ack_psh():
    # ACK (0x10) + PSH (0x08) = 0x18
    tcp_payload = make_tcp_header(src_port=443, dst_port=52341, flags=0x18, payload=b"HTTP/1.1 200 OK")
    ip_pkt = make_ipv4_packet(src_ip="142.250.190.46", dst_ip="192.168.1.15", protocol=6, payload=tcp_payload)
    eth_frame = make_eth_header(ethertype=0x0800) + ip_pkt

    pkt = PacketParser.parse(eth_frame, packet_id=2, interface="eth0")
    assert pkt is not None
    assert "ACK" in pkt.tcp_flags
    assert "PSH" in pkt.tcp_flags
    assert pkt.direction == "WAN → LAN"


def test_parse_ipv4_udp():
    udp_payload = make_udp_header(src_port=43122, dst_port=53, payload=b"\x00\x01query")
    ip_pkt = make_ipv4_packet(src_ip="192.168.1.20", dst_ip="192.168.1.50", protocol=17, payload=udp_payload)
    eth_frame = make_eth_header(ethertype=0x0800) + ip_pkt

    pkt = PacketParser.parse(eth_frame, packet_id=3, interface="eth0", local_ips=["192.168.1.50"])
    assert pkt is not None
    assert pkt.ip_version == "IPv4"
    assert pkt.protocol == "UDP"
    assert pkt.src_port == 43122
    assert pkt.dst_port == 53
    assert pkt.direction == "INBOUND (LOCAL)"


def test_parse_ipv4_icmp():
    # ICMP Echo Request: type 8, code 0
    icmp_payload = struct.pack("!BBHHH", 8, 0, 0, 1, 1) + b"abcdefghijklmnopqrstuvw"
    ip_pkt = make_ipv4_packet(src_ip="192.168.1.25", dst_ip="8.8.8.8", protocol=1, payload=icmp_payload)
    eth_frame = make_eth_header(ethertype=0x0800) + ip_pkt

    pkt = PacketParser.parse(eth_frame, packet_id=4)
    assert pkt is not None
    assert pkt.protocol == "ICMP Echo"
    assert pkt.src_port is None
    assert pkt.dst_port is None


def test_parse_arp():
    # Hardware type 1 (Ethernet), Proto 0x0800 (IPv4), HwSize 6, ProtoSize 4, Op 1 (Request)
    arp_data = struct.pack(
        "!HHBBH6s4s6s4s",
        1,
        0x0800,
        6,
        4,
        1,  # Request
        b"\x00" * 6,
        bytes(map(int, "192.168.1.10".split("."))),
        b"\xff" * 6,
        bytes(map(int, "192.168.1.1".split("."))),
    )
    eth_frame = make_eth_header(ethertype=0x0806) + arp_data

    pkt = PacketParser.parse(eth_frame, packet_id=5)
    assert pkt is not None
    assert pkt.ip_version == "ARP"
    assert pkt.protocol == "ARP (Req)"
    assert pkt.src_ip == "192.168.1.10"
    assert pkt.dst_ip == "192.168.1.1"


def test_direction_determination():
    assert determine_direction("192.168.1.5", "1.1.1.1") == "LAN → WAN"
    assert determine_direction("1.1.1.1", "192.168.1.5") == "WAN → LAN"
    assert determine_direction("192.168.1.5", "192.168.1.1") == "LAN (LOCAL)"
    assert determine_direction("192.168.1.50", "8.8.8.8", local_ips=["192.168.1.50"]) == "OUTBOUND (LOCAL)"
    assert determine_direction("8.8.8.8", "192.168.1.50", local_ips=["192.168.1.50"]) == "INBOUND (LOCAL)"


def test_truncated_packet_handling():
    # Zero bytes
    assert PacketParser.parse(b"", 1) is None
    # Less than 14 bytes Ethernet
    assert PacketParser.parse(b"\x01\x02\x03", 1) is None
    # Truncated IP header
    truncated = make_eth_header() + b"\x45\x00\x00"
    assert PacketParser.parse(truncated, 1) is None
