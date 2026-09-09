"""Unit tests for NetworkGatewayManager."""

import pytest
from focusguard.network.gateway import NetworkGatewayManager


def test_gateway_status_reporting():
    mgr = NetworkGatewayManager(dns_port=53)
    status = mgr.get_gateway_status()

    assert "gateway_capable" in status
    assert "ip_forwarding" in status
    assert "transparent_redirection" in status
    assert status["dns_port"] == 53
    assert status["mode"] in ("TRANSPARENT_GATEWAY", "STANDARD_DNS")


def test_gateway_without_iptables():
    mgr = NetworkGatewayManager(dns_port=53)
    mgr._has_iptables = False

    success, msg = mgr.enable_transparent_redirection()
    assert not success
    assert "iptables utility not found" in msg

    success, msg = mgr.disable_transparent_redirection()
    assert not success
    assert "iptables utility not found" in msg


def test_gateway_permission_error_handling(monkeypatch):
    import subprocess

    mgr = NetworkGatewayManager(dns_port=53)
    mgr._has_iptables = True

    def mock_run(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=["iptables"],
            stderr=b"iptables: Permission denied (you must be root)"
        )

    monkeypatch.setattr(subprocess, "run", mock_run)
    success, msg = mgr.enable_transparent_redirection()
    assert not success
    assert "root privileges" in msg.lower()
