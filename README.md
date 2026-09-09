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

## Interactive Menu

If you prefer navigating via an interactive menu rather than typing flags:
```bash
focusguard
```
```text
FocusGuard Appliance Console
────────────────────────────────
1. View Appliance Status
2. List Blocked Domains
3. Add Blocked Domain
4. Remove Blocked Domain
5. Start Locked Focus Session
6. View Active Session
7. Run Diagnostics (Doctor)
8. View Audit Logs
9. Exit
────────────────────────────────
Select an option [1-9]: 
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
