"""Tests for bypass resistance and VPN defense."""

import pytest
from focusguard.network.bypass import BypassResistanceManager


def test_bypass_manager_defaults():
    mgr = BypassResistanceManager()
    status = mgr.get_bypass_status(gateway_active=False)
    assert "overall" in status
    assert "dns_bypass" in status
    assert "known_vpns" in status
    assert status["vpn_providers_tracked"] >= 10
    assert status["doh_resolvers_tracked"] >= 5


def test_identify_vpn_bypass():
    mgr = BypassResistanceManager()
    
    # Check known VPN domains
    res = mgr.identify_bypass_attempt("nordvpn.com")
    assert res is not None
    bypass_type, provider = res
    assert bypass_type == "VPN Bypass"
    assert provider == "NordVPN"

    res = mgr.identify_bypass_attempt("api.nordvpn.com")
    assert res is not None
    assert res[0] == "VPN Bypass"

    res = mgr.identify_bypass_attempt("us1234.expressvpn.com")
    assert res is not None
    assert res[1] == "ExpressVPN"

    res = mgr.identify_bypass_attempt("vpn.proton.me")
    assert res is not None
    assert res[1] == "ProtonVPN"

    # Ordinary domain
    assert mgr.identify_bypass_attempt("google.com") is None
    assert mgr.identify_bypass_attempt("bracu.ac.bd") is None


def test_identify_doh_bypass():
    mgr = BypassResistanceManager()

    res = mgr.identify_bypass_attempt("cloudflare-dns.com")
    assert res is not None
    bypass_type, provider = res
    assert bypass_type == "DoH Bypass"
    assert "Cloudflare" in provider

    res = mgr.identify_bypass_attempt("dns.google")
    assert res is not None
    assert res[0] == "DoH Bypass"

    res = mgr.identify_bypass_attempt("dns.quad9.net")
    assert res is not None
    assert res[0] == "DoH Bypass"


def test_tunnel_restrictions_non_linux_safe():
    mgr = BypassResistanceManager()
    # On systems without iptables (or Windows dev environment), should return graceful error
    if not mgr._has_iptables:
        success, msg = mgr.enable_tunnel_restrictions()
        assert success is False
        assert "iptables not found" in msg

        success, msg = mgr.disable_tunnel_restrictions()
        assert success is False
