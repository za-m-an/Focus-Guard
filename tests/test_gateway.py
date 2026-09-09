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
