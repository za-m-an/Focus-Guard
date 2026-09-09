"""FocusGuard Background Daemon Service with Real-Time Event Bus and Gateway Management."""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path
import signal
import sys

from focusguard.core.policy import PolicyEngine
from focusguard.dns.resolver import DNSResolver
from focusguard.dns.server import DNSServer
from focusguard.dns.sinkhole import DomainSinkhole
from focusguard.network.diagnostics import DiagnosticsRunner
from focusguard.network.gateway import NetworkGatewayManager
from focusguard.service.event_bus import EventBus
from focusguard.service.ipc_server import IPCServer
from focusguard.storage.log_store import EventLogStore
from focusguard.storage.state import StateManager
from focusguard.version import __version__

logger = logging.getLogger("focusguard")


class FocusGuardDaemon:
    """
    Main server appliance daemon running DNS filtering, policy enforcement,
    network gateway redirection, and real-time IPC streaming.
    """

    def __init__(
        self,
        data_dir: Path | str | None = None,
        socket_path: Path | str | None = None,
        dns_port: int | None = None,
        auto_gateway: bool = True,
    ) -> None:
        self.state_mgr = StateManager(data_dir=data_dir)
        self.log_store = EventLogStore(
            db_path=Path(data_dir) / "events.db" if data_dir else None
        )
        self.sinkhole = DomainSinkhole(block_doh=True)
        self.policy_engine = PolicyEngine(
            sinkhole=self.sinkhole,
            state_manager=self.state_mgr,
            log_store=self.log_store,
        )

        self.event_bus = EventBus()

        # DNS resolver and port
        port = dns_port or self.policy_engine.config.dns_port
        upstreams = [
            (str(u[0]), int(u[1])) for u in self.policy_engine.config.upstreams
        ]
        self.resolver = DNSResolver(upstreams=upstreams)

        # Gateway and transparent redirection manager
        self.gateway = NetworkGatewayManager(dns_port=port)
        self.auto_gateway = auto_gateway

        def on_blocked_query(client_ip: str, domain: str, qtype: int) -> None:
            self.log_store.record("dns_block", "query_sinkholed", f"Domain: {domain} from {client_ip}")

        def on_flow_recorded(client_ip: str, domain: str, qtype: int, action: str, reason: str) -> None:
            sess_id = self.policy_engine.session_mgr.state.session_id if self.policy_engine.session_mgr.is_locked else None
            self.log_store.record_flow(
                client_ip=client_ip,
                domain=domain,
                qtype=qtype,
                action=action,
                reason=reason,
                session_id=sess_id,
            )

        self.dns_server = DNSServer(
            sinkhole=self.sinkhole,
            resolver=self.resolver,
            port=port,
            on_block_callback=on_blocked_query,
            flow_callback=on_flow_recorded,
            event_bus=self.event_bus,
        )

        self.diagnostics = DiagnosticsRunner(self.policy_engine, gateway_manager=self.gateway)
        self.ipc_server = IPCServer(
            policy_engine=self.policy_engine,
            socket_path=socket_path,
            diagnostics_runner=self.diagnostics,
            event_bus=self.event_bus,
            log_store=self.log_store,
            gateway_manager=self.gateway,
        )
        self._running = False

    async def _heartbeat_loop(self) -> None:
        """Runs every second: evaluates session timer and auto-expiration."""
        while self._running:
            try:
                completed = self.policy_engine.tick()
                if completed:
                    logger.info("Focus session completed. Policy restored.")
            except Exception as e:
                logger.error("Error during policy tick: %s", e)
            await asyncio.sleep(1.0)

    async def run(self) -> None:
        """Start daemon components, enable gateway redirection, and run event loop."""
        self._running = True
        logger.info("Starting FocusGuard v%s on DietPi...", __version__)

        await self.dns_server.start()
        await self.ipc_server.start()

        # Attempt transparent redirection if in gateway mode
        if self.auto_gateway and self.gateway.is_ip_forwarding_enabled():
            success, msg = self.gateway.enable_transparent_redirection()
            if success:
                logger.info("Transparent gateway redirection initialized: %s", msg)

        heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        stop_event = asyncio.Event()

        def _handle_stop(*_: object) -> None:
            logger.info("Shutdown signal received.")
            stop_event.set()

        # Signal handlers (Unix)
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _handle_stop)
            except (NotImplementedError, RuntimeError):
                pass

        try:
            await stop_event.wait()
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False
            heartbeat_task.cancel()
            await self.ipc_server.stop()
            await self.dns_server.stop()
            logger.info("FocusGuard daemon cleanly shut down.")


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="FocusGuard DietPi Background Daemon")
    parser.add_argument("--data-dir", help="Path to state storage directory")
    parser.add_argument("--socket", help="Path to IPC Unix socket")
    parser.add_argument("--port", type=int, help="DNS port (default: 53)")
    parser.add_argument("--no-gateway", action="store_true", help="Disable automatic transparent redirection")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")
    args = parser.parse_args()

    setup_logging(args.verbose)
    daemon = FocusGuardDaemon(
        data_dir=args.data_dir,
        socket_path=args.socket,
        dns_port=args.port,
        auto_gateway=not args.no_gateway,
    )

    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
