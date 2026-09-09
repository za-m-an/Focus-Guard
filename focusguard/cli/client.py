"""IPC client for FocusGuard CLI communicating with the background daemon."""

from __future__ import annotations

import json
from pathlib import Path
import socket
from typing import Any, Generator

from focusguard.service.ipc_server import DEFAULT_SOCKET_PATH, FALLBACK_PORT


class DaemonError(RuntimeError):
    """Raised when the daemon returns an error."""
    pass


class ServiceNotRunningError(RuntimeError):
    """Raised when unable to connect to the FocusGuard daemon."""
    pass


class FocusGuardClient:
    """
    Synchronous / lightweight socket client for CLI commands and real-time streaming.
    """

    def __init__(self, socket_path: Path | str | None = None, timeout: float = 4.0) -> None:
        self.socket_path = Path(socket_path) if socket_path else DEFAULT_SOCKET_PATH
        self.timeout = timeout

    def _connect(self, timeout: float | None = None) -> socket.socket:
        t = timeout if timeout is not None else self.timeout

        # 1. Try Unix socket if supported on platform and file exists
        if hasattr(socket, "AF_UNIX") and self.socket_path.exists():
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(t)
                sock.connect(str(self.socket_path))
                return sock
            except OSError:
                pass

        # 2. Check fallback home socket if primary didn't work
        if hasattr(socket, "AF_UNIX"):
            user_socket = Path.home() / ".focusguard" / "focusguard.sock"
            if user_socket.exists():
                try:
                    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    sock.settimeout(t)
                    sock.connect(str(user_socket))
                    return sock
                except OSError:
                    pass

        # 3. Try loopback TCP fallback (Windows or development)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(t)
            sock.connect(("127.0.0.1", FALLBACK_PORT))
            return sock
        except OSError:
            raise ServiceNotRunningError(
                "Cannot connect to FocusGuard service.\n"
                "Ensure the daemon is running:\n"
                "  Linux (DietPi): sudo systemctl status focusguard\n"
                "  Development:    focusguardd"
            )

    def send_command(self, action: str, params: dict[str, Any] | None = None) -> Any:
        """
        Connect to daemon, send command, receive and parse response.
        """
        request_bytes = json.dumps({"action": action, "params": params or {}}).encode("utf-8") + b"\n"
        sock = self._connect()

        try:
            sock.sendall(request_bytes)
            # Read response line
            buffer = bytearray()
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buffer.extend(chunk)
                if b"\n" in buffer:
                    break

            if not buffer:
                raise DaemonError("Daemon closed connection without returning response.")

            resp_line = buffer.split(b"\n", 1)[0]
            resp_dict = json.loads(resp_line.decode("utf-8"))

            if not resp_dict.get("ok"):
                error_msg = resp_dict.get("error", "Unknown error")
                raise DaemonError(error_msg)

            return resp_dict.get("result")

        finally:
            sock.close()

    def stream_monitor(self, params: dict[str, Any] | None = None) -> Generator[dict[str, Any], None, None]:
        """
        Connect to daemon, request live flow monitor stream, and yield FlowEvents in real-time.
        """
        sock = self._connect(timeout=None)
        request_bytes = json.dumps({"action": "monitor", "params": params or {}}).encode("utf-8") + b"\n"
        sock.sendall(request_bytes)

        buffer = bytearray()
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buffer.extend(chunk)
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if not line:
                        continue
                    data = json.loads(line.decode("utf-8"))
                    if "event" in data:
                        yield data["event"]
        finally:
            sock.close()
