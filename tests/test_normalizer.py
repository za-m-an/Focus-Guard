"""Unit tests for domain normalization and validation."""

import pytest
from focusguard.core.normalizer import (
    normalize_domain,
    validate_domain,
    get_companion_domains,
    InvalidDomainError,
)


def test_normalize_plain_domain():
    assert normalize_domain("youtube.com") == "youtube.com"
    assert normalize_domain("  YOUTUBE.COM  ") == "youtube.com"
    assert normalize_domain("www.youtube.com") == "www.youtube.com"


def test_normalize_urls():
    assert normalize_domain("https://youtube.com") == "youtube.com"
    assert normalize_domain("http://www.youtube.com/watch?v=12345") == "www.youtube.com"
    assert normalize_domain("https://reddit.com/r/popular?sort=hot") == "reddit.com"
    assert normalize_domain("facebook.com/messages/t/123") == "facebook.com"


def test_normalize_ports_and_wildcards():
    assert normalize_domain("example.com:8443") == "example.com"
    assert normalize_domain("*.tiktok.com") == "tiktok.com"


def test_invalid_domains():
    with pytest.raises(InvalidDomainError):
        normalize_domain("")

    with pytest.raises(InvalidDomainError):
        normalize_domain("   ")

    with pytest.raises(InvalidDomainError):
        normalize_domain("singleword")

    with pytest.raises(InvalidDomainError):
        normalize_domain("192.168.1.1")  # IP addresses are not valid domains

    with pytest.raises(InvalidDomainError):
        normalize_domain("bad_character.com")


def test_companion_domains():
    companions = get_companion_domains("youtube.com")
    assert "googlevideo.com" in companions
    assert "ytimg.com" in companions

    assert get_companion_domains("unknown-site-12345.com") == []
