"""Domain sinkhole decision engine using reverse-label prefix matching."""

from __future__ import annotations

from focusguard.core.normalizer import normalize_domain, InvalidDomainError

# Critical system domains that must never be blocked in allowlist or distraction sessions
ESSENTIAL_SYSTEM_DOMAINS = {
    "localhost",
    "dietpi.com",
    "debian.org",
    "archive.ubuntu.com",
    "pool.ntp.org",
    "time.google.com",
    "time.windows.com",
    "time.apple.com",
    "time.cloudflare.com",
}

# Known public DNS-over-HTTPS / DNS-over-TLS bootstrap domains to prevent browser stealth bypasses
DOH_BOOTSTRAP_DOMAINS = {
    "cloudflare-dns.com",
    "one.one.one.one",
    "dns.google",
    "dns.google.com",
    "dns.quad9.net",
    "dns.adguard.com",
    "doh.cleanbrowsing.org",
    "doh.mullvad.net",
    "doh.opendns.com",
}


class DomainSinkhole:
    """
    Evaluates whether a queried domain should be blocked or allowed based on
    reversed-label hierarchy matching.
    """

    def __init__(self, block_doh: bool = True) -> None:
        self.block_doh = block_doh
        # Sets of reversed label tuples, e.g. ('com', 'youtube')
        self._blocked_trees: set[tuple[str, ...]] = set()
        self._allowed_trees: set[tuple[str, ...]] = set()
        self.allowlist_mode: bool = False

        if self.block_doh:
            for domain in DOH_BOOTSTRAP_DOMAINS:
                self._add_rule(domain, self._blocked_trees)

    @staticmethod
    def _domain_to_key(domain: str) -> tuple[str, ...]:
        """Convert 'www.youtube.com' -> ('com', 'youtube', 'www')."""
        clean = domain.strip(". \t\r\n").lower()
        labels = clean.split(".")
        return tuple(reversed(labels))

    def _add_rule(self, domain: str, target_set: set[tuple[str, ...]]) -> None:
        try:
            norm = normalize_domain(domain)
            target_set.add(self._domain_to_key(norm))
        except InvalidDomainError:
            pass

    def set_blocked_domains(self, domains: list[str]) -> None:
        """Replace active blocked domains (preserving DoH rules if enabled)."""
        new_trees: set[tuple[str, ...]] = set()
        if self.block_doh:
            for d in DOH_BOOTSTRAP_DOMAINS:
                self._add_rule(d, new_trees)

        for d in domains:
            self._add_rule(d, new_trees)
        self._blocked_trees = new_trees

    def set_allowed_domains(self, domains: list[str]) -> None:
        """Set domains permitted in allowlist mode."""
        new_trees: set[tuple[str, ...]] = set()
        # Always allow critical infrastructure
        for d in ESSENTIAL_SYSTEM_DOMAINS:
            self._add_rule(d, new_trees)

        for d in domains:
            self._add_rule(d, new_trees)
        self._allowed_trees = new_trees

    def _matches_tree(self, key: tuple[str, ...], tree_set: set[tuple[str, ...]]) -> bool:
        """
        Check if any prefix of the reversed key exists in tree_set.
        Example:
          key = ('com', 'youtube', 'www')
          checks:
            ('com',)
            ('com', 'youtube') -> MATCH!
        """
        for i in range(1, len(key) + 1):
            if key[:i] in tree_set:
                return True
        return False

    def is_blocked(self, query_domain: str) -> tuple[bool, str]:
        """
        Evaluate if domain is blocked.
        Returns: (blocked: bool, reason: str)
        """
        clean = query_domain.strip(". \t\r\n").lower()
        if not clean:
            return False, "empty_query"

        # Check essential system domains first (never blocked)
        key = self._domain_to_key(clean)
        for sys_dom in ESSENTIAL_SYSTEM_DOMAINS:
            sys_key = self._domain_to_key(sys_dom)
            if self._matches_tree(key, {sys_key}):
                return False, "system_essential"

        # If allowlist mode is active: block unless in allowed set
        if self.allowlist_mode:
            if self._matches_tree(key, self._allowed_trees):
                return False, "allowlist_permitted"
            return True, "not_in_allowlist"

        # Standard blocklist mode
        if self._matches_tree(key, self._blocked_trees):
            return True, "blocked_by_policy"

        return False, "permitted"
