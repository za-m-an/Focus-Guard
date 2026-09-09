# FocusGuard — DietPi Network-Wide Distraction Blocker

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Platform: DietPi / Linux](https://img.shields.io/badge/platform-DietPi%20%2F%20Linux-green.svg)](https://dietpi.com)

**FocusGuard** is a production-grade, self-hosted, network-wide distraction-blocking server appliance engineered specifically for **DietPi** (and Debian-based minimal Linux systems).

It enables the owner of a private home network to temporarily lock down distracting websites (YouTube, social media, entertainment) across **every device on the home network** (laptops, smartphones, tablets, smart TVs) with a single command over SSH.

---

```text
                    ┌─────────────────────────┐
                    │       INTERNET          │
                    └────────────┬────────────┘
                                 │ WAN
                    ┌────────────┴────────────┐
                    │       HOME ROUTER       │
                    │   Gateway: 192.168.1.1  │
                    │ DHCP DNS -> DietPi IP   │
                    └──────┬────────────┬─────┘
                           │            │ Direct LAN / Wi-Fi Traffic
             ┌─────────────┴─────┐      │ (Full wire speed)
             │   DietPi SERVER   │      ▼
             │   192.168.1.50    │  ┌───────────────┐
             │ ┌───────────────┐ │  │ Client Devices│
             │ │  focusguardd  │ │  │ Laptop, Phone,│
             │ │  (DNS Engine, │ │  │ TV, Tablet    │
             │ │  Policy, Lock)│ │  └───────┬───────┘
             │ └───────┬───────┘ │          │
             │         │ Unix    │          │ DNS Queries (Port 53)
             │         │ Socket  │          │
             │ ┌───────┴───────┐ │          │
             │ │focusguard CLI │ │◄─────────┘
             │ └───────────────┘ │
             └───────────────────┘
```

---

## Key Highlights

- **Server Appliance Design**: Runs 24/7 in the background under `systemd`. No Windows application, browser extension, or desktop GUI required.
- **SSH-First Control**: Connect via `ssh user@dietpi`, manage sessions, and exit. Sessions continue enforcing independently.
- **Anti-Impulse Locked Sessions**: Once activated (e.g. for 4 hours or until 23:30), normal application commands cannot stop, pause, or modify the blocklist until expiration.
- **Durable Across Reboots**: Stored persistently on disk with UTC timestamps, monotonic clocks, and HMAC signatures. If the server reboots, the lock automatically resumes if time remains.
- **Subdomain Radix Sinks**: Blocking `youtube.com` automatically blocks all subdomains (`m.youtube.com`, `www.youtube.com`) and includes known CDNs (`googlevideo.com`, `ytimg.com`).
- **Dual-Stack IPv4 & IPv6**: Dual-stack DNS server simultaneously resolves or sinkholes `A` (IPv4) and `AAAA` (IPv6) queries.
- **Zero Privacy Invasion**: Operates strictly on domain lookups. HTTPS payloads and certificates are never intercepted, inspected, or decrypted.
- **Ultra Lightweight**: Pure asynchronous Python with standard libraries. Zero compiler dependencies. Consumes ~20 MB RAM and <0.1% CPU on ARM single-board computers (Raspberry Pi, Orange Pi, NanoPi).

---

## Quick Start (Installation on DietPi)

Clone the repository to your DietPi server and run the automated installer:

```bash
git clone https://github.com/za-m-an/Focus-Guard.git
cd Focus-Guard
sudo chmod +x scripts/install.sh
sudo ./scripts/install.sh
```

The installer will:
1. Validate your Linux and Python environment.
2. Create an isolated system user and group (`focusguard`).
3. Set up directory permissions and grant low-port binding (`CAP_NET_BIND_SERVICE`).
4. Install and enable the `focusguard.service` daemon under systemd.
5. Run an automatic health check (`focusguard doctor`).

---

## Updating FocusGuard

To pull the latest updates, refresh binaries, and restart the service at any time:

```bash
cd Focus-Guard
sudo ./scripts/update.sh
```

---

## Usage Workflow

Connect to your DietPi server over SSH:
```bash
ssh dietpi@192.168.1.50
```

### 1. View Status
```bash
focusguard status
```
```text
FocusGuard Appliance Status
──────────────────────────────────────────────
  Service Daemon:        ● ACTIVE
  Network DNS Filter:    ● RUNNING (Port 53)
  Policy Mode:           Blocklist Engine
  Session Status:        IDLE
  Permanent Blocklist:   5 domains
  Total Active Blocked:  5
  DoH / DoT Guard:       Active
──────────────────────────────────────────────
```

### 2. Manage Blocked Websites
```bash
# Add websites to permanent blocklist
focusguard add youtube.com
focusguard add reddit.com
focusguard add tiktok.com

# List configured domains
focusguard list

# Remove a domain
focusguard remove reddit.com
```

### 3. Start a Locked Focus Session

#### By Duration (e.g., 4 hours, 45 minutes, 1 hour 30 mins)
```bash
focusguard start --duration 4h
```

#### By Absolute End Time (e.g., until 23:30 tonight)
```bash
focusguard start --until 23:30
```

#### Output:
```text
╔═══════════════════════════════════════════════════════╗
║               🔒 LOCKED FOCUS SESSION                 ║
╠═══════════════════════════════════════════════════════╣
║  Status:      LOCKED (Anti-Impulse Active)            ║
║  Started:     2026-09-09 20:00:00                     ║
║  Ends:        2026-09-09 23:30:00                     ║
║  Remaining:   03:29:58                                ║
║  Domains:     5                                       ║
╚═══════════════════════════════════════════════════════╝

  You may safely disconnect from SSH.
  The DietPi server will enforce this session in the background.
  Pause / stop / edit is disabled until the session expires.
```

Now type `exit` to close SSH and begin your study session!

---

## Anti-Impulse Lock Protection

If temptation strikes and you SSH back in to stop the blocker:

```bash
$ focusguard stop

ERROR: LOCKED FOCUS SESSION IN PROGRESS.
Modification and cancellation are disabled until: 2026-09-09T23:30:00+00:00
Time remaining: 02:45:12
Anti-impulse guard active. Stay focused!
```

Any attempt to `remove`, `edit`, or `stop` during the locked window is rejected. When the expiration timestamp is reached, FocusGuard automatically lifts the session rules and returns to the normal policy.

---

### 4. Service-Level Distraction Blocking (Web & Mobile Apps)

Instead of manually guessing CDN and API domains for complex platforms, block entire services across browsers and native iOS/Android mobile apps:

```bash
# List all registered distraction platforms and status
focusguard services

# Permanently block or unblock an entire service
focusguard service block instagram
focusguard service block tiktok
focusguard service unblock tiktok

# Start a locked session specifically targeting selected services
focusguard start --duration 3h --services youtube,instagram,reddit
```

Registered services encompass primary web portals, background mobile API endpoints, and media delivery CDNs:
- **YouTube** (Web, iOS/Android apps, `googlevideo.com`, `ytimg.com`)
- **Instagram** (Web, mobile apps, Reels, Stories, `cdninstagram.com`)
- **Facebook** (Web, Messenger, Graph APIs, `fbcdn.net`)
- **TikTok** (Web, native apps, video delivery CDNs)
- **Reddit** (Web, official mobile app, `redd.it`, image/video CDNs)
- **Twitter / X** (`twitter.com`, `x.com`, `twimg.com`, API gateways)
- **Netflix & Twitch** (Full web and streaming client endpoints)

---

### 5. VPN & Encrypted DNS Bypass Resistance

To prevent casual circumvention of focus sessions via commercial VPNs or encrypted DNS resolvers:

```bash
# View bypass defense status and hardening levels
focusguard bypass-status
```
```text
BYPASS RESISTANCE & CIRCUMVENTION DEFENSE
──────────────────────────────────────────────────────────────────────────
Overall Hardening:     ACTIVE (HARDENED)

DNS Bypass (Port 53):  PROTECTED
DoT Bypass (Port 853): PROTECTED
DoH Bypass (HTTPS):    PROTECTED (10 resolvers sinkholed)
Known VPN Endpoints:   BLOCKED (11 commercial providers)
Common Tunnels:        RESTRICTED (WireGuard: 51820, OpenVPN: 1194, IPsec)
IPv6 Circumvention:    PROTECTED
Proxy Endpoints:       PARTIALLY PROTECTED
──────────────────────────────────────────────────────────────────────────
Note: FocusGuard provides robust defense against casual circumvention on
authorized private networks. Custom tunnels or cellular data remain out-of-scope.
```

---

### 6. Connected Device Discovery (`focusguard devices`)

Inspect all active client devices communicating through the FocusGuard appliance:

```bash
focusguard devices
```
```text
CONNECTED & ACTIVE NETWORK CLIENTS
──────────────────────────────────────────────────────────────────────────
DEVICE             IP ADDRESS       STATUS    QUERIES   BLOCKED   LAST SEEN
──────────────────────────────────────────────────────────────────────────
MacBook-Pro.lan    192.168.1.15     ACTIVE    842       290       2026-09-09 20:41:12
Pixel-8.lan        192.168.1.22     ACTIVE    390       12        2026-09-09 20:40:55
iPad-Air.lan       192.168.1.30     ACTIVE    188       87        2026-09-09 20:38:19
Smart-TV.lan       192.168.1.45     IDLE      45        0         2026-09-09 19:12:00
──────────────────────────────────────────────────────────────────────────
Total Active Clients: 3 (Active within 15 minutes)
```

---

## Live Network Flow Monitoring (`focusguard monitor`)

Watch DNS queries, service matches, and bypass events across your LAN in real-time as devices browse:

```bash
focusguard monitor
```
```text
FOCUSGUARD LIVE NETWORK MONITOR
──────────────────────────────────────────────────────────────────────────
TIME       DEVICE            DESTINATION                ACTION     REASON
──────────────────────────────────────────────────────────────────────────
20:14:02   192.168.1.15      youtube.com                BLOCKED    Service: YouTube
20:14:03   192.168.1.15      rr5.googlevideo.com        BLOCKED    Service: YouTube
20:14:04   192.168.1.22      github.com                 ALLOWED    No active rule matched
20:14:05   192.168.1.15      cloudflare-dns.com         BLOCKED    DoH Bypass: Cloudflare DoH
20:14:06   192.168.1.30      api.nordvpn.com            BLOCKED    VPN Bypass: NordVPN
──────────────────────────────────────────────────────────────────────────
```

### Filters:
- Show only blocked requests: `focusguard monitor --blocked`
- Filter by device IP: `focusguard monitor --device 192.168.1.15`
- Filter by domain name: `focusguard monitor --domain youtube`
- Filter by distraction service: `focusguard monitor --service instagram`

---

## Traffic Analytics & Statistics (`focusguard stats`)

Inspect aggregate traffic counts, block rates, top blocked domains, and active devices:

```bash
focusguard stats
```
```text
FocusGuard Traffic Analytics & Statistics
════════════════════════════════════════════════════
  Total Queries:      1,420
  Blocked Queries:    389 (27.4% block rate)
  Allowed Queries:    1,031
  Active Devices:     4

Top Blocked Domains:
──────────────────────────────────────
  • youtube.com                   194
  • googlevideo.com               112
  • facebook.com                   54
  • reddit.com                     29

Device Activity Breakdown:
──────────────────────────────────────────────
  IP Address         Total      Blocked
  192.168.1.15       842        290
  192.168.1.22       390        12
  192.168.1.30       188        87
════════════════════════════════════════════════════
```

Add `--session` to scope metrics specifically to the current active focus session:
```bash
focusguard stats --session
```


---

## Packet-Level Monitoring & Header Inspection

In addition to DNS-layer observability, FocusGuard features an integrated **packet-level monitoring and inspection subsystem** capable of capturing wire frames that traverse the DietPi network appliance.

### 1. Live Packet Monitor (`focusguard packet-monitor`)
Observe network packets in real-time, inspect direction (`LAN → WAN`, `WAN → LAN`, `LOCAL`), protocol headers, ports, and policy correlation:

```bash
focusguard packet-monitor
```
```text
FOCUSGUARD LIVE PACKET MONITOR
────────────────────────────────────────────────────────────────────────────
TIME     IFACE  DIR        SOURCE                 DESTINATION            PROTO   ACTION
────────────────────────────────────────────────────────────────────────────
21:31:04 eth0   LAN → WAN  192.168.1.15:52144   → 142.250.190.46:443     TCP     OBSERVED [HTTPS/QUIC Web Flow]
21:31:04 eth0   LAN → WAN  192.168.1.15:41000   → 198.51.100.2:51820     UDP     MATCH [WireGuard Tunnel (Port 51820)]
21:31:05 eth0   WAN → LAN  142.250.190.46:443   → 192.168.1.15:52144     TCP     OBSERVED [HTTPS/QUIC Web Flow]
21:31:05 eth0   LAN → WAN  192.168.1.20:43122   → 1.1.1.1:53             UDP     OBSERVED [DNS Traffic (Port 53)]
────────────────────────────────────────────────────────────────────────────
```

#### Verbose Inspection:
Add `-v` or `--verbose` to inspect TCP flags (SYN, ACK, PSH, FIN, RST) and packet length on each line:
```bash
focusguard packet-monitor --verbose
```

#### Stream Filtering:
- Filter by device IP: `focusguard packet-monitor --device 192.168.1.15`
- Filter by protocol: `focusguard packet-monitor --protocol tcp`
- Filter by port: `focusguard packet-monitor --port 443`

---

### 2. Packet Traffic Statistics (`focusguard packet-stats`)
Inspect aggregate packet counts, byte volumes, protocol distribution, and active connection flows:

```bash
focusguard packet-stats
```
```text
FOCUSGUARD PACKET TRAFFIC STATISTICS
════════════════════════════════════════════════════
  Packets Observed:  128,421
  Bytes Observed:    84.2 MB (88,290,144 B)
  Active Flows:      84

  Protocol Distribution:
  ──────────────────────────────────────────────
    • TCP:            76.4%  (98,113 pkts)
    • UDP:            21.8%  (27,995 pkts)
    • ICMP/ICMPv6:     1.1%  (1,412 pkts)
    • Other / ARP:     0.7%  (901 pkts)

  Directional Volume:
  ──────────────────────────────────────────────
    • Inbound:       42.1 MB
    • Outbound:      42.1 MB
════════════════════════════════════════════════════
```

---

### 3. Detailed Packet Inspection (`focusguard packet inspect`)
Inspect all decoded headers of a specific packet or the most recent frame:

```bash
# Inspect latest packet
focusguard packet inspect

# Inspect specific packet with payload preview
focusguard packet inspect --id 42 --hex
```
```text
Packet Header Inspection (ID #42)
────────────────────────────────────────────────────
  Timestamp:     21:31:04.382
  Interface:     eth0
  Direction:     LAN → WAN
  IP Version:    IPv4

  Source:
    IP:          192.168.1.15
    Port:        52144
    Device:      MacBook-Pro

  Destination:
    IP:          142.250.190.46
    Port:        443

  Protocol:      TCP
  Packet Length: 74 bytes
  TTL / Hop:     64
  TCP Flags:     SYN
  Policy Match:  HTTPS/QUIC Web Flow
  Policy Action: OBSERVED

  Raw Payload Preview (Hex & ASCII):
  ──────────────────────────────────────────────────
  45 00 00 4a d4 31 40 00 40 06 ... | E..J.1@.@...
────────────────────────────────────────────────────
```

---

## Automatic Network Enforcement & Gateway Mode


To automatically enforce policy on **any new device that joins your home network** without manually configuring DNS on every device:

FocusGuard provides transparent network redirection via Linux kernel IP forwarding and iptables:

```bash
# View gateway & redirection status
focusguard gateway status

# Enable transparent DNS interception (redirects all port 53 traffic)
sudo focusguard gateway enable

# Disable transparent redirection (strictly rejected while focus session is locked!)
sudo focusguard gateway disable
```

When enabled:
- Any outbound DNS packet (port 53 UDP/TCP) originating from any device is transparently intercepted and filtered by FocusGuard.
- Even if a device has hardcoded `8.8.8.8` or `1.1.1.1`, its queries are intercepted.
- Outbound DNS-over-TLS (port 853) is rejected to prevent encrypted DNS bypass.

---

## Interactive Menu

If you prefer navigating via an interactive menu rather than typing flags:
```bash
focusguard
```
```text
FocusGuard Appliance Console
─────────────────────────────────────────────
 1. View Appliance Status
 2. List Blocked Domains
 3. Add Blocked Domain
 4. Remove Blocked Domain
 5. Start Locked Focus Session
 6. View Active Session
 7. Stop Active Session
 8. Live Network Monitor
 9. Traffic Analytics & Stats
10. Gateway Redirection
11. Manage Distraction Services
12. Discovered Network Devices
13. Bypass Defense & VPN Resistance
14. Packet Monitor & Traffic Statistics
15. View Audit Logs
16. Exit
─────────────────────────────────────────────
Select an option [1-16]: 


```

---

## System Diagnostics (`focusguard doctor`)

Run the comprehensive self-test anytime to verify network health, interfaces, and DNS resolution:

```bash
focusguard doctor
```
```text
FocusGuard System & Network Diagnostics (Doctor)
══════════════════════════════════════════════════════════════
Overall Health: OPTIMAL

  [✓ PASS] Network Interfaces
         IPv4: 192.168.1.50 | IPv6: 2001:db8::50

  [✓ PASS] Upstream Internet DNS
         Connected to upstream resolvers (1.1.1.1 / 9.9.9.9)

  [✓ PASS] DNS Server (Port 53)
         DNS Engine configured on port 53

  [🔒 LOCKED] Focus Session State
         Status: LOCKED | Expires: 2026-09-09T23:30:00+00:00

  [✓ PASS] IPv6 DNS Protection
         IPv6 addresses detected. FocusGuard dual-stack DNS filters IPv6 AAAA queries.

  [✓ PASS] DoH/DoT Countermeasures
         Known public DoH bootstrap domains sinkholed. SVCB/HTTPS records suppressed.

  [✓ PASS] System Clock & Time Guard
         Current UTC Time: 2026-09-09T20:19:00+00:00
══════════════════════════════════════════════════════════════
```

---

## Router Configuration

To distribute DietPi's DNS address to all devices on your LAN:
1. Log in to your home router admin interface (`http://192.168.1.1`).
2. Navigate to **LAN -> DHCP Server**.
3. Set **Primary DNS Server** to your DietPi IP address (`192.168.1.50`).
4. **Leave Secondary DNS EMPTY** (do not enter 8.8.8.8 or 1.1.1.1, or clients will bypass the blocker).
5. Save settings and reconnect your devices to Wi-Fi.

For full brand-specific router guides (ASUS, TP-Link, Netgear, OpenWrt), see [docs/ROUTER_SETUP.md](file:///c:/Users/kamru/OneDrive/Documents/Cyber%20Security/NET_BLOCKER/docs/ROUTER_SETUP.md).

---

## Emergency Recovery

If you ever need to restore standard internet access without DietPi:
- Change your router's Primary DNS back to `1.1.1.1` or `8.8.8.8` and reboot the router.
- See [docs/RECOVERY.md](file:///c:/Users/kamru/OneDrive/Documents/Cyber%20Security/NET_BLOCKER/docs/RECOVERY.md) for step-by-step recovery options.

---

## Testing

Run the full automated test suite using `pytest`:
```bash
python -m pytest tests -v
```

---

## License

MIT License. Designed for private home network administration and personal focus.
