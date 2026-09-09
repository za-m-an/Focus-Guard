"""Robust UTC time handling, duration parsing, absolute timestamp calculations, and anti-tamper guards."""

from __future__ import annotations

import datetime
import os
import re
import uuid
from typing import Tuple


class TimeTamperingError(RuntimeError):
    """Raised when suspicious clock rollbacks or time modifications are detected."""
    pass


# Matches 2h, 45m, 1h30m, 90s, 2h15m30s
DURATION_REGEX = re.compile(
    r"^(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?(?:(?P<seconds>\d+)s)?$",
    re.IGNORECASE,
)


def get_system_boot_id() -> str:
    """Read Linux kernel boot ID or generate fallback host identifier."""
    boot_id_path = "/proc/sys/kernel/random/boot_id"
    if os.path.exists(boot_id_path):
        try:
            with open(boot_id_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            pass
    # Fallback for Windows/macOS development environments
    return str(uuid.getnode())


def get_current_utc() -> datetime.datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.datetime.now(datetime.timezone.utc)


def parse_duration_to_seconds(duration_str: str) -> int:
    """
    Parses human-readable duration strings:
      - '2h' -> 7200
      - '45m' -> 2700
      - '1h30m' -> 5400
      - '30s' -> 30
      - '4' (plain number assumed minutes or hours? strict requirement: require unit or default min)
    """
    clean = duration_str.strip().lower()
    if not clean:
        raise ValueError("Duration string cannot be empty.")

    # Plain integer: interpret as minutes
    if clean.isdigit():
        mins = int(clean)
        if mins <= 0:
            raise ValueError("Duration must be greater than 0.")
        return mins * 60

    match = DURATION_REGEX.match(clean)
    if not match or not any(match.groups()):
        raise ValueError(f"Invalid duration format '{duration_str}'. Examples: '4h', '45m', '1h30m'.")

    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)

    total = hours * 3600 + minutes * 60 + seconds
    if total <= 0:
        raise ValueError("Duration must be greater than 0.")
    return total


def parse_until_to_utc(until_str: str, now: datetime.datetime | None = None) -> datetime.datetime:
    """
    Parses target end time (e.g. '23:30', '18:00:00', '2026-09-10T23:30:00')
    and returns a timezone-aware UTC datetime.
    
    If only time (HH:MM) is given, it assumes local time today. If that time has
    already passed today, it assumes tomorrow.
    """
    now = now or get_current_utc()
    clean = until_str.strip()

    # Case 1: Full ISO-8601 string
    try:
        dt = datetime.datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        else:
            dt = dt.astimezone(datetime.timezone.utc)
        if dt <= now:
            raise ValueError(f"Expiration time '{until_str}' is in the past.")
        return dt
    except ValueError:
        pass

    # Case 2: Time string like HH:MM or HH:MM:SS
    time_parts = clean.split(":")
    if len(time_parts) in (2, 3) and all(p.isdigit() for p in time_parts):
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        second = int(time_parts[2]) if len(time_parts) == 3 else 0

        if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
            raise ValueError(f"Invalid time values in '{until_str}'.")

        # Convert local time to target datetime
        local_now = datetime.datetime.now()
        target_local = local_now.replace(hour=hour, minute=minute, second=second, microsecond=0)

        # If target has passed today, move to tomorrow
        if target_local <= local_now:
            target_local += datetime.timedelta(days=1)

        # Convert to UTC
        local_tz = datetime.datetime.now().astimezone().tzinfo
        target_aware = target_local.replace(tzinfo=local_tz).astimezone(datetime.timezone.utc)
        return target_aware

    raise ValueError(
        f"Cannot parse end time '{until_str}'. Use HH:MM (e.g. '23:30') or full ISO format (e.g. '2026-09-10T23:30:00')."
    )


def format_remaining_seconds(seconds: int | float) -> str:
    """Format seconds into HH:MM:SS."""
    sec = max(0, int(seconds))
    hours = sec // 3600
    minutes = (sec % 3600) // 60
    rem_seconds = sec % 60
    return f"{hours:02d}:{minutes:02d}:{rem_seconds:02d}"
