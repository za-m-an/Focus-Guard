"""Core Policy Engine: coordinates permanent rules, focus sessions, and DNS sinkhole."""

from __future__ import annotations

import datetime
from typing import Any

from focusguard.core.normalizer import (
    normalize_domain,
    get_companion_domains,
    InvalidDomainError,
)
from focusguard.core.services import (
    SERVICE_REGISTRY,
    get_service,
    list_available_services,
    match_service_by_domain,
    get_all_domains_for_services,
)
from focusguard.network.bypass import BypassResistanceManager
from focusguard.core.session import SessionManager, LockedSessionError
from focusguard.core.time_guard import (
    get_current_utc,
    parse_duration_to_seconds,
    parse_until_to_utc,
)
from focusguard.dns.sinkhole import DomainSinkhole
from focusguard.storage.log_store import EventLogStore
from focusguard.storage.state import StateManager, PersistentData, AppConfig


class PolicyEngine:
    """
    Central coordinator of domain policies, locked focus sessions, persistence, and DNS sinkhole state.
    """

    def __init__(
        self,
        sinkhole: DomainSinkhole,
        state_manager: StateManager | None = None,
        log_store: EventLogStore | None = None,
        bypass_manager: BypassResistanceManager | None = None,
    ) -> None:
        self.sinkhole = sinkhole
        self.state_manager = state_manager or StateManager()
        self.log_store = log_store or EventLogStore()
        self.bypass_mgr = bypass_manager or BypassResistanceManager()

        # Load persisted state from disk
        persisted_data, is_valid = self.state_manager.load()
        self.config: AppConfig = persisted_data.config
        self.session_mgr = SessionManager(persisted_data.session)

        # Apply configuration to sinkhole
        self.sinkhole.block_doh = self.config.block_doh
        self.sinkhole.allowlist_mode = self.config.allowlist_mode
        self.sinkhole.set_allowed_domains(self.config.allowed_domains)

        # Check for reboot recovery: is there an unexpired locked session?
        if self.session_mgr.is_locked:
            has_expired, _ = self.session_mgr.check_expiration()
            if has_expired:
                self.session_mgr.release_expired()
                self._save_state()
                self.log_store.record("session", "reboot_recovered_expired", "Session expired during or before reboot.")
            else:
                self.log_store.record("session", "reboot_resumed_locked", f"Resumed active locked session until {self.session_mgr.state.expires_at_utc}.")

        self._refresh_sinkhole()

    def _get_all_active_blocked_domains(self) -> list[str]:
        """Combine permanent domains, services, bypass protection, and active session domains."""
        domains = set(self.config.permanent_domains)

        # 1. Include domains from permanently blocked services
        if hasattr(self.config, "permanent_services") and self.config.permanent_services:
            domains.update(get_all_domains_for_services(self.config.permanent_services))

        # 2. Include VPN bypass resistance domains if enabled
        if getattr(self.config, "block_vpns", True):
            domains.update(self.bypass_mgr.get_all_vpn_domains())

        # 3. Include DoH provider domains if enabled
        if getattr(self.config, "block_doh", True):
            domains.update(self.bypass_mgr.get_all_doh_domains())

        # 4. Include active focus session domains and services
        if self.session_mgr.is_locked:
            domains.update(self.session_mgr.state.session_domains)
            if hasattr(self.session_mgr.state, "session_services") and self.session_mgr.state.session_services:
                domains.update(get_all_domains_for_services(self.session_mgr.state.session_services))

        return sorted(domains)

    def _refresh_sinkhole(self) -> None:
        """Update in-memory sinkhole matcher with current effective domains."""
        active_domains = self._get_all_active_blocked_domains()
        self.sinkhole.set_blocked_domains(active_domains)

    def _save_state(self) -> None:
        """Persist current state to disk."""
        data = PersistentData(
            config=self.config,
            session=self.session_mgr.state,
        )
        self.state_manager.save(data)

    def add_permanent_domain(self, domain_input: str, include_companions: bool = True) -> list[str]:
        """
        Add a domain to permanent blocklist (only permitted when NOT in a locked session, or adds to permanent rules).
        """
        self.session_mgr.assert_not_locked()

        normalized = normalize_domain(domain_input)
        added = []
        if normalized not in self.config.permanent_domains:
            self.config.permanent_domains.append(normalized)
            added.append(normalized)

        if include_companions:
            for companion in get_companion_domains(normalized):
                if companion not in self.config.permanent_domains:
                    self.config.permanent_domains.append(companion)
                    added.append(companion)

        self._refresh_sinkhole()
        self._save_state()
        self.log_store.record("policy", "add_domain", f"Added: {', '.join(added) if added else normalized}")
        return added or [normalized]

    def remove_permanent_domain(self, domain_input: str) -> str:
        """
        Remove a domain from permanent blocklist.
        STRICT: Rejected with LockedSessionError if a focus session is active!
        """
        self.session_mgr.assert_not_locked()

        normalized = normalize_domain(domain_input)
        if normalized in self.config.permanent_domains:
            self.config.permanent_domains.remove(normalized)
            self._refresh_sinkhole()
            self._save_state()
            self.log_store.record("policy", "remove_domain", f"Removed: {normalized}")
            return normalized

        raise ValueError(f"Domain '{normalized}' is not in permanent blocklist.")

    def block_permanent_service(self, service_id: str) -> dict[str, Any]:
        """Add a complete distraction service to the permanent blocklist."""
        self.session_mgr.assert_not_locked()

        svc = get_service(service_id)
        if not svc:
            raise ValueError(f"Unknown service '{service_id}'. Run 'focusguard services' to view available services.")

        if not hasattr(self.config, "permanent_services"):
            self.config.permanent_services = []

        if svc.id not in self.config.permanent_services:
            self.config.permanent_services.append(svc.id)
            self._refresh_sinkhole()
            self._save_state()
            self.log_store.record("policy", "block_service", f"Permanently blocked service: {svc.name}")

        return svc.to_dict()

    def unblock_permanent_service(self, service_id: str) -> str:
        """Remove a service from the permanent blocklist (disallowed during active locked session)."""
        self.session_mgr.assert_not_locked()

        svc = get_service(service_id)
        if not svc:
            raise ValueError(f"Unknown service '{service_id}'.")

        if hasattr(self.config, "permanent_services") and svc.id in self.config.permanent_services:
            self.config.permanent_services.remove(svc.id)
            self._refresh_sinkhole()
            self._save_state()
            self.log_store.record("policy", "unblock_service", f"Unblocked service: {svc.name}")
            return svc.name

        raise ValueError(f"Service '{svc.name}' is not currently in permanent blocklist.")

    def get_services_status(self) -> list[dict[str, Any]]:
        """Return list of all registered distraction services with their current block state."""
        active_services = set(getattr(self.config, "permanent_services", []))
        if self.session_mgr.is_locked and hasattr(self.session_mgr.state, "session_services"):
            active_services.update(self.session_mgr.state.session_services)

        result = []
        for svc in SERVICE_REGISTRY.values():
            s_dict = svc.to_dict()
            s_dict["is_blocked"] = svc.id in active_services
            s_dict["is_session_scoped"] = (
                self.session_mgr.is_locked
                and hasattr(self.session_mgr.state, "session_services")
                and svc.id in self.session_mgr.state.session_services
            )
            result.append(s_dict)
        return result

    def evaluate_domain(self, domain: str) -> tuple[str, str]:
        """
        Evaluate an incoming domain query against bypass intelligence, services, and policies.
        Returns: (action: 'BLOCKED' | 'ALLOWED', reason: str)
        """
        # 1. Check bypass resistance (VPN or DoH)
        bypass_match = self.bypass_mgr.identify_bypass_attempt(domain)
        if bypass_match:
            b_type, provider = bypass_match
            if (b_type == "DoH Bypass" and self.config.block_doh) or (b_type == "VPN Bypass" and getattr(self.config, "block_vpns", True)):
                return "BLOCKED", f"{b_type}: {provider}"

        # 2. Check sinkhole status
        is_blocked = self.sinkhole.is_blocked(domain)
        if is_blocked:
            svc_name = match_service_by_domain(domain)
            if svc_name:
                return "BLOCKED", f"Service: {svc_name}"
            return "BLOCKED", "Policy Rule"

        return "ALLOWED", "No active rule matched"

    def start_focus_session(
        self,
        duration_str: str | None = None,
        until_str: str | None = None,
        custom_domains: list[str] | None = None,
        custom_services: list[str] | None = None,
        include_companions: bool = True,
    ) -> dict[str, Any]:
        """
        Start a locked focus session with duration or until timestamp.
        """
        now = get_current_utc()

        # Determine expiration timestamp
        if until_str:
            expires_at = parse_until_to_utc(until_str, now)
            duration_seconds = int((expires_at - now).total_seconds())
        elif duration_str:
            duration_seconds = parse_duration_to_seconds(duration_str)
            expires_at = now + datetime.timedelta(seconds=duration_seconds)
        else:
            raise ValueError("Must specify either duration (e.g. '2h') or end time (e.g. '23:30').")

        # Determine blocked domains and services for this session
        session_domains: set[str] = set()
        session_services: set[str] = set()

        if custom_services:
            for s in custom_services:
                svc = get_service(s)
                if svc:
                    session_services.add(svc.id)
                    session_domains.update(svc.all_domains)

        if custom_domains:
            for d in custom_domains:
                try:
                    norm = normalize_domain(d)
                    session_domains.add(norm)
                    if include_companions:
                        for comp in get_companion_domains(norm):
                            session_domains.add(comp)
                except InvalidDomainError:
                    continue

        if not custom_domains and not custom_services:
            # If no custom domains/services given, use all current permanent rules
            session_domains.update(self.config.permanent_domains)
            if hasattr(self.config, "permanent_services") and self.config.permanent_services:
                session_services.update(self.config.permanent_services)
                session_domains.update(get_all_domains_for_services(self.config.permanent_services))

        if not session_domains:
            raise ValueError("No valid domains or services specified for focus session.")

        # Activate locked session
        state = self.session_mgr.start_session(
            expires_at_utc=expires_at,
            duration_seconds=duration_seconds,
            domains=sorted(session_domains),
            services=sorted(session_services),
            now=now,
        )

        self._refresh_sinkhole()
        self._save_state()
        self.log_store.record(
            "session",
            "start_locked_session",
            f"Locked until {expires_at.isoformat()} ({len(session_domains)} domains, {len(session_services)} services)",
        )

        return self.session_mgr.get_summary()

    def stop_focus_session(self) -> None:
        """
        Stop an active focus session.
        CRITICAL ANTI-IMPULSE REQUIREMENT:
        MUST RAISE LockedSessionError IF SESSION IS ACTIVE!
        """
        self.session_mgr.assert_not_locked()

    def tick(self) -> bool:
        """
        Periodic heartbeat call (run every second by daemon).
        Checks if active session reached expiration timestamp and auto-restores previous state.
        Returns: True if session completed on this tick.
        """
        has_expired, msg = self.session_mgr.check_expiration()
        if has_expired:
            self.session_mgr.release_expired()
            self._refresh_sinkhole()
            self._save_state()
            self.log_store.record("session", "expired_auto_restored", msg)
            return True
        return False

    def get_status(self) -> dict[str, Any]:
        """Return comprehensive status overview for CLI status display."""
        active_domains = self._get_all_active_blocked_domains()
        session_info = self.session_mgr.get_summary()
        active_services = set(getattr(self.config, "permanent_services", []))
        if self.session_mgr.is_locked and hasattr(self.session_mgr.state, "session_services"):
            active_services.update(self.session_mgr.state.session_services)

        return {
            "session": session_info,
            "policy": {
                "permanent_domains": list(self.config.permanent_domains),
                "permanent_count": len(self.config.permanent_domains),
                "permanent_services": list(getattr(self.config, "permanent_services", [])),
                "active_services": list(active_services),
                "active_blocked_count": len(active_domains),
                "allowlist_mode": self.config.allowlist_mode,
                "block_doh": self.config.block_doh,
                "block_vpns": getattr(self.config, "block_vpns", True),
            },
            "dns": {
                "port": self.config.dns_port,
                "upstreams": self.config.upstreams,
            },
            "bypass": self.bypass_mgr.get_bypass_status(),
        }
