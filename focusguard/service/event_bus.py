"""Async in-memory Event Bus for broadcasting real-time network flow events."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, asdict
from typing import Any, Callable


@dataclass
class FlowEvent:
    timestamp: str
    client_ip: str
    domain: str
    qtype: int
    action: str          # "BLOCKED" or "ALLOWED"
    reason: str
    session_active: bool = False
    service: str | None = None
    bypass_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EventBus:
    """
    Publish/Subscribe event bus for real-time streaming to CLI monitor clients.
    """

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[FlowEvent]] = set()

    def subscribe(self, maxsize: int = 100) -> asyncio.Queue[FlowEvent]:
        """Create a new subscriber queue."""
        q: asyncio.Queue[FlowEvent] = asyncio.Queue(maxsize=maxsize)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[FlowEvent]) -> None:
        """Remove a subscriber queue."""
        self._subscribers.discard(q)

    def publish(self, event: FlowEvent) -> None:
        """Broadcast event to all active subscriber queues without blocking."""
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # Discard oldest event if subscriber is slow
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except Exception:
                    pass

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)
