"""Privacy-preserving, circular SQLite event, audit, and network flow store."""

from __future__ import annotations

import datetime
from pathlib import Path
import sqlite3
from typing import Any


class EventLogStore:
    """
    Circular audit, operational event, and network flow log with automatic retention limits.
    Prevents storage exhaustion on DietPi SD cards.
    """

    DEFAULT_MAX_EVENTS = 1000
    DEFAULT_MAX_FLOWS = 5000

    def __init__(
        self,
        db_path: Path | str | None = None,
        max_entries: int = DEFAULT_MAX_EVENTS,
        max_flows: int = DEFAULT_MAX_FLOWS,
    ) -> None:
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
        self.max_flows = max_flows
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            # Operational events table (audit, policy changes, reboots)
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

            # Network traffic flows table (for real-time monitoring and analytics)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS flows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    client_ip TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    qtype INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    session_id TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_flows_ts ON flows(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_flows_action ON flows(action)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_flows_client ON flows(client_ip)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_flows_domain ON flows(domain)")
            conn.commit()

    def record(self, category: str, action: str, details: str = "") -> None:
        """Record an operational audit event and enforce circular cap."""
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO events (timestamp, category, action, details) VALUES (?, ?, ?, ?)",
                (ts, category, action, details),
            )
            # Enforce max limit
            conn.execute("""
                DELETE FROM events WHERE id IN (
                    SELECT id FROM events ORDER BY id DESC LIMIT -1 OFFSET ?
                )
            """, (self.max_entries,))
            conn.commit()

    def record_flow(
        self,
        client_ip: str,
        domain: str,
        qtype: int,
        action: str,
        reason: str,
        session_id: str | None = None,
        timestamp: str | None = None,
    ) -> None:
        """Record a network flow query (ALLOWED or BLOCKED) and enforce circular cap."""
        ts = timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()
        clean_domain = domain.strip(". \t\r\n").lower()
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO flows 
                   (timestamp, client_ip, domain, qtype, action, reason, session_id) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (ts, client_ip, clean_domain, qtype, action, reason, session_id),
            )
            # Prune oldest entries when exceeding max_flows
            conn.execute("""
                DELETE FROM flows WHERE id IN (
                    SELECT id FROM flows ORDER BY id DESC LIMIT -1 OFFSET ?
                )
            """, (self.max_flows,))
            conn.commit()

    def get_recent(self, limit: int = 50, category: str | None = None) -> list[dict[str, Any]]:
        """Retrieve recent operational events sorted by newest first."""
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

    def get_recent_flows(
        self,
        limit: int = 50,
        blocked_only: bool = False,
        client_ip: str | None = None,
        domain: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve recent network flow records with optional filters."""
        query = "SELECT timestamp, client_ip, domain, qtype, action, reason, session_id FROM flows WHERE 1=1"
        params: list[Any] = []

        if blocked_only:
            query += " AND action = 'BLOCKED'"
        if client_ip:
            query += " AND client_ip = ?"
            params.append(client_ip)
        if domain:
            query += " AND domain LIKE ?"
            params.append(f"%{domain.lower()}%")

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._get_conn() as conn:
            cursor = conn.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]

    def get_stats(self, session_id: str | None = None) -> dict[str, Any]:
        """Compute aggregate traffic and blocking metrics."""
        with self._get_conn() as conn:
            clause = "WHERE session_id = ?" if session_id else ""
            params = [session_id] if session_id else []

            # Total, Allowed, Blocked counts
            cursor = conn.execute(
                f"""
                SELECT 
                    COUNT(*) AS total_queries,
                    SUM(CASE WHEN action = 'BLOCKED' THEN 1 ELSE 0 END) AS blocked_queries,
                    SUM(CASE WHEN action = 'ALLOWED' THEN 1 ELSE 0 END) AS allowed_queries,
                    COUNT(DISTINCT client_ip) AS unique_devices,
                    COUNT(DISTINCT domain) AS unique_domains
                FROM flows {clause}
                """,
                params,
            )
            row = cursor.fetchone()
            total = row["total_queries"] or 0
            blocked = row["blocked_queries"] or 0
            allowed = row["allowed_queries"] or 0
            devices = row["unique_devices"] or 0
            domains = row["unique_domains"] or 0
            rate = round((blocked / total * 100), 1) if total > 0 else 0.0

            # Top blocked domains
            top_domains_cursor = conn.execute(
                f"""
                SELECT domain, COUNT(*) as count 
                FROM flows 
                {('WHERE ' + ('session_id = ? AND ' if session_id else '') + "action = 'BLOCKED'") if session_id else "WHERE action = 'BLOCKED'"}
                GROUP BY domain 
                ORDER BY count DESC 
                LIMIT 10
                """,
                params,
            )
            top_domains = [{"domain": r["domain"], "count": r["count"]} for r in top_domains_cursor.fetchall()]

            # Active device breakdown
            devices_cursor = conn.execute(
                f"""
                SELECT 
                    client_ip, 
                    COUNT(*) as total_queries,
                    SUM(CASE WHEN action = 'BLOCKED' THEN 1 ELSE 0 END) as blocked_queries
                FROM flows {clause}
                GROUP BY client_ip 
                ORDER BY total_queries DESC 
                LIMIT 10
                """,
                params,
            )
            device_breakdown = [
                {
                    "client_ip": r["client_ip"],
                    "total_queries": r["total_queries"],
                    "blocked_queries": r["blocked_queries"],
                }
                for r in devices_cursor.fetchall()
            ]

            return {
                "total_queries": total,
                "blocked_queries": blocked,
                "allowed_queries": allowed,
                "block_rate_percent": rate,
                "unique_devices": devices,
                "unique_domains": domains,
                "top_blocked_domains": top_domains,
                "device_breakdown": device_breakdown,
                "is_session_scoped": bool(session_id),
            }

    def clear(self) -> None:
        """Clear all event and flow logs."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM events")
            conn.execute("DELETE FROM flows")
            conn.commit()
