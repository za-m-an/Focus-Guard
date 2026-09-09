"""Unit tests for PacketMonitorEngine and policy correlation."""

import asyncio
import struct
import pytest
from focusguard.network.monitor import PacketMonitorEngine
from focusguard.network.devices import DeviceTracker
from tests.test_packet_parser import make_eth_header, make_ipv4_packet, make_udp_header, make_tcp_header


def test_monitor_defaults_and_lifecycle():
    engine = PacketMonitorEngine(interface="eth0")
    engine.start()
    status = engine.get_status()
    assert status["status"] == "ACTIVE"
    assert status["interface"] == "eth0"
    assert status["packets_observed"] == 0
    engine.stop()
    assert engine.get_status()["status"] == "STOPPED"


def test_monitor_process_raw_frame_and_buffer():
    engine = PacketMonitorEngine()
    
    # Send TCP packet
    tcp = make_tcp_header(src_port=51234, dst_port=80, flags=0x02)
    ip_pkt = make_ipv4_packet(src_ip="192.168.1.50", dst_ip="93.184.216.34", protocol=6, payload=tcp)
    eth = make_eth_header() + ip_pkt

    pkt = engine.process_raw_frame(eth)
    assert pkt is not None
    assert pkt.id == 1
    assert pkt.protocol == "TCP"
    assert pkt.src_port == 51234
    assert pkt.dst_port == 80

    # Test circular buffer lookup
    by_id = engine.get_packet_by_id(1)
    assert by_id is not None
    assert by_id["id"] == 1
    assert by_id["src_ip"] == "192.168.1.50"

    latest = engine.get_latest_packet()
    assert latest is not None
    assert latest["id"] == 1


def test_monitor_policy_correlation():
    engine = PacketMonitorEngine()

    # 1. WireGuard VPN port 51820
    udp_wg = make_udp_header(src_port=41000, dst_port=51820)
    ip_wg = make_ipv4_packet(src_ip="192.168.1.15", dst_ip="198.51.100.2", protocol=17, payload=udp_wg)
    pkt_wg = engine.process_raw_frame(make_eth_header() + ip_wg)
    assert pkt_wg is not None
    assert pkt_wg.policy_match is not None
    assert "WireGuard" in pkt_wg.policy_match
    assert pkt_wg.policy_action == "MATCH"

    # 2. DNS query port 53
    udp_dns = make_udp_header(src_port=54321, dst_port=53)
    ip_dns = make_ipv4_packet(src_ip="192.168.1.15", dst_ip="1.1.1.1", protocol=17, payload=udp_dns)
    pkt_dns = engine.process_raw_frame(make_eth_header() + ip_dns)
    assert pkt_dns is not None
    assert "DNS" in pkt_dns.policy_match
    assert pkt_dns.policy_action == "OBSERVED"

    # 3. OpenVPN port 1194
    udp_ovpn = make_udp_header(src_port=42000, dst_port=1194)
    ip_ovpn = make_ipv4_packet(src_ip="192.168.1.20", dst_ip="203.0.113.5", protocol=17, payload=udp_ovpn)
    pkt_ovpn = engine.process_raw_frame(make_eth_header() + ip_ovpn)
    assert pkt_ovpn is not None
    assert "OpenVPN" in pkt_ovpn.policy_match
    assert pkt_ovpn.policy_action == "MATCH"


def test_monitor_stats_breakdown():
    engine = PacketMonitorEngine()

    # Ingest 3 TCP and 1 UDP packets
    tcp_raw = make_eth_header() + make_ipv4_packet("192.168.1.1", "1.1.1.1", 6, make_tcp_header(1000, 443))
    udp_raw = make_eth_header() + make_ipv4_packet("192.168.1.2", "8.8.8.8", 17, make_udp_header(2000, 53))

    for _ in range(3):
        engine.process_raw_frame(tcp_raw)
    engine.process_raw_frame(udp_raw)

    stats = engine.get_stats()
    assert stats["packets_observed"] == 4
    assert stats["tcp_packets"] == 3
    assert stats["udp_packets"] == 1
    assert stats["tcp_percentage"] == 75.0
    assert stats["udp_percentage"] == 25.0


def test_monitor_device_correlation():
    device_tracker = DeviceTracker()
    device_tracker.record_query("192.168.1.77")
    device_tracker.set_device_hostname("192.168.1.77", "MacBook-Air")

    engine = PacketMonitorEngine(device_tracker=device_tracker)
    frame = make_eth_header() + make_ipv4_packet("192.168.1.77", "1.1.1.1", 17, make_udp_header(4000, 53))

    
    pkt = engine.process_raw_frame(frame)
    assert pkt is not None
    assert pkt.device_name == "MacBook-Air"
