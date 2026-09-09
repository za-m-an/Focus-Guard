# FocusGuard Architecture Deep-Dive

FocusGuard is a lightweight, production-grade network distraction blocker engineered specifically for DietPi (Debian-based minimal Linux). It operates as a dedicated network DNS appliance managed over SSH via a rich terminal interface.

---

## 1. System Components

```text
                                  ┌─────────────────────────────┐
                                  │      SSH Client (User)      │
                                  └──────────────┬──────────────┘
                                                 │
                                                 ▼
                                  ┌─────────────────────────────┐
                                  │     focusguard (CLI / TUI)  │
                                  └──────────────┬──────────────┘
                                                 │ Unix Domain Socket
                                                 │ /run/focusguard/focusguard.sock
                                                 ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ focusguardd (Persistent Linux Daemon under systemd)                                    │
│                                                                                        │
│   ┌─────────────────────┐      ┌─────────────────────────┐     ┌───────────────────┐   │
│   │     IPC Server      │      │      Policy Engine      │     │  Session Manager  │   │
│   │ (Local Unix Socket) │◄────►│   (Permanent + Session) │◄───►│ (State: LOCKED)   │   │
│   └─────────────────────┘      └───────────┬─────────────┘     └─────────┬─────────┘   │
│                                            │                             │             │
│                                            ▼                             ▼             │
│                                ┌───────────────────────┐       ┌───────────────────┐   │
│                                │    Domain Sinkhole    │       │   State Manager   │   │
│                                │ (Reversed Tree Match) │       │ (Atomic JSON+HMAC)│   │
│                                └───────────▲───────────┘       └───────────────────┘   │
│                                            │                                           │
│                 ┌──────────────────────────┴──────────────────────────┐                │
│                 │               Dual-Stack DNS Engine                 │                │
│                 │    UDP/TCP Port 53 (IPv4 0.0.0.0 & IPv6 [::])       │                │
│                 └───────┬──────────────────────────────────────▲──────┘                │
│                         │                                      │                       │
└─────────────────────────┼──────────────────────────────────────┼───────────────────────┘
                          ▼                                      │
              ┌────────────────────────┐              ┌────────────────────────┐
              │    Local LAN Clients   │              │  Upstream DNS Servers  │
              │ (Laptops, Phones, TVs) │              │  (Cloudflare / Quad9)  │
              └────────────────────────┘              └────────────────────────┘
```

---

## 2. Asynchronous DNS Engine

FocusGuard implements an RFC 1035 wire-format DNS parser and serializer with zero external C or pip dependencies.
- **Listeners**:
  - UDP: `asyncio.DatagramProtocol` binding `0.0.0.0:53` and `[::]:53`.
  - TCP: `asyncio.start_server` handling length-prefixed DNS streams.
- **Sinkhole Strategy**:
  - `A` (IPv4) query -> returns synthetic `0.0.0.0` with TTL 300.
  - `AAAA` (IPv6) query -> returns synthetic `::` with TTL 300.
  - `HTTPS` (type 65) & `SVCB` (type 64) queries -> returns `NODATA` (empty answers, RCODE 0) to prevent modern browsers (Chrome/Firefox/Safari) from using Encrypted Client Hello (ECH) or auto-upgrading to external DoH.
- **Upstream Forwarding & Cache**:
  - Permitted queries are forwarded asynchronously to upstream resolvers (`1.1.1.1`, `9.9.9.9`).
  - Cached in an in-memory TTL map with concurrent request deduplication to prevent upstream request storms.

---

## 3. Subdomain Tree Matching (`DomainSinkhole`)

Rather than inefficient regular expressions or linear string scans, domains are stored as reversed label tuples:
```python
# 'youtube.com'  -> ('com', 'youtube')
# 'www.youtube.com' -> ('com', 'youtube', 'www')
```
When a query arrives for `m.youtube.com`, the reversed key `('com', 'youtube', 'm')` is checked against the prefix tree. This is $O(k)$ where $k$ is the label count (typically 2–4 steps), making lookups sub-microsecond and immune to ReDoS.

---

## 4. Anti-Impulse Locked State Machine

The session lock prevents impulsive bypasses when study willpower wavers.

```text
               ┌──────────────────────────────┐
               │             IDLE             │
               │  (Permanent Blocklist active)│
               └──────────────┬───────────────┘
                              │ focusguard start
                              ▼
               ┌──────────────────────────────┐
               │            LOCKED            │
               │  • Stop / Remove rejected    │
               │  • Timestamp stored to disk  │
               │  • HMAC signature validated  │
               └──────┬────────────────┬──────┘
                      │                │
                Server Reboot    Timer Expires
                      │                │
                      ▼                ▼
               ┌──────────────┐ ┌──────────────┐
               │ REBOOT CHECK │ │ AUTO-EXPIRE  │
               │ now < expire?│ │ Restore state│
               └──────────────┘ └──────────────┘
```

### Durability Guarantees
1. **Reboot Survival**: Session expiration is stored as an absolute UTC timestamp (`expires_at_utc`). On reboot, if `now < expires_at_utc`, the daemon resumes the `LOCKED` session automatically.
2. **Clock Rollback Protection**: If system time moves backward before the recorded `created_at_utc`, FocusGuard flags a tamper condition and remains locked.
3. **Atomic Persistence**: State writes use `write(tempfile) -> fsync -> os.replace(target)`, preventing corrupt state on sudden power loss.
4. **HMAC Signature**: The JSON state is signed with a 256-bit machine-local secret (`/var/lib/focusguard/.secret`). Manual edits to `state.json` are rejected.

---

## 5. Security & Least Privilege

- **Unprivileged User**: `focusguardd` runs under dedicated system user and group `focusguard`.
- **Capability-Based Binding**: Port 53 binding is granted via Linux capability `AmbientCapabilities=CAP_NET_BIND_SERVICE`. No root access is needed during DNS serving.
- **Zero LAN Management Attack Surface**: Management is restricted to the local Unix domain socket `/run/focusguard/focusguard.sock` (mode `0660`). No HTTP API is exposed to the local network.
- **Privacy First**: FocusGuard never decrypts HTTPS packets or installs TLS certificates. It only resolves domain names. Audit logs are circular (capped at 1,000 entries) and store only high-level operational events.
