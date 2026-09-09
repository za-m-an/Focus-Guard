"""Dual-stack asynchronous UDP/TCP DNS Server."""

from __future__ import annotations

import asyncio
import logging
import socket
import struct
from typing import Callable

from focusguard.dns.protocol import (
    DNSMessage,
    RCODE_FORMERR,
    RCODE_SERVFAIL,
)
from focusguard.dns.resolver import DNSResolver
from focusguard.dns.sinkhole import DomainSinkhole

logger = logging.getLogger("focusguard.dns")


class DNSUDPProtocol(asyncio.DatagramProtocol):
    """Handles UDP DNS packets."""

    def __init__(self, server: DNSServer) -> None:
        self.server = server
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        asyncio.create_task(self._process_query(data, addr))

    async def _process_query(self, data: bytes, addr: tuple[str, int]) -> None:
        if not self.transport:
            return
        response = await self.server.handle_query(data, addr[0])
        if response:
            try:
                self.transport.sendto(response, addr)
            except OSError as e:
                logger.debug("Failed sending UDP DNS response to %s: %s", addr, e)


class DNSServer:
    """
    Production-grade asynchronous DNS Server supporting UDP and TCP over IPv4 and IPv6.
    """

    def __init__(
        self,
        sinkhole: DomainSinkhole,
        resolver: DNSResolver,
        host_v4: str = "0.0.0.0",
        host_v6: str = "::",
        port: int = 53,
        on_block_callback: Callable[[str, str, int], None] | None = None,
        flow_callback: Callable[[str, str, int, str, str], None] | None = None,
        event_bus: Any = None,
    ) -> None:
        self.sinkhole = sinkhole
        self.resolver = resolver
        self.host_v4 = host_v4
        self.host_v6 = host_v6
        self.port = port
        self.on_block_callback = on_block_callback
        self.flow_callback = flow_callback
        self.event_bus = event_bus
        self._is_running = False
        self._udp_transports: list[asyncio.DatagramTransport] = []
        self._tcp_servers: list[asyncio.Server] = []

    async def handle_query(self, query_bytes: bytes, client_ip: str) -> bytes | None:
        """
        Processes a raw DNS packet, checks sinkhole, or forwards to upstream.
        Broadcasting real-time flow events to the monitor event bus and audit store.
        """
        try:
            msg = DNSMessage.parse(query_bytes)
        except Exception:
            # Bad packet format
            if len(query_bytes) >= 2:
                msg_id = struct.unpack("!H", query_bytes[:2])[0]
                err_resp = DNSMessage(id=msg_id, qr=1, rcode=RCODE_FORMERR)
                return err_resp.to_bytes()
            return None

        # Standard query without questions -> return SERVFAIL
        if not msg.questions:
            servfail = DNSMessage(id=msg.id, qr=1, rcode=RCODE_SERVFAIL)
            return servfail.to_bytes()

        q = msg.questions[0]
        qname = q.qname
        is_blocked, reason = self.sinkhole.is_blocked(qname)
        action = "BLOCKED" if is_blocked else "ALLOWED"

        # Broadcast to real-time monitor subscribers
        if self.event_bus:
            try:
                from focusguard.service.event_bus import FlowEvent
                import datetime
                self.event_bus.publish(FlowEvent(
                    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    client_ip=client_ip,
                    domain=qname,
                    qtype=q.qtype,
                    action=action,
                    reason=reason,
                ))
            except Exception:
                pass

        # Record flow in SQLite audit log
        if self.flow_callback:
            try:
                self.flow_callback(client_ip, qname, q.qtype, action, reason)
            except Exception:
                pass

        if is_blocked:
            if self.on_block_callback:
                try:
                    self.on_block_callback(client_ip, qname, q.qtype)
                except Exception:
                    pass
            sink_resp = msg.create_sinkhole_response(sink_ipv4="0.0.0.0", sink_ipv6="::")
            return sink_resp.to_bytes()

        # Permitted -> forward upstream
        return await self.resolver.resolve(query_bytes, msg)

    async def _handle_tcp_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        client_ip = peer[0] if peer else "unknown"

        try:
            while True:
                # DNS over TCP is prefixed by a 2-byte length
                len_bytes = await reader.readexactly(2)
                req_len = struct.unpack("!H", len_bytes)[0]
                if req_len == 0:
                    break
                query_data = await reader.readexactly(req_len)
                response = await self.handle_query(query_data, client_ip)
                if response:
                    writer.write(struct.pack("!H", len(response)) + response)
                    await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionResetError, BrokenPipeError):
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def start(self) -> None:
        """Start UDP and TCP servers on configured IPv4 and IPv6 addresses."""
        loop = asyncio.get_running_loop()
        self._is_running = True

        # Bind UDP IPv4
        try:
            transport, _ = await loop.create_datagram_endpoint(
                lambda: DNSUDPProtocol(self),
                local_addr=(self.host_v4, self.port),
            )
            self._udp_transports.append(transport)
            logger.info("DNS UDP listening on %s:%d", self.host_v4, self.port)
        except Exception as e:
            logger.warning("Could not bind UDP on IPv4 %s:%d: %s", self.host_v4, self.port, e)

        # Bind UDP IPv6
        if socket.has_ipv6 and self.host_v6:
            try:
                transport_v6, _ = await loop.create_datagram_endpoint(
                    lambda: DNSUDPProtocol(self),
                    local_addr=(self.host_v6, self.port),
                )
                self._udp_transports.append(transport_v6)
                logger.info("DNS UDP listening on [%s]:%d", self.host_v6, self.port)
            except Exception as e:
                logger.warning("Could not bind UDP on IPv6 [%s]:%d: %s", self.host_v6, self.port, e)

        # Bind TCP IPv4
        try:
            tcp_v4 = await asyncio.start_server(
                self._handle_tcp_client,
                host=self.host_v4,
                port=self.port,
            )
            self._tcp_servers.append(tcp_v4)
            logger.info("DNS TCP listening on %s:%d", self.host_v4, self.port)
        except Exception as e:
            logger.warning("Could not bind TCP on IPv4 %s:%d: %s", self.host_v4, self.port, e)

        # Bind TCP IPv6
        if socket.has_ipv6 and self.host_v6:
            try:
                tcp_v6 = await asyncio.start_server(
                    self._handle_tcp_client,
                    host=self.host_v6,
                    port=self.port,
                )
                self._tcp_servers.append(tcp_v6)
                logger.info("DNS TCP listening on [%s]:%d", self.host_v6, self.port)
            except Exception as e:
                logger.warning("Could not bind TCP on IPv6 [%s]:%d: %s", self.host_v6, self.port, e)

    async def stop(self) -> None:
        """Stop all running DNS transports and listeners."""
        self._is_running = False
        for transport in self._udp_transports:
            transport.close()
        self._udp_transports.clear()

        for server in self._tcp_servers:
            server.close()
            await server.wait_closed()
        self._tcp_servers.clear()
        logger.info("DNS Server stopped.")
