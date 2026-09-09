"""Atomic state persistence with HMAC signature validation."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SessionState:
    status: str = "IDLE"  # IDLE, LOCKED, EXPIRED
    session_id: str | None = None
    created_at_utc: str | None = None
    expires_at_utc: str | None = None
    duration_seconds: int = 0
    session_domains: list[str] = field(default_factory=list)
    session_services: list[str] = field(default_factory=list)
    boot_id: str | None = None


@dataclass
class AppConfig:
    permanent_domains: list[str] = field(default_factory=list)
    permanent_services: list[str] = field(default_factory=list)
    allowed_domains: list[str] = field(default_factory=list)
    allowlist_mode: bool = False
    block_doh: bool = True
    block_vpns: bool = True
    dns_port: int = 53
    upstreams: list[list[Any]] = field(
        default_factory=lambda: [["1.1.1.1", 53], ["9.9.9.9", 53], ["1.0.0.1", 53]]
    )


@dataclass
class PersistentData:
    config: AppConfig = field(default_factory=AppConfig)
    session: SessionState = field(default_factory=SessionState)
    hmac_signature: str | None = None


class StateManager:
    """
    Manages atomic writing and loading of persistent configuration and session state.
    """

    DEFAULT_DATA_DIR = Path("/var/lib/focusguard")
    STATE_FILE_NAME = "state.json"
    SECRET_FILE_NAME = ".secret"

    def __init__(self, data_dir: Path | str | None = None) -> None:
        if data_dir is not None:
            self.data_dir = Path(data_dir)
        else:
            # Fallback to local directory if /var/lib/focusguard is not writable
            self.data_dir = self.DEFAULT_DATA_DIR

        self.state_file = self.data_dir / self.STATE_FILE_NAME
        self.secret_file = self.data_dir / self.SECRET_FILE_NAME
        self._secret: bytes | None = None

    def _ensure_dir(self) -> None:
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            # If system dir is not writable (e.g. running as local test/user), use user home
            fallback = Path.home() / ".focusguard"
            fallback.mkdir(parents=True, exist_ok=True)
            self.data_dir = fallback
            self.state_file = self.data_dir / self.STATE_FILE_NAME
            self.secret_file = self.data_dir / self.SECRET_FILE_NAME

    def _get_secret(self) -> bytes:
        if self._secret is not None:
            return self._secret

        self._ensure_dir()
        if self.secret_file.exists():
            try:
                self._secret = self.secret_file.read_bytes().strip()
                if len(self._secret) >= 32:
                    return self._secret
            except OSError:
                pass

        # Generate new 32-byte cryptographically secure random secret
        new_secret = secrets.token_bytes(32)
        try:
            # Restrict permissions to owner only
            self.secret_file.write_bytes(new_secret)
            try:
                os.chmod(self.secret_file, 0o600)
            except OSError:
                pass
        except OSError:
            pass
        self._secret = new_secret
        return self._secret

    def _calculate_hmac(self, data_dict: dict[str, Any]) -> str:
        """Calculate HMAC-SHA256 signature of canonical JSON data (excluding signature field)."""
        clean_copy = dict(data_dict)
        clean_copy.pop("hmac_signature", None)
        canonical_bytes = json.dumps(clean_copy, sort_keys=True).encode("utf-8")
        secret = self._get_secret()
        return hmac.new(secret, canonical_bytes, hashlib.sha256).hexdigest()

    def save(self, data: PersistentData) -> None:
        """Atomically persist state data to disk using temporary file + rename."""
        self._ensure_dir()
        raw_dict = asdict(data)
        raw_dict["hmac_signature"] = self._calculate_hmac(raw_dict)

        tmp_file = self.data_dir / f"{self.STATE_FILE_NAME}.tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(raw_dict, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())

        # Atomic replacement guarantees zero corrupt state on sudden power loss
        os.replace(tmp_file, self.state_file)

    def load(self) -> tuple[PersistentData, bool]:
        """
        Load state from disk.
        Returns: (data, is_tamper_verified: bool)
        """
        self._ensure_dir()
        if not self.state_file.exists():
            default_data = PersistentData()
            self.save(default_data)
            return default_data, True

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                raw_dict = json.load(f)

            stored_sig = raw_dict.get("hmac_signature")
            expected_sig = self._calculate_hmac(raw_dict)
            is_verified = (stored_sig is not None) and hmac.compare_digest(stored_sig, expected_sig)

            config_raw = raw_dict.get("config", {})
            session_raw = raw_dict.get("session", {})

            data = PersistentData(
                config=AppConfig(
                    permanent_domains=config_raw.get("permanent_domains", []),
                    permanent_services=config_raw.get("permanent_services", []),
                    allowed_domains=config_raw.get("allowed_domains", []),
                    allowlist_mode=config_raw.get("allowlist_mode", False),
                    block_doh=config_raw.get("block_doh", True),
                    block_vpns=config_raw.get("block_vpns", True),
                    dns_port=config_raw.get("dns_port", 53),
                    upstreams=config_raw.get("upstreams", [["1.1.1.1", 53], ["9.9.9.9", 53]]),
                ),
                session=SessionState(
                    status=session_raw.get("status", "IDLE"),
                    session_id=session_raw.get("session_id"),
                    created_at_utc=session_raw.get("created_at_utc"),
                    expires_at_utc=session_raw.get("expires_at_utc"),
                    duration_seconds=session_raw.get("duration_seconds", 0),
                    session_domains=session_raw.get("session_domains", []),
                    session_services=session_raw.get("session_services", []),
                    boot_id=session_raw.get("boot_id"),
                ),
                hmac_signature=stored_sig,
            )
            return data, is_verified
        except Exception:
            # Corrupted file -> backup corrupted copy and return fresh default
            try:
                corrupt_backup = self.data_dir / f"{self.STATE_FILE_NAME}.corrupt"
                os.replace(self.state_file, corrupt_backup)
            except OSError:
                pass
            fallback = PersistentData()
            self.save(fallback)
            return fallback, False
