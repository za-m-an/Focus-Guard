"""Unit tests for domain sinkhole matching logic."""

import pytest
from focusguard.dns.sinkhole import DomainSinkhole


def test_subdomain_matching():
    sinkhole = DomainSinkhole(block_doh=False)
    sinkhole.set_blocked_domains(["youtube.com", "reddit.com"])

    # Direct match
    blocked, reason = sinkhole.is_blocked("youtube.com")
    assert blocked is True
    assert reason == "blocked_by_policy"

    # Subdomain match
    blocked, _ = sinkhole.is_blocked("www.youtube.com")
    assert blocked is True

    blocked, _ = sinkhole.is_blocked("m.youtube.com")
    assert blocked is True

    blocked, _ = sinkhole.is_blocked("deep.sub.reddit.com")
    assert blocked is True

    # Unrelated domain should not be blocked
    blocked, _ = sinkhole.is_blocked("notyoutube.com")
    assert blocked is False

    blocked, _ = sinkhole.is_blocked("github.com")
    assert blocked is False

    blocked, _ = sinkhole.is_blocked("youtube.com.attacker.com")
    assert blocked is False


def test_essential_system_domains_always_allowed():
    sinkhole = DomainSinkhole()
    sinkhole.set_blocked_domains(["debian.org", "time.google.com"])

    # Critical system domains are protected
    blocked, reason = sinkhole.is_blocked("dietpi.com")
    assert blocked is False
    assert reason == "system_essential"

    blocked, reason = sinkhole.is_blocked("time.google.com")
    assert blocked is False
    assert reason == "system_essential"


def test_allowlist_mode():
    sinkhole = DomainSinkhole()
    sinkhole.allowlist_mode = True
    sinkhole.set_allowed_domains(["bracu.ac.bd", "github.com"])

    # Permitted in allowlist
    blocked, reason = sinkhole.is_blocked("bracu.ac.bd")
    assert blocked is False
    assert reason == "allowlist_permitted"

    blocked, reason = sinkhole.is_blocked("sub.bracu.ac.bd")
    assert blocked is False

    # Not permitted in allowlist
    blocked, reason = sinkhole.is_blocked("youtube.com")
    assert blocked is True
    assert reason == "not_in_allowlist"


def test_doh_bootstrap_blocked():
    sinkhole = DomainSinkhole(block_doh=True)
    # Known DoH domains should be blocked by default
    blocked, _ = sinkhole.is_blocked("cloudflare-dns.com")
    assert blocked is True

    blocked, _ = sinkhole.is_blocked("dns.google")
    assert blocked is True
