"""Local IPC Server for secure communication between CLI and FocusGuard daemon."""

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

logger = logging.getLogger("focusguard.ipc")

DEFAULT_SOCKET_PATH = Path("/run/focusguard/focusguard.sock")
FALLBACK_PORT = 45353


class IPCServer:
    """
    Manages local IPC communication over Unix Domain Sockets (or localhost TCP fallback).
    """

    def __init__(
        self,
        policy_engine: PolicyEngine,
        socket_path: Path | str | None = None,
        diagnostics_runner: Any = None,
    ) -> None:
        self.policy_engine = policy_engine
        self.diagnostics_runner = diagnostics_runner
        self.socket_path = Path(socket_path) if socket_path else DEFAULT_SOCKET_PATH
        self._server: asyncio.Server | None = None
        self._is_unix = hasattr(socket, "AF_UNIX")

    def _ensure_socket_dir(self) -> None:
        try:
            self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Fallback to local /tmp or home directory
            fallback = Path.home() / ".focusguard" / "focusguard.sock"
            fallback.parent.mkdir(parents=True, exist_ok=True)
            self.socket_path = fallback

    async def handle_request(self, request_dict: dict[str, Any]) -> dict[str, Any]:
        """Dispatch IPC command to policy engine or diagnostics."""
        action = request_dict.get("action", "")
        params = request_dict.get("params", {})

        try:
            if action == "ping":
                return {"ok": True, "result": "pong"}

            elif action == "status":
                status = self.policy_engine.get_status()
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
                companions = params.get("include_companions", True)
                summary = self.policy_engine.start_focus_session(
                    duration_str=duration,
                    until_str=until,
                    custom_domains=custom_domains,
                    include_companions=companions,
                )
                return {"ok": True, "result": summary}

            elif action == "stop":
                self.policy_engine.stop_focus_session()
                return {"ok": True, "result": "Session stopped."}

            elif action == "session":
                return {"ok": True, "result": self.policy_engine.session_mgr.get_summary()}

            elif action == "logs":
                limit = int(params.get("limit", 50))
                category = params.get("category")
                events = self.policy_engine.log_store.get_recent(limit=limit, category=category)
                return {"ok": True, "result": events}

            elif action == "doctor":
                if self.diagnostics_runner:
                    report = await self.diagnostics_runner.run_checks()
                else:
                    report = {"status": "OK", "checks": []}
                return {"ok": True, "result": report}

            else:
                return {"ok": False, "error": f"Unknown action '{action}'"}

        except LockedSessionError as e:
            return {"ok": False, "error": str(e), "is_locked": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

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
                    response = await self.handle_request(request)
                except Exception as e:
                    response = {"ok": False, "error": f"Invalid JSON request: {e}"}

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
        # Attempt Unix domain socket first
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
                    # Set permissions so focusguard group can communicate
                    os.chmod(self.socket_path, 0o660)
                except OSError:
                    pass
                logger.info("IPC server listening on Unix socket: %s", self.socket_path)
                return
            except Exception as e:
                logger.warning("Could not bind Unix domain socket (%s): %s. Falling back to loopback TCP.", self.socket_path, e)

        # Fallback to local loopback TCP (for Windows or unsupported AF_UNIX)
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
