"""Unit tests for PolicyEngine domain management and locked session lifecycle."""

from pathlib import Path
import pytest
from focusguard.core.policy import PolicyEngine
from focusguard.core.session import LockedSessionError
from focusguard.dns.sinkhole import DomainSinkhole
from focusguard.storage.log_store import EventLogStore
from focusguard.storage.state import StateManager


@pytest.fixture
def policy_engine(tmp_path: Path):
    sinkhole = DomainSinkhole(block_doh=False)
    state_mgr = StateManager(data_dir=tmp_path / "data")
    log_store = EventLogStore(db_path=tmp_path / "events.db")
    return PolicyEngine(sinkhole=sinkhole, state_manager=state_mgr, log_store=log_store)


def test_add_and_remove_domain(policy_engine: PolicyEngine):
    added = policy_engine.add_permanent_domain("youtube.com", include_companions=True)
    assert "youtube.com" in added
    assert "googlevideo.com" in added
    assert "youtube.com" in policy_engine.config.permanent_domains

    # Sinks should now block youtube.com
    blocked, _ = policy_engine.sinkhole.is_blocked("youtube.com")
    assert blocked is True

    # Remove youtube.com
    removed = policy_engine.remove_permanent_domain("youtube.com")
    assert removed == "youtube.com"
    assert "youtube.com" not in policy_engine.config.permanent_domains


def test_locked_session_rejects_modifications(policy_engine: PolicyEngine):
    # Start focus session for 1 hour
    policy_engine.start_focus_session(
        duration_str="1h",
        custom_domains=["reddit.com"],
        include_companions=False,
    )

    assert policy_engine.session_mgr.is_locked
    # Attempting to remove domain or stop must fail!
    with pytest.raises(LockedSessionError):
        policy_engine.remove_permanent_domain("reddit.com")

    with pytest.raises(LockedSessionError):
        policy_engine.stop_focus_session()

    # Even adding is protected or rejected during locked session
    with pytest.raises(LockedSessionError):
        policy_engine.add_permanent_domain("facebook.com")


def test_reboot_recovery(tmp_path: Path):
    sinkhole1 = DomainSinkhole(block_doh=False)
    state_dir = tmp_path / "data"
    log_db = tmp_path / "events.db"
    engine1 = PolicyEngine(sinkhole1, StateManager(state_dir), EventLogStore(log_db))

    # Add permanent domain
    engine1.add_permanent_domain("facebook.com", include_companions=False)
    # Start 2-hour locked session
    engine1.start_focus_session(duration_str="2h", custom_domains=["instagram.com"])

    assert engine1.session_mgr.is_locked

    # Simulate server reboot: new process loads from the same data directory
    sinkhole2 = DomainSinkhole(block_doh=False)
    engine2 = PolicyEngine(sinkhole2, StateManager(state_dir), EventLogStore(log_db))

    # Should automatically resume locked session
    assert engine2.session_mgr.is_locked
    assert "facebook.com" in engine2.config.permanent_domains
    assert "instagram.com" in engine2.session_mgr.state.session_domains

    # Sinkhole in new process must be blocking both
    blocked_fb, _ = engine2.sinkhole.is_blocked("facebook.com")
    blocked_ig, _ = engine2.sinkhole.is_blocked("instagram.com")
    assert blocked_fb is True
    assert blocked_ig is True


def test_permanent_service_blocking(policy_engine: PolicyEngine):
    # Block Instagram service
    added = policy_engine.block_permanent_service("instagram")
    assert "instagram" in policy_engine.config.permanent_services
    assert added["id"] == "instagram"
    assert added["name"] == "Instagram"


    # Domain evaluation should now identify it as blocked by service policy
    action, reason = policy_engine.evaluate_domain("instagram.com")
    assert action == "BLOCKED"
    assert "Instagram" in reason


    # Unblock Instagram service
    removed = policy_engine.unblock_permanent_service("instagram")
    assert "instagram" not in policy_engine.config.permanent_services


def test_locked_session_rejects_service_unblock(policy_engine: PolicyEngine):
    policy_engine.block_permanent_service("tiktok")
    policy_engine.start_focus_session(duration_str="1h", custom_domains=[])

    assert policy_engine.session_mgr.is_locked
    with pytest.raises(LockedSessionError):
        policy_engine.unblock_permanent_service("tiktok")

