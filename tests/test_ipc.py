"""Unit tests for IPC Server and FocusGuardClient communication."""

import asyncio
from pathlib import Path
import pytest
from focusguard.cli.client import FocusGuardClient, DaemonError
from focusguard.core.policy import PolicyEngine
from focusguard.dns.sinkhole import DomainSinkhole
from focusguard.service.ipc_server import IPCServer
from focusguard.storage.log_store import EventLogStore
from focusguard.storage.state import StateManager


@pytest.mark.anyio
async def test_ipc_roundtrip(tmp_path: Path):
    sinkhole = DomainSinkhole(block_doh=False)
    state_mgr = StateManager(data_dir=tmp_path / "data")
    log_store = EventLogStore(db_path=tmp_path / "events.db")
    engine = PolicyEngine(sinkhole, state_mgr, log_store)

    ipc_server = IPCServer(engine)
    await ipc_server.start()

    client = FocusGuardClient()

    try:
        # Run synchronous client commands in thread so the test's asyncio event loop can serve them
        res = await asyncio.to_thread(client.send_command, "ping")
        assert res == "pong"

        # Status
        status = await asyncio.to_thread(client.send_command, "status")
        assert "session" in status
        assert status["session"]["status"] == "IDLE"

        # Add domain
        res_add = await asyncio.to_thread(client.send_command, "add", {"domain": "reddit.com", "include_companions": False})
        assert "reddit.com" in res_add["added"]

        # List
        res_list = await asyncio.to_thread(client.send_command, "list")
        assert "reddit.com" in res_list["permanent_domains"]

        # Start locked session
        res_session = await asyncio.to_thread(client.send_command, "start", {"duration": "1h", "domains": ["reddit.com"]})
        assert res_session["status"] == "LOCKED"

        # Try to stop (must fail due to anti-impulse lock!)
        with pytest.raises(DaemonError) as exc_info:
            await asyncio.to_thread(client.send_command, "stop")
        assert "LOCKED FOCUS SESSION" in str(exc_info.value)

    finally:
        await ipc_server.stop()
