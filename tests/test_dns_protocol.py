"""Unit tests for RFC 1035 wire-format DNS protocol."""

import ipaddress
import pytest
from focusguard.dns.protocol import (
    DNSMessage,
    DNSQuestion,
    TYPE_A,
    TYPE_AAAA,
    TYPE_HTTPS,
    RCODE_NOERROR,
)


def test_serialize_and_parse_query():
    msg = DNSMessage(id=0x1234, qr=0, rd=1)
    msg.questions.append(DNSQuestion(qname="youtube.com", qtype=TYPE_A))

    packet = msg.to_bytes()
    assert len(packet) > 12

    parsed = DNSMessage.parse(packet)
    assert parsed.id == 0x1234
    assert parsed.qr == 0
    assert parsed.rd == 1
    assert len(parsed.questions) == 1
    assert parsed.questions[0].qname == "youtube.com"
    assert parsed.questions[0].qtype == TYPE_A


def test_sinkhole_response_a():
    msg = DNSMessage(id=0x5678, qr=0, rd=1)
    msg.questions.append(DNSQuestion(qname="facebook.com", qtype=TYPE_A))

    resp = msg.create_sinkhole_response(sink_ipv4="0.0.0.0")
    assert resp.id == 0x5678
    assert resp.qr == 1
    assert resp.aa == 1
    assert resp.rcode == RCODE_NOERROR
    assert len(resp.answers) == 1
    assert resp.answers[0].name == "facebook.com"
    assert resp.answers[0].rtype == TYPE_A
    assert resp.answers[0].rdata == ipaddress.IPv4Address("0.0.0.0").packed

    # Verify round-trip serialization
    encoded = resp.to_bytes()
    parsed_resp = DNSMessage.parse(encoded)
    assert parsed_resp.id == 0x5678
    assert parsed_resp.qr == 1
    assert parsed_resp.answers[0].rdata == b"\x00\x00\x00\x00"


def test_sinkhole_response_aaaa():
    msg = DNSMessage(id=0x9ABC, qr=0, rd=1)
    msg.questions.append(DNSQuestion(qname="instagram.com", qtype=TYPE_AAAA))

    resp = msg.create_sinkhole_response(sink_ipv6="::")
    assert len(resp.answers) == 1
    assert resp.answers[0].rtype == TYPE_AAAA
    assert resp.answers[0].rdata == ipaddress.IPv6Address("::").packed


def test_sinkhole_response_https_nodata():
    msg = DNSMessage(id=0xDEF0, qr=0, rd=1)
    msg.questions.append(DNSQuestion(qname="reddit.com", qtype=TYPE_HTTPS))

    resp = msg.create_sinkhole_response()
    # For HTTPS (65), answers should be empty (NODATA) to prevent ECH upgrade
    assert len(resp.answers) == 0
    assert resp.rcode == RCODE_NOERROR
