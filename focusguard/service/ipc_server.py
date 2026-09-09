"""Local IPC Server for secure communication between CLI and FocusGuard daemon, with real-time event streaming."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
import socket
from typing import Any

from focusguard.core.policy import PolicyEngine
from focusguard.core.session import LockedSessionError
from focusguard.service.event_bus import EventBus
from focusguard.storage.log_store import EventLogStore

logger = logging.getLogger("focusguard.ipc")

DEFAULT_SOCKET_PATH = Path("/run/focusguard/focusguard.sock")
FALLBACK_PORT = 45353


class IPCServer:
    """
    Manages local IPC communication over Unix Domain Sockets with streaming support.
    """

    def __init__(
        self,
        policy_engine: PolicyEngine,
        socket_path: Path | str | None = None,
        diagnostics_runner: Any = None,
        event_bus: EventBus | None = None,
        log_store: EventLogStore | None = None,
        gateway_manager: Any = None,
        device_tracker: Any = None,
    ) -> None:
        self.policy_engine = policy_engine
        self.diagnostics_runner = diagnostics_runner
        self.event_bus = event_bus or EventBus()
        self.log_store = log_store or (policy_engine.log_store if hasattr(policy_engine, "log_store") else None)
        self.gateway_manager = gateway_manager
        self.device_tracker = device_tracker
        self.socket_path = Path(socket_path) if socket_path else DEFAULT_SOCKET_PATH
        self._server: asyncio.Server | None = None
        self._is_unix = hasattr(socket, "AF_UNIX")

    def _ensure_socket_dir(self) -> None:
        try:
            self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            fallback = Path.home() / ".focusguard" / "focusguard.sock"
            fallback.parent.mkdir(parents=True, exist_ok=True)
            self.socket_path = fallback

    async def handle_request(self, request_dict: dict[str, Any]) -> dict[str, Any]:
        """Dispatch IPC command to policy engine, storage, or diagnostics."""
        action = request_dict.get("action", "")
        params = request_dict.get("params", {})

        try:
            if action == "ping":
                return {"ok": True, "result": "pong"}

            elif action == "status":
                status = self.policy_engine.get_status()
                if self.gateway_manager:
                    status["gateway"] = self.gateway_manager.get_gateway_status()
                return {"ok": True, "result": status}

            elif action == "add":
                domain = params.get("domain", "")
                companions = params.get("include_companions", True)
                added = self.policy_engine.add_permanent_domain(domain, include_companions=companions)
                return {"ok": True, "result": {"added": added}}

            elif action == "remove":
                domain = params.get("domain", "")
                removed = self.policy_engine.remove_permanent_domain(domain)
                return {"ok": True, "result": {"removed": removed}}

            elif action == "list":
                status = self.policy_engine.get_status()
                return {
                    "ok": True,
                    "result": {
                        "permanent_domains": status["policy"]["permanent_domains"],
                        "session_domains": status["session"]["domains"],
                        "is_locked": status["session"]["status"] == "LOCKED",
                    },
                }

            elif action == "start":
                duration = params.get("duration")
                until = params.get("until")
                custom_domains = params.get("domains")
                custom_services = params.get("services")
                companions = params.get("include_companions", True)
                summary = self.policy_engine.start_focus_session(
                    duration_str=duration,
                    until_str=until,
                    custom_domains=custom_domains,
                    custom_services=custom_services,
                    include_companions=companions,
                )
                return {"ok": True, "result": summary}

            elif action == "stop":
                self.policy_engine.stop_focus_session()
                return {"ok": True, "result": "Session stopped."}

            elif action == "session":
                return {"ok": True, "result": self.policy_engine.session_mgr.get_summary()}

            elif action == "services_list":
                return {"ok": True, "result": self.policy_engine.get_services_status()}

            elif action == "service_block":
                service = params.get("service", "")
                res = self.policy_engine.block_permanent_service(service)
                return {"ok": True, "result": res}

            elif action == "service_unblock":
                service = params.get("service", "")
                res = self.policy_engine.unblock_permanent_service(service)
                return {"ok": True, "result": res}

            elif action == "devices_list":
                if self.device_tracker:
                    devices = self.device_tracker.get_all_devices()
                else:
                    devices = []
                return {"ok": True, "result": devices}

            elif action == "bypass_status":
                gw_active = False
                if self.gateway_manager:
                    gw_active = self.gateway_manager.is_transparent_redirection_active()
                return {"ok": True, "result": self.policy_engine.bypass_mgr.get_bypass_status(gateway_active=gw_active)}

            elif action == "logs":
                limit = int(params.get("limit", 50))
                category = params.get("category")
                if self.log_store:
                    events = self.log_store.get_recent(limit=limit, category=category)
                else:
                    events = self.policy_engine.log_store.get_recent(limit=limit, category=category)
                return {"ok": True, "result": events}

            elif action == "stats":
                session_scoped = params.get("session_scoped", False)
                session_id = None
                if session_scoped and self.policy_engine.session_mgr.is_locked:
                    session_id = self.policy_engine.session_mgr.state.session_id

                if self.log_store:
                    stats = self.log_store.get_stats(session_id=session_id)
                else:
                    stats = {"total_queries": 0, "blocked_queries": 0, "allowed_queries": 0}
                return {"ok": True, "result": stats}

            elif action == "doctor":
                if self.diagnostics_runner:
                    report = await self.diagnostics_runner.run_checks()
                else:
                    report = {"status": "OK", "checks": []}
                return {"ok": True, "result": report}

            elif action == "gateway_status":
                if self.gateway_manager:
                    return {"ok": True, "result": self.gateway_manager.get_gateway_status()}
                return {"ok": True, "result": {"gateway_capable": False, "mode": "STANDARD_DNS"}}

            elif action == "gateway_enable":
                if self.gateway_manager:
                    success, msg = self.gateway_manager.enable_transparent_redirection()
                    return {"ok": success, "result": msg, "error": None if success else msg}
                return {"ok": False, "error": "Gateway manager not initialized."}

            elif action == "gateway_disable":
                # Strict anti-impulse lock: cannot disable gateway if focus session is locked!
                self.policy_engine.session_mgr.assert_not_locked()
                if self.gateway_manager:
                    success, msg = self.gateway_manager.disable_transparent_redirection()
                    return {"ok": success, "result": msg, "error": None if success else msg}
                return {"ok": False, "error": "Gateway manager not initialized."}

            else:
                return {"ok": False, "error": f"Unknown action '{action}'"}

        except LockedSessionError as e:
            return {"ok": False, "error": str(e), "is_locked": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _stream_monitor(
        self, params: dict[str, Any], reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Stream real-time flow events to the client."""
        blocked_only = bool(params.get("blocked_only", False))
        device_filter = params.get("device", "").strip()
        domain_filter = params.get("domain", "").strip().lower()
        service_filter = params.get("service", "").strip().lower()

        queue = self.event_bus.subscribe(maxsize=200)

        # Send initial confirmation
        init_resp = json.dumps({"ok": True, "streaming": True}).encode("utf-8") + b"\n"
        writer.write(init_resp)
        await writer.drain()

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=10.0)
                except asyncio.TimeoutError:
                    # Emit periodic keepalive heartbeat so connection never goes stale
                    writer.write(b'{"heartbeat": true}\n')
                    await writer.drain()
                    continue

                # Apply filters
                if blocked_only and event.action != "BLOCKED":
                    continue
                if device_filter and event.client_ip != device_filter:
                    continue
                if domain_filter and domain_filter not in event.domain.lower():
                    continue
                if service_filter and (not event.service or service_filter not in event.service.lower()):
                    continue

                event.session_active = self.policy_engine.session_mgr.is_locked
                payload = json.dumps({"event": event.to_dict()}).encode("utf-8") + b"\n"
                writer.write(payload)
                await writer.drain()
        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
            pass
        finally:
            self.event_bus.unsubscribe(queue)

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                try:
                    request = json.loads(line.decode("utf-8"))
                except Exception as e:
                    writer.write(json.dumps({"ok": False, "error": f"Invalid JSON: {e}"}).encode("utf-8") + b"\n")
                    await writer.drain()
                    continue

                action = request.get("action", "")
                params = request.get("params", {})

                # Check if this is a live monitoring stream request
                if action == "monitor":
                    await self._stream_monitor(params, reader, writer)
                    break

                response = await self.handle_request(request)
                out_bytes = json.dumps(response).encode("utf-8") + b"\n"
                writer.write(out_bytes)
                await writer.drain()
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def start(self) -> None:
        """Start the IPC socket server."""
        if self._is_unix:
            self._ensure_socket_dir()
            if self.socket_path.exists():
                try:
                    self.socket_path.unlink()
                except OSError:
                    pass

            try:
                self._server = await asyncio.start_unix_server(
                    self._handle_client, path=str(self.socket_path)
                )
                try:
                    os.chmod(self.socket_path, 0o660)
                except OSError:
                    pass
                logger.info("IPC server listening on Unix socket: %s", self.socket_path)
                return
            except Exception as e:
                logger.warning("Could not bind Unix domain socket (%s): %s. Falling back to loopback TCP.", self.socket_path, e)

        self._server = await asyncio.start_server(
            self._handle_client, host="127.0.0.1", port=FALLBACK_PORT
        )
        logger.info("IPC server listening on loopback TCP 127.0.0.1:%d", FALLBACK_PORT)

    async def stop(self) -> None:
        """Close IPC socket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        if self._is_unix and self.socket_path.exists():
            try:
                self.socket_path.unlink()
            except OSError:
                pass
        logger.info("IPC server stopped.")
