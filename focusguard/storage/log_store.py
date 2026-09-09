"""Privacy-preserving, circular SQLite event and audit log."""

from __future__ import annotations

import datetime
from pathlib import Path
import sqlite3
from typing import Any


class EventLogStore:
    """
    Circular audit and operational event log with automatic retention limits.
    Prevents storage exhaustion on DietPi SD cards.
    """

    DEFAULT_MAX_ENTRIES = 1000

    def __init__(self, db_path: Path | str | None = None, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        if db_path is not None:
            self.db_path = Path(db_path)
        else:
            base_dir = Path("/var/log/focusguard")
            try:
                base_dir.mkdir(parents=True, exist_ok=True)
                self.db_path = base_dir / "events.db"
            except OSError:
                fallback = Path.home() / ".focusguard"
                fallback.mkdir(parents=True, exist_ok=True)
                self.db_path = fallback / "events.db"

        self.max_entries = max_entries
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    category TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp)")
            conn.commit()

    def record(self, category: str, action: str, details: str = "") -> None:
        """Record an event and enforce circular cap."""
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO events (timestamp, category, action, details) VALUES (?, ?, ?, ?)",
                (ts, category, action, details),
            )
            # Enforce max limit: prune oldest entries if table exceeds limit
            conn.execute("""
                DELETE FROM events WHERE id IN (
                    SELECT id FROM events ORDER BY id DESC LIMIT -1 OFFSET ?
                )
            """, (self.max_entries,))
            conn.commit()

    def get_recent(self, limit: int = 50, category: str | None = None) -> list[dict[str, Any]]:
        """Retrieve recent events sorted by newest first."""
        with self._get_conn() as conn:
            if category:
                cursor = conn.execute(
                    "SELECT timestamp, category, action, details FROM events WHERE category = ? ORDER BY id DESC LIMIT ?",
                    (category, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT timestamp, category, action, details FROM events ORDER BY id DESC LIMIT ?",
                    (limit,),
                )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def clear(self) -> None:
        """Clear all event logs."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM events")
            conn.commit()
