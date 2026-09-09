"""Asynchronous upstream DNS resolver with concurrent TTL caching."""

from __future__ import annotations

import asyncio
import socket
import time
from dataclasses import dataclass
from focusguard.dns.protocol import DNSMessage, RCODE_SERVFAIL


@dataclass
class CacheEntry:
    response_bytes: bytes
    expires_at: float


class DNSResolver:
    """
    Forwards permitted DNS queries to configured upstream servers with local caching.
    """

    DEFAULT_UPSTREAMS = [
        ("1.1.1.1", 53),     # Cloudflare Primary
        ("9.9.9.9", 53),     # Quad9 Primary
        ("1.0.0.1", 53),     # Cloudflare Secondary
        ("149.112.112.112", 53), # Quad9 Secondary
    ]

    def __init__(
        self,
        upstreams: list[tuple[str, int]] | None = None,
        timeout: float = 2.5,
        cache_enabled: bool = True,
    ) -> None:
        self.upstreams = upstreams or list(self.DEFAULT_UPSTREAMS)
        self.timeout = timeout
        self.cache_enabled = cache_enabled
        self._cache: dict[tuple[str, int], CacheEntry] = {}
        self._lock = asyncio.Lock()

    def _get_cache_key(self, msg: DNSMessage) -> tuple[str, int] | None:
        if not msg.questions:
            return None
        q = msg.questions[0]
        return (q.qname.lower(), q.qtype)

    async def get_cached_response(self, msg: DNSMessage) -> bytes | None:
        if not self.cache_enabled:
            return None
        key = self._get_cache_key(msg)
        if not key:
            return None

        now = time.monotonic()
        entry = self._cache.get(key)
        if entry:
            if entry.expires_at > now:
                # Rewrite message ID to match incoming query
                cached_msg = DNSMessage.parse(entry.response_bytes)
                cached_msg.id = msg.id
                return cached_msg.to_bytes()
            else:
                del self._cache[key]
        return None

    def store_cache(self, msg: DNSMessage, response_bytes: bytes) -> None:
        if not self.cache_enabled:
            return
        key = self._get_cache_key(msg)
        if not key:
            return

        try:
            parsed = DNSMessage.parse(response_bytes)
            if not parsed.answers:
                return
            min_ttl = min(r.ttl for r in parsed.answers)
            # Clamp TTL between 10s and 3600s
            effective_ttl = max(10, min(min_ttl, 3600))
            now = time.monotonic()
            self._cache[key] = CacheEntry(
                response_bytes=response_bytes,
                expires_at=now + effective_ttl,
            )
        except Exception:
            pass

    async def resolve(self, query_bytes: bytes, msg: DNSMessage) -> bytes:
        """
        Query upstream servers over UDP with fallback and return raw wire response.
        """
        # Check cache first
        cached = await self.get_cached_response(msg)
        if cached is not None:
            return cached

        # Try upstreams sequentially or with quick fallback
        for host, port in self.upstreams:
            try:
                response = await self._query_udp(query_bytes, host, port)
                if response:
                    self.store_cache(msg, response)
                    return response
            except (asyncio.TimeoutError, OSError):
                continue

        # All upstreams failed -> return SERVFAIL
        servfail = DNSMessage(
            id=msg.id,
            qr=1,
            opcode=msg.opcode,
            rd=msg.rd,
            ra=1,
            rcode=RCODE_SERVFAIL,
            questions=msg.questions,
        )
        return servfail.to_bytes()

    async def _query_udp(self, query_bytes: bytes, host: str, port: int) -> bytes:
        loop = asyncio.get_running_loop()
        is_ipv6 = ":" in host
        family = socket.AF_INET6 if is_ipv6 else socket.AF_INET

        sock = socket.socket(family, socket.SOCK_DGRAM)
        sock.setblocking(False)

        try:
            await loop.sock_connect(sock, (host, port))
            await loop.sock_sendall(sock, query_bytes)

            data = await asyncio.wait_for(loop.sock_recv(sock, 4096), timeout=self.timeout)
            return data
        finally:
            sock.close()
