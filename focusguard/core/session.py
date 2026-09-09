"""Locked-Session State Machine with Anti-Impulse Enforcement."""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from typing import Any

from focusguard.core.time_guard import (
    get_current_utc,
    get_system_boot_id,
    format_remaining_seconds,
    TimeTamperingError,
)
from focusguard.storage.state import SessionState


class LockedSessionError(RuntimeError):
    """
    Raised when a user attempts to stop, modify, or bypass an active locked focus session.
    """

    def __init__(self, expires_at_iso: str, remaining_seconds: float) -> None:
        self.expires_at_iso = expires_at_iso
        self.remaining_seconds = remaining_seconds
        remaining_str = format_remaining_seconds(remaining_seconds)
        super().__init__(
            f"LOCKED FOCUS SESSION IN PROGRESS.\n"
            f"Modification and cancellation are disabled until: {expires_at_iso}\n"
            f"Time remaining: {remaining_str}\n"
            f"Anti-impulse guard active. Stay focused!"
        )


class SessionManager:
    """
    Manages the lifecycle, state transitions, and lock enforcement for focus sessions.
    """

    def __init__(self, initial_state: SessionState | None = None) -> None:
        self.state = initial_state or SessionState()

    @property
    def is_locked(self) -> bool:
        return self.state.status == "LOCKED"

    def get_remaining_seconds(self, now: datetime.datetime | None = None) -> float:
        """Returns remaining seconds in current locked session, or 0 if not locked."""
        if not self.is_locked or not self.state.expires_at_utc:
            return 0.0

        now = now or get_current_utc()
        expires_at = datetime.datetime.fromisoformat(self.state.expires_at_utc)
        remaining = (expires_at - now).total_seconds()
        return max(0.0, remaining)

    def start_session(
        self,
        expires_at_utc: datetime.datetime,
        duration_seconds: int,
        domains: list[str],
        services: list[str] | None = None,
        now: datetime.datetime | None = None,
    ) -> SessionState:
        """
        Transition into a LOCKED focus session.
        """
        now = now or get_current_utc()

        # Check if already active
        if self.is_locked:
            rem = self.get_remaining_seconds(now)
            if rem > 0:
                raise LockedSessionError(self.state.expires_at_utc or "", rem)

        session_id = str(uuid.uuid4())
        boot_id = get_system_boot_id()

        self.state = SessionState(
            status="LOCKED",
            session_id=session_id,
            created_at_utc=now.isoformat(),
            expires_at_utc=expires_at_utc.isoformat(),
            duration_seconds=duration_seconds,
            session_domains=list(domains),
            session_services=list(services or []),
            boot_id=boot_id,
        )
        return self.state

    def check_expiration(self, now: datetime.datetime | None = None) -> tuple[bool, str]:
        """
        Evaluate if session has expired or if clock tampering occurred.
        Returns: (has_transitioned_to_expired: bool, message: str)
        """
        if not self.is_locked:
            return False, "Not locked"

        now = now or get_current_utc()

        # Anti-tamper check: ensure clock didn't travel back before creation time
        if self.state.created_at_utc:
            created_at = datetime.datetime.fromisoformat(self.state.created_at_utc)
            if now < created_at:
                # System clock was moved backwards!
                return False, "Clock rollback detected: remaining in locked mode."

        expires_at = datetime.datetime.fromisoformat(self.state.expires_at_utc or "")
        if now >= expires_at:
            # Session expired naturally!
            self.state.status = "EXPIRED"
            return True, "Focus session reached expiration time and completed successfully."

        return False, "Session still active"

    def release_expired(self) -> None:
        """Reset state to IDLE after expiration is handled."""
        self.state = SessionState(status="IDLE")

    def assert_not_locked(self) -> None:
        """
        Enforce anti-impulse lock: raises LockedSessionError if a session is currently active.
        """
        if self.is_locked:
            rem = self.get_remaining_seconds()
            if rem > 0:
                raise LockedSessionError(self.state.expires_at_utc or "", rem)
            else:
                # Expired but not yet formally transitioned
                self.check_expiration()

    def get_summary(self) -> dict[str, Any]:
        """Return human-readable session summary dictionary."""
        rem = self.get_remaining_seconds()
        return {
            "status": self.state.status,
            "session_id": self.state.session_id,
            "created_at": self.state.created_at_utc,
            "expires_at": self.state.expires_at_utc,
            "duration_seconds": self.state.duration_seconds,
            "remaining_seconds": int(rem),
            "remaining_formatted": format_remaining_seconds(rem),
            "domains": self.state.session_domains,
            "domain_count": len(self.state.session_domains),
            "services": getattr(self.state, "session_services", []),
            "service_count": len(getattr(self.state, "session_services", [])),
        }
