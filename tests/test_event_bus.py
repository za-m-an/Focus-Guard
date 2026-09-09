"""Unit tests for EventBus pub/sub flow streaming."""

import pytest
from focusguard.service.event_bus import EventBus, FlowEvent


@pytest.mark.anyio
async def test_event_bus_pub_sub():
    bus = EventBus()
    assert bus.subscriber_count == 0

    q1 = bus.subscribe()
    q2 = bus.subscribe()
    assert bus.subscriber_count == 2

    event = FlowEvent(
        timestamp="2026-09-09T20:00:00Z",
        client_ip="192.168.1.15",
        domain="youtube.com",
        qtype=1,
        action="BLOCKED",
        reason="blocked_by_policy",
    )

    bus.publish(event)

    ev1 = await q1.get()
    assert ev1.domain == "youtube.com"
    assert ev1.action == "BLOCKED"
    assert ev1.client_ip == "192.168.1.15"

    ev2 = await q2.get()
    assert ev2.domain == "youtube.com"

    bus.unsubscribe(q1)
    assert bus.subscriber_count == 1
