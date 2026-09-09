"""Unit tests for traffic flow logging and statistical analytics."""

from pathlib import Path
import pytest
from focusguard.storage.log_store import EventLogStore


def test_flow_recording_and_stats(tmp_path: Path):
    db_file = tmp_path / "test_flows.db"
    store = EventLogStore(db_path=db_file, max_flows=100)

    # Record some allowed queries
    store.record_flow("192.168.1.10", "github.com", 1, "ALLOWED", "permitted")
    store.record_flow("192.168.1.10", "stackoverflow.com", 1, "ALLOWED", "permitted")
    store.record_flow("192.168.1.25", "wikipedia.org", 1, "ALLOWED", "permitted")

    # Record some blocked queries
    store.record_flow("192.168.1.10", "youtube.com", 1, "BLOCKED", "blocked_by_policy")
    store.record_flow("192.168.1.10", "youtube.com", 1, "BLOCKED", "blocked_by_policy")
    store.record_flow("192.168.1.25", "facebook.com", 1, "BLOCKED", "blocked_by_policy")
    store.record_flow("192.168.1.25", "youtube.com", 1, "BLOCKED", "blocked_by_policy")

    stats = store.get_stats()
    assert stats["total_queries"] == 7
    assert stats["blocked_queries"] == 4
    assert stats["allowed_queries"] == 3
    assert stats["unique_devices"] == 2
    assert stats["unique_domains"] == 5

    # Top blocked domains
    top_domains = stats["top_blocked_domains"]
    assert len(top_domains) >= 2
    assert top_domains[0]["domain"] == "youtube.com"
    assert top_domains[0]["count"] == 3
    assert top_domains[1]["domain"] == "facebook.com"
    assert top_domains[1]["count"] == 1

    # Device breakdown
    devs = stats["device_breakdown"]
    assert len(devs) == 2


def test_flow_circular_pruning(tmp_path: Path):
    db_file = tmp_path / "prune_test.db"
    store = EventLogStore(db_path=db_file, max_flows=5)

    for i in range(12):
        store.record_flow("192.168.1.10", f"domain{i}.com", 1, "ALLOWED", "permitted")

    flows = store.get_recent_flows(limit=50)
    assert len(flows) == 5
    # The most recent should be domain11.com
    assert flows[0]["domain"] == "domain11.com"


def test_filtered_flow_retrieval(tmp_path: Path):
    db_file = tmp_path / "filter_test.db"
    store = EventLogStore(db_path=db_file)

    store.record_flow("192.168.1.5", "youtube.com", 1, "BLOCKED", "policy")
    store.record_flow("192.168.1.5", "github.com", 1, "ALLOWED", "policy")
    store.record_flow("192.168.1.99", "reddit.com", 1, "BLOCKED", "policy")

    # Filter blocked only
    blocked = store.get_recent_flows(blocked_only=True)
    assert len(blocked) == 2

    # Filter by device
    dev_flows = store.get_recent_flows(client_ip="192.168.1.99")
    assert len(dev_flows) == 1
    assert dev_flows[0]["domain"] == "reddit.com"

    # Filter by domain
    yt_flows = store.get_recent_flows(domain="youtube")
    assert len(yt_flows) == 1
