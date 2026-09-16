# FocusGuard v1.0.0 — Production Release

> **Network-Wide Focus & Distraction Enforcement for DietPi Home Servers**

FocusGuard v1.0.0 is the first production release of our self-hosted, network-wide distraction blocker and focus enforcement appliance designed for DietPi and single-board Linux computers.

Unlike browser extensions or phone apps that can be uninstalled in seconds during moments of low willpower, FocusGuard enforces focus sessions at the **home network layer**, protecting every phone, laptop, smart TV, and gaming console connected to your home Wi-Fi.

---

## Key Highlights & Features

### 1. Dual-Stack DNS Sinkhole Engine
* Pure-Python, zero-external-dependency asynchronous DNS engine listening on port 53 (UDP & TCP).
* Dual-stack support for both IPv4 (`A` records → `0.0.0.0`) and IPv6 (`AAAA` records → `::`).
* Instant sub-millisecond local sinkholing with upstream forwarding (Cloudflare / Quad9) for permitted traffic.
* Memory-efficient in-memory domain trie matching with wildcard and companion domain resolution.

### 2. Tamper-Resistant Anti-Impulse Locked Sessions
* Timed focus sessions (e.g. `focusguard start -d 4h` or `focusguard start -u 22:30`).
* **Anti-Impulse Lock:** Once started, sessions cannot be paused, edited, shortened, or stopped until the timer naturally expires.
* **Persistent State:** Survives server reboots, systemctl service restarts, and SSH disconnects via atomic disk persistence and Linux boot ID tracking.
* **Clock Rollback Protection:** Detects if the system clock was manipulated backwards and refuses early release.

### 3. Service-Level Distraction Catalog (Web & Mobile Apps)
* Single-command blocking of entire platforms across browsers and native iOS/Android mobile applications:
  * **Social Media:** YouTube, Instagram, Facebook & Messenger, TikTok, Twitter / X, Reddit.
  * **Streaming:** Netflix, Twitch, Spotify.
  * **Gaming & Consoles:** Xbox & Game Pass, PlayStation & PSN, Steam / Valve, Discord, Roblox, Epic Games & Fortnite, Nintendo & Switch Online.
  * **App Stores:** Google Play Store & background download services.
* Automatically bundles authentication APIs, companion domains, background sync endpoints, and media delivery CDNs.

### 4. Transparent Network Gateway & Interception
* Optional transparent redirection via Linux `iptables` and kernel IP forwarding (`focusguard gateway enable`).
* Intercepts outbound port 53 traffic from rogue IoT devices or hardcoded DNS resolvers (e.g. 8.8.8.8, 1.1.1.1).
* Enforces network-wide policies without requiring manual DNS configuration on every individual client device.

### 5. Live Packet-Level Monitoring & Header Inspection
* Non-blocking packet observer using Linux `AF_PACKET` raw sockets with zero third-party dependencies.
* Inspects IPv4/IPv6 headers, TCP flags (SYN, ACK, FIN, RST, PSH), UDP ports, ICMP/ICMPv6, and ARP frames.
* Bidirectional 5-tuple flow tracking with idle pruning and active connection metrics (`focusguard packet-monitor`).
* Safe, bounded packet inspection (`focusguard packet inspect --id <ID> --hex`) with terminal flood protection.

### 6. Discovered Device Tracking & Traffic Analytics
* Automatically correlates network traffic with local devices using ARP/DHCP tables (`focusguard devices`).
* Live CLI network stream (`focusguard monitor`) showing real-time query flows and blocking actions.
* Session-scoped and all-time traffic analytics (`focusguard stats`).

### 7. VPN & Encrypted DNS Bypass Defense
* Hardened countermeasures against casual focus session evasion (`focusguard bypass-status`).
* Sinkholes bootstrap endpoints for 10+ public DoH resolvers and suppresses DNS SVCB/HTTPS records.
* Restricts common VPN ports (WireGuard 51820, OpenVPN 1194, IPsec 500/4500).

---

## Installation & Quickstart

```bash
# 1. Clone repository
git clone https://github.com/za-m-an/Focus-Guard.git
cd Focus-Guard

# 2. Run automated installer (configures systemd service & CLI)
sudo bash scripts/install.sh

# 3. Check appliance health
focusguard doctor

# 4. Launch interactive terminal menu
focusguard
```

---

## Technical Specifications

* **Operating System:** Optimized for DietPi (Debian 11/12/Bookworm). Compatible with Raspberry Pi OS, Ubuntu, Debian.
* **Runtime:** Python 3.10+ (pure standard library, 0 external runtime pip dependencies).
* **Network Overhead:** < 15 MB RAM, sub-millisecond DNS lookup latency.
* **License:** MIT License.
