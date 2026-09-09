"""Unit tests for flow tracking and connection aggregation."""

import time
import pytest
from focusguard.network.flows import FlowTracker, make_flow_key
from focusguard.network.packets import PacketMetadata


def test_make_flow_key_symmetry():
    k1 = make_flow_key("TCP", "192.168.1.15", 52144, "142.250.190.46", 443)
    k2 = make_flow_key("TCP", "142.250.190.46", 443, "192.168.1.15", 52144)
    assert k1 == k2


def test_flow_bidirectional_aggregation():
    tracker = FlowTracker()

    # Client -> Server packet
    pkt1 = PacketMetadata(
        id=1,
        timestamp="21:30:00.000",
        interface="eth0",
        direction="LAN → WAN",
        ip_version="IPv4",
        src_ip="192.168.1.15",
        dst_ip="142.250.190.46",
        protocol="TCP",
        src_port=52144,
        dst_port=443,
        length=74,
        tcp_flags=["SYN"],
    )

    flow = tracker.record_packet(pkt1)
    assert flow is not None
    assert flow.total_packets == 1
    assert flow.bytes_client_to_server == 74
    assert flow.tcp_state == "SYN_SENT"
    assert tracker.get_active_flow_count() == 1

    # Server -> Client response packet
    pkt2 = PacketMetadata(
        id=2,
        timestamp="21:30:00.020",
        interface="eth0",
        direction="WAN → LAN",
        ip_version="IPv4",
        src_ip="142.250.190.46",
        dst_ip="192.168.1.15",
        protocol="TCP",
        src_port=443,
        dst_port=52144,
        length=1480,
        tcp_flags=["SYN", "ACK"],
    )

    flow2 = tracker.record_packet(pkt2)
    assert flow2 is flow  # Same flow object
    assert flow.total_packets == 2
    assert flow.bytes_server_to_client == 1480
    assert flow.total_bytes == 1554
    assert tracker.get_active_flow_count() == 1


def test_flow_capacity_eviction():
    tracker = FlowTracker(max_flows=10)

    for i in range(15):
        pkt = PacketMetadata(
            id=i,
            timestamp="21:30:00.000",
            interface="eth0",
            direction="LAN → WAN",
            ip_version="IPv4",
            src_ip=f"192.168.1.{i+10}",
            dst_ip="8.8.8.8",
            protocol="UDP",
            src_port=10000 + i,
            dst_port=53,
            length=64,
        )
        tracker.record_packet(pkt)

    # Should not exceed maximum capacity
    assert tracker.get_active_flow_count() <= 10


def test_flow_stale_pruning():
    tracker = FlowTracker(idle_timeout=5.0)

    pkt = PacketMetadata(
        id=1,
        timestamp="21:30:00.000",
        interface="eth0",
        direction="LAN → WAN",
        ip_version="IPv4",
        src_ip="192.168.1.5",
        dst_ip="1.1.1.1",
        protocol="UDP",
        src_port=45000,
        dst_port=53,
        length=60,
    )
    flow = tracker.record_packet(pkt)
    assert flow is not None
    assert tracker.get_active_flow_count() == 1

    # Artificially age the flow past timeout
    flow.last_seen = time.time() - 10.0
    tracker._last_prune = 0.0  # Force prune on next check

    tracker._prune_stale_locked(time.time())
    assert tracker.get_active_flow_count() == 0
