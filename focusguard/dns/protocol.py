"""RFC 1035 compliant DNS wire-format parser and builder."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
import ipaddress


# DNS Record Types
TYPE_A = 1
TYPE_NS = 2
TYPE_CNAME = 5
TYPE_SOA = 6
TYPE_PTR = 12
TYPE_MX = 15
TYPE_TXT = 16
TYPE_AAAA = 28
TYPE_SVCB = 64
TYPE_HTTPS = 65
TYPE_ANY = 255

CLASS_IN = 1

# Response Codes
RCODE_NOERROR = 0
RCODE_FORMERR = 1
RCODE_SERVFAIL = 2
RCODE_NXDOMAIN = 3
RCODE_NOTIMP = 4
RCODE_REFUSED = 5


@dataclass
class DNSQuestion:
    qname: str
    qtype: int
    qclass: int = CLASS_IN

    def to_bytes(self) -> bytes:
        data = bytearray()
        for label in self.qname.strip(".").split("."):
            encoded = label.encode("ascii")
            data.append(len(encoded))
            data.extend(encoded)
        data.append(0)
        data.extend(struct.pack("!HH", self.qtype, self.qclass))
        return bytes(data)


@dataclass
class DNSRecord:
    name: str
    rtype: int
    rclass: int = CLASS_IN
    ttl: int = 300
    rdata: bytes = b""

    def to_bytes(self, name_offset_map: dict[str, int] | None = None) -> bytes:
        # Simple non-compressed or basic name serialization
        name_bytes = bytearray()
        for label in self.name.strip(".").split("."):
            enc = label.encode("ascii")
            name_bytes.append(len(enc))
            name_bytes.extend(enc)
        name_bytes.append(0)

        header = struct.pack("!HHIH", self.rtype, self.rclass, self.ttl, len(self.rdata))
        return bytes(name_bytes) + header + self.rdata


@dataclass
class DNSMessage:
    id: int = 0
    qr: int = 0         # 0=Query, 1=Response
    opcode: int = 0     # 0=Standard query
    aa: int = 0         # Authoritative answer
    tc: int = 0         # Truncation
    rd: int = 1         # Recursion desired
    ra: int = 0         # Recursion available
    z: int = 0          # Reserved
    rcode: int = 0      # Response code
    questions: list[DNSQuestion] = field(default_factory=list)
    answers: list[DNSRecord] = field(default_factory=list)
    authorities: list[DNSRecord] = field(default_factory=list)
    additionals: list[DNSRecord] = field(default_factory=list)

    @classmethod
    def parse(cls, data: bytes) -> DNSMessage:
        """Parse raw DNS wire packet into DNSMessage."""
        if len(data) < 12:
            raise ValueError(f"DNS packet too short ({len(data)} bytes, min 12)")

        msg_id, flags, qdcount, ancount, nscount, arcount = struct.unpack("!HHHHHH", data[:12])

        qr = (flags >> 15) & 0x1
        opcode = (flags >> 11) & 0xF
        aa = (flags >> 10) & 0x1
        tc = (flags >> 9) & 0x1
        rd = (flags >> 8) & 0x1
        ra = (flags >> 7) & 0x1
        z = (flags >> 4) & 0x7
        rcode = flags & 0xF

        msg = cls(
            id=msg_id,
            qr=qr,
            opcode=opcode,
            aa=aa,
            tc=tc,
            rd=rd,
            ra=ra,
            z=z,
            rcode=rcode,
        )

        offset = 12

        # Parse Questions
        for _ in range(qdcount):
            qname, offset = cls._read_name(data, offset)
            if offset + 4 > len(data):
                raise ValueError("Malformed question section")
            qtype, qclass = struct.unpack("!HH", data[offset:offset + 4])
            offset += 4
            msg.questions.append(DNSQuestion(qname=qname, qtype=qtype, qclass=qclass))

        # Parse Answers
        for _ in range(ancount):
            record, offset = cls._read_record(data, offset)
            msg.answers.append(record)

        # Parse Authorities
        for _ in range(nscount):
            record, offset = cls._read_record(data, offset)
            msg.authorities.append(record)

        # Parse Additionals
        for _ in range(arcount):
            record, offset = cls._read_record(data, offset)
            msg.additionals.append(record)

        return msg

    @classmethod
    def _read_name(cls, data: bytes, offset: int) -> tuple[str, int]:
        labels = []
        visited_pointers = set()
        current = offset
        original_offset = -1

        while True:
            if current >= len(data):
                raise ValueError("Premature end of DNS packet reading name")

            length = data[current]

            # Compression pointer (starts with 11xxxxxx)
            if (length & 0xC0) == 0xC0:
                if current + 2 > len(data):
                    raise ValueError("Premature end of DNS packet in pointer")
                pointer = struct.unpack("!H", data[current:current + 2])[0] & 0x3FFF
                if pointer in visited_pointers:
                    raise ValueError("DNS compression loop detected")
                visited_pointers.add(pointer)

                if original_offset == -1:
                    original_offset = current + 2

                current = pointer
                continue

            current += 1
            if length == 0:
                break

            if current + length > len(data):
                raise ValueError("DNS label length exceeds packet size")

            label = data[current:current + length].decode("ascii", errors="replace").lower()
            labels.append(label)
            current += length

        end_offset = original_offset if original_offset != -1 else current
        domain = ".".join(labels)
        return domain, end_offset

    @classmethod
    def _read_record(cls, data: bytes, offset: int) -> tuple[DNSRecord, int]:
        name, offset = cls._read_name(data, offset)
        if offset + 10 > len(data):
            raise ValueError("Malformed record header")
        rtype, rclass, ttl, rdlength = struct.unpack("!HHIH", data[offset:offset + 10])
        offset += 10
        if offset + rdlength > len(data):
            raise ValueError("Record data length exceeds packet size")
        rdata = data[offset:offset + rdlength]
        offset += rdlength
        return DNSRecord(name=name, rtype=rtype, rclass=rclass, ttl=ttl, rdata=rdata), offset

    def to_bytes(self) -> bytes:
        """Serialize DNSMessage to wire bytes."""
        flags = (
            ((self.qr & 1) << 15)
            | ((self.opcode & 0xF) << 11)
            | ((self.aa & 1) << 10)
            | ((self.tc & 1) << 9)
            | ((self.rd & 1) << 8)
            | ((self.ra & 1) << 7)
            | ((self.z & 7) << 4)
            | (self.rcode & 0xF)
        )

        header = struct.pack(
            "!HHHHHH",
            self.id,
            flags,
            len(self.questions),
            len(self.answers),
            len(self.authorities),
            len(self.additionals),
        )

        packet = bytearray(header)

        for q in self.questions:
            packet.extend(q.to_bytes())

        for rr in self.answers:
            packet.extend(rr.to_bytes())

        for rr in self.authorities:
            packet.extend(rr.to_bytes())

        for rr in self.additionals:
            packet.extend(rr.to_bytes())

        return bytes(packet)

    def create_sinkhole_response(self, sink_ipv4: str = "0.0.0.0", sink_ipv6: str = "::") -> DNSMessage:
        """
        Build an authoritative sinkhole answer:
          - For TYPE_A -> 0.0.0.0
          - For TYPE_AAAA -> ::
          - For HTTPS (65) / SVCB (64) -> NODATA (NoError, 0 answers)
        """
        resp = DNSMessage(
            id=self.id,
            qr=1,           # Response
            opcode=self.opcode,
            aa=1,           # Authoritative
            tc=0,
            rd=self.rd,
            ra=1,           # Recursion Available
            rcode=RCODE_NOERROR,
            questions=list(self.questions),
        )

        if not self.questions:
            return resp

        q = self.questions[0]
        ttl = 300

        if q.qtype == TYPE_A:
            rdata = ipaddress.IPv4Address(sink_ipv4).packed
            resp.answers.append(DNSRecord(name=q.qname, rtype=TYPE_A, ttl=ttl, rdata=rdata))
        elif q.qtype == TYPE_AAAA:
            rdata = ipaddress.IPv6Address(sink_ipv6).packed
            resp.answers.append(DNSRecord(name=q.qname, rtype=TYPE_AAAA, ttl=ttl, rdata=rdata))
        # For TYPE_HTTPS, TYPE_SVCB, or other types: return NODATA (empty answers) to disable ECH/DoH discovery

        return resp

    def create_refused_response(self) -> DNSMessage:
        """Create a REFUSED error response."""
        return DNSMessage(
            id=self.id,
            qr=1,
            opcode=self.opcode,
            aa=1,
            rd=self.rd,
            ra=1,
            rcode=RCODE_REFUSED,
            questions=list(self.questions),
        )
