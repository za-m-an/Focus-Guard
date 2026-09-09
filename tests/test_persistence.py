"""Unit tests for atomic state persistence, HMAC validation, and event log storage."""

import json
from pathlib import Path
import pytest
from focusguard.storage.state import StateManager, PersistentData, AppConfig, SessionState
from focusguard.storage.log_store import EventLogStore


def test_atomic_save_and_load(tmp_path: Path):
    mgr = StateManager(data_dir=tmp_path)
    data = PersistentData(
        config=AppConfig(permanent_domains=["youtube.com", "tiktok.com"]),
        session=SessionState(status="IDLE"),
    )
    mgr.save(data)

    loaded, is_verified = mgr.load()
    assert is_verified is True
    assert "youtube.com" in loaded.config.permanent_domains
    assert "tiktok.com" in loaded.config.permanent_domains
    assert loaded.session.status == "IDLE"


def test_hmac_tamper_detection(tmp_path: Path):
    mgr = StateManager(data_dir=tmp_path)
    data = PersistentData(
        config=AppConfig(permanent_domains=["youtube.com"]),
        session=SessionState(status="LOCKED", expires_at_utc="2026-09-10T23:30:00+00:00"),
    )
    mgr.save(data)

    # Manually tamper with state file on disk (simulate rogue edit)
    state_file = tmp_path / "state.json"
    with open(state_file, "r", encoding="utf-8") as f:
        content = json.load(f)

    # Tamper with session status
    content["session"]["status"] = "IDLE"
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(content, f)

    # Load should detect HMAC signature mismatch
    loaded, is_verified = mgr.load()
    assert is_verified is False


def test_event_log_circular(tmp_path: Path):
    db_file = tmp_path / "test_events.db"
    log = EventLogStore(db_path=db_file, max_entries=5)

    for i in range(10):
        log.record("test", f"action_{i}", f"detail_{i}")

    recent = log.get_recent(limit=50)
    # Should be capped at max_entries (5)
    assert len(recent) == 5
    # The most recent should be action_9
    assert recent[0]["action"] == "action_9"
