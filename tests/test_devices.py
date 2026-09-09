"""Tests for device discovery and tracking."""

from datetime import datetime, timezone, timedelta
import pytest
from focusguard.network.devices import DeviceTracker, DeviceInfo


def test_device_tracker_record_query():
    tracker = DeviceTracker()
    
    # Record queries from two devices
    tracker.record_query("192.168.1.50")
    tracker.record_query("192.168.1.50", is_blocked=True)
    tracker.record_query("192.168.1.60")

    devices = tracker.get_all_devices()
    assert len(devices) == 2

    dev_50 = next(d for d in devices if d["ip"] == "192.168.1.50")
    assert dev_50["total_queries"] == 2
    assert dev_50["blocked_queries"] == 1
    assert dev_50["active"] is True

    dev_60 = next(d for d in devices if d["ip"] == "192.168.1.60")
    assert dev_60["total_queries"] == 1
    assert dev_60["blocked_queries"] == 0
    assert dev_60["active"] is True


def test_device_tracker_active_count():
    tracker = DeviceTracker()
    assert tracker.active_device_count() == 0

    tracker.record_query("192.168.1.10")
    tracker.record_query("192.168.1.20")
    assert tracker.active_device_count() == 2


def test_device_inactive_calculation():
    # Artificially age the device beyond 15 minutes
    old_time = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
    dev = DeviceInfo(
        ip="192.168.1.10",
        last_seen=old_time,
        total_queries=5,
    )
    assert dev.is_active is False

    recent_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    dev_recent = DeviceInfo(
        ip="192.168.1.11",
        last_seen=recent_time,
        total_queries=2,
    )
    assert dev_recent.is_active is True


def test_device_to_dict():
    tracker = DeviceTracker()
    tracker.record_query("192.168.1.15")
    
    devices = tracker.get_all_devices()
    assert len(devices) == 1
    dev_dict = devices[0]
    assert dev_dict["ip"] == "192.168.1.15"
    assert dev_dict["total_queries"] == 1
    assert dev_dict["active"] is True
    assert "hostname" in dev_dict
    assert "last_seen" in dev_dict
