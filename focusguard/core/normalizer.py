"""Domain normalization, validation, and companion service resolution."""

from __future__ import annotations

import re
from urllib.parse import urlparse


class InvalidDomainError(ValueError):
    """Raised when an input cannot be parsed or is an invalid domain."""
    pass


# Known companion domains for major distraction platforms to ensure comprehensive blocking
SERVICE_COMPANIONS: dict[str, list[str]] = {
    "youtube.com": [
        "googlevideo.com",
        "ytimg.com",
        "youtube-nocookie.com",
        "youtu.be",
        "yt3.ggpht.com",
    ],
    "facebook.com": [
        "fbcdn.net",
        "fbsbx.com",
        "fb.com",
        "messenger.com",
    ],
    "instagram.com": [
        "cdninstagram.com",
        "ig.me",
    ],
    "tiktok.com": [
        "tiktokcdn.com",
        "byteoversea.com",
        "ibytedtos.com",
        "musical.ly",
    ],
    "reddit.com": [
        "redd.it",
        "redditmedia.com",
        "redditstatic.com",
    ],
    "twitter.com": [
        "x.com",
        "twimg.com",
        "t.co",
    ],
    "x.com": [
        "twitter.com",
        "twimg.com",
        "t.co",
    ],
    "netflix.com": [
        "nflxext.com",
        "nflximg.net",
        "nflxvideo.net",
    ],
    "twitch.tv": [
        "ttvnw.net",
        "jtvnw.net",
    ],
}

# Regex for standard RFC 1035 / RFC 1123 label: letters, digits, hyphen, not starting/ending with hyphen
LABEL_REGEX = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")


def normalize_domain(raw_input: str) -> str:
    """
    Extract and normalize a clean domain string from diverse user inputs.
    
    Accepts:
      - 'youtube.com'
      - 'www.youtube.com'
      - 'https://youtube.com'
      - 'https://www.youtube.com/watch?v=123'
      - 'http://reddit.com/r/all?sort=top'
      - 'sub.example.co.uk:8080/path'
      - '*.tiktok.com'
    
    Returns:
      Canonical lower-case domain name (e.g. 'youtube.com').
    """
    if not raw_input or not isinstance(raw_input, str):
        raise InvalidDomainError("Domain input cannot be empty.")

    candidate = raw_input.strip().lower()

    # Strip wildcard prefix if user explicitly typed *.example.com
    if candidate.startswith("*."):
        candidate = candidate[2:]

    # If input starts with a scheme or looks like a URL, parse it via urllib
    if "://" in candidate:
        parsed = urlparse(candidate)
        candidate = parsed.netloc or parsed.path
    elif "/" in candidate:
        # User typed e.g. "youtube.com/watch?v=123"
        candidate = candidate.split("/", 1)[0]

    # Strip port if present (e.g. "example.com:8080")
    if ":" in candidate:
        candidate = candidate.split(":", 1)[0]

    # Strip query parameters or fragments if still remaining
    for char in ("?", "#", "@"):
        if char in candidate:
            candidate = candidate.split(char, 1)[0]

    # Strip leading/trailing dots and whitespaces
    candidate = candidate.strip(". \t\r\n")

    if not candidate:
        raise InvalidDomainError("Extracted domain is empty after normalization.")

    # Convert IDN (Internationalized Domain Names) to ASCII punycode
    try:
        candidate = candidate.encode("idna").decode("ascii")
    except Exception as e:
        raise InvalidDomainError(f"Invalid domain encoding: {e}") from e

    # Validation
    validate_domain(candidate)
    return candidate


def validate_domain(domain: str) -> None:
    """
    Validates a canonical domain name according to RFC 1035 / RFC 1123.
    """
    if len(domain) > 253:
        raise InvalidDomainError(f"Domain '{domain}' exceeds maximum length of 253 characters.")

    labels = domain.split(".")
    if len(labels) < 2:
        raise InvalidDomainError(
            f"Domain '{domain}' must contain at least one dot (TLD required, e.g. .com, .org)."
        )

    # Top-Level Domain (TLD) must not be purely numeric
    if labels[-1].isdigit():
        raise InvalidDomainError(f"TLD in '{domain}' cannot be purely numeric (IP addresses not allowed as domain rules).")

    for i, label in enumerate(labels):
        if not label:
            raise InvalidDomainError(f"Domain '{domain}' contains empty label.")
        if len(label) > 63:
            raise InvalidDomainError(f"Domain label '{label}' exceeds 63 characters.")
        if not LABEL_REGEX.match(label):
            raise InvalidDomainError(
                f"Invalid character in domain label '{label}'. Allowed: alphanumeric and hyphen (cannot begin or end with hyphen)."
            )


def get_companion_domains(domain: str) -> list[str]:
    """
    Retrieve recommended companion CDNs/API domains for known platforms.
    For example, for 'youtube.com', returns googlevideo.com, ytimg.com, etc.
    """
    canonical = domain.lower()
    # Strip leading www. if present for companion lookup
    if canonical.startswith("www."):
        canonical = canonical[4:]
    return SERVICE_COMPANIONS.get(canonical, [])
