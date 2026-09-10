"""Unit tests for Locked Focus Session state machine and anti-impulse guarantees."""

import datetime
import pytest
from focusguard.core.session import SessionManager, LockedSessionError
from focusguard.core.time_guard import parse_duration_to_seconds, parse_until_to_utc


def test_duration_parser():
    assert parse_duration_to_seconds("2h") == 7200
    assert parse_duration_to_seconds("45m") == 2700
    assert parse_duration_to_seconds("1h30m") == 5400
    assert parse_duration_to_seconds("30s") == 30
    assert parse_duration_to_seconds("10") == 600  # Default minutes

    with pytest.raises(ValueError):
        parse_duration_to_seconds("invalid")


def test_session_lock_rejection():
    mgr = SessionManager()
    assert not mgr.is_locked

    now = datetime.datetime.now(datetime.timezone.utc)
    expires = now + datetime.timedelta(hours=2)

    # Start session
    mgr.start_session(
        expires_at_utc=expires,
        duration_seconds=7200,
        domains=["youtube.com", "facebook.com"],
        now=now,
    )

    assert mgr.is_locked
    # Anti-impulse check: assert_not_locked MUST raise LockedSessionError
    with pytest.raises(LockedSessionError) as exc_info:
        mgr.assert_not_locked(now=now)

    assert "LOCKED FOCUS SESSION IN PROGRESS" in str(exc_info.value)
    assert "Anti-impulse guard active" in str(exc_info.value)


def test_session_expiration_and_release():
    mgr = SessionManager()
    now = datetime.datetime.now(datetime.timezone.utc)
    expires = now + datetime.timedelta(minutes=30)

    mgr.start_session(
        expires_at_utc=expires,
        duration_seconds=1800,
        domains=["youtube.com"],
        now=now,
    )

    # Before expiration
    current = now + datetime.timedelta(minutes=15)
    expired, _ = mgr.check_expiration(now=current)
    assert expired is False
    assert mgr.is_locked

    # Exactly at expiration
    current = expires
    expired, _ = mgr.check_expiration(now=current)
    assert expired is True
    assert mgr.state.status == "EXPIRED"

    mgr.release_expired()
    assert not mgr.is_locked
    # Now assert_not_locked should succeed without raising
    mgr.assert_not_locked()


def test_clock_rollback_protection():
    mgr = SessionManager()
    start_time = datetime.datetime.now(datetime.timezone.utc)
    expires = start_time + datetime.timedelta(hours=1)

    mgr.start_session(
        expires_at_utc=expires,
        duration_seconds=3600,
        domains=["reddit.com"],
        now=start_time,
    )


    # Simulate clock tampering: user rolls back clock to before start_time
    tampered_time = start_time - datetime.timedelta(hours=2)
    expired, msg = mgr.check_expiration(now=tampered_time)

    assert expired is False
    assert "rollback detected" in msg.lower()
    assert mgr.is_locked
