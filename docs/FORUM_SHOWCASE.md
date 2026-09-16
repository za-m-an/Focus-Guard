# Open Source Forum Showcase & Launch Kit

Use the templates below when publishing **FocusGuard** on open-source communities, self-hosted forums, Reddit, and Hacker News.

---

## 1. Reddit Template (r/selfhosted, r/dietpi, r/raspberry_pi, r/getdisciplined)

**Post Title Suggestions:**
* *Show r/selfhosted: FocusGuard — Network-wide distraction blocker & anti-impulse focus enforcer for DietPi / Raspberry Pi*
* *I built FocusGuard: A self-hosted network appliance that locks down distractions across every phone, TV, and console on your Wi-Fi (pure Python, zero dependencies)*

**Post Body:**
```markdown
Hey r/selfhosted!

Like many of you, I struggled with phone and web distractions when trying to get deep work done. Browser extensions and phone screen-time apps never worked for me because during moments of low willpower, they take literally 5 seconds to disable or bypass.

I wanted something that acts like a physical lockbox for my entire home network. So I built **FocusGuard** — a dedicated, self-hosted distraction blocking appliance designed specifically for single-board computers running **DietPi** (or Raspberry Pi OS / Debian).

GitHub: https://github.com/za-m-an/Focus-Guard

### What makes it different?

1. **Enforced at the Network Layer:** Instead of installing apps on each device, FocusGuard sits at your router/DNS layer. When you start a focus session, it blocks distractions on your iPhone, Android, work laptop, Smart TV, and gaming consoles simultaneously.
2. **Strict Anti-Impulse Lock:** Once you run `focusguard start -d 3h`, the session is locked. There is no pause button, no override password, and no "give me 5 more minutes". Even if you restart the DietPi board or restart the systemd service, state is persisted atomically with boot-ID tracking and clock-rollback detection.
3. **Whole-Service & App Catalog:** You don't have to manually hunt down CDN domains or companion APIs. Running `focusguard service block instagram` or `focusguard start -d 2h --services youtube xbox playstation` automatically kills the web portals, mobile app APIs (Stories/Reels), and background CDNs.
4. **Transparent Gateway Mode:** With `focusguard gateway enable`, it uses kernel IP forwarding and iptables to transparently redirect rogue port 53 traffic, preventing smart devices or browsers with hardcoded resolvers (8.8.8.8, 1.1.1.1) from bypassing the sinkhole.
5. **Real-time Live Packet Inspection:** Built-in `focusguard packet-monitor` inspects IPv4/IPv6 headers, TCP flags, UDP ports, and bidirectional flows using Linux AF_PACKET raw sockets with zero third-party libraries.
6. **Zero External Runtime Dependencies:** Written in 100% pure Python 3.10+ using only standard library modules. Consumes less than 15 MB RAM on a DietPi device.

### Supported Platforms out of the box:
* **Social:** YouTube, Instagram, TikTok, Facebook, Reddit, Twitter / X
* **Gaming & Consoles:** Xbox & Game Pass, PlayStation & PSN, Steam, Discord, Roblox, Epic Games / Fortnite, Nintendo Switch
* **Streaming & Stores:** Netflix, Twitch, Spotify, Google Play Store

### Quick Install (DietPi / Debian):
```bash
git clone https://github.com/za-m-an/Focus-Guard.git
cd Focus-Guard
sudo bash scripts/install.sh
focusguard
```

Would love to hear your thoughts, feedback, or suggestions for additional service definitions!
```

---

## 2. Hacker News Template (Show HN)

**Post Title:**
`Show HN: FocusGuard – Network-wide anti-impulse focus enforcer for DietPi (Python)`

**Post URL:**
`https://github.com/za-m-an/Focus-Guard`

**Post Body (if text post or first comment):**
```text
Hey HN,

I built FocusGuard, a self-hosted network appliance for DietPi/Debian designed to eliminate digital distractions across an entire home LAN.

Existing tools (browser extensions, Screen Time, Freedom) operate at the application layer and suffer from the fundamental flaw that the user who enables them can disable them during moments of cognitive fatigue or impulse.

FocusGuard operates at the network layer with a dual-stack IPv4/IPv6 DNS sinkhole and transparent iptables gateway:

- Anti-Impulse Invariant: Once a timed session begins (`focusguard start -d 4h`), state is cryptographically persisted with boot-ID tracking and clock-rollback detection. It rejects pause, cancellation, or domain-removal requests until the timer naturally elapses.
- Full Ecosystem Blocking: Modern mobile apps do not fail when you block the primary domain; they fall back to companion APIs and CDN edge nodes. FocusGuard ships with catalog definitions covering web, mobile background sync, and CDNs for platforms like YouTube (googlevideo), Instagram, TikTok, Xbox Live, PSN, Discord, and Steam.
- Packet-Level Monitoring: Built-in non-blocking packet observer using Linux AF_PACKET raw sockets that inspects headers (TCP flags, UDP ports, IPv6 NextHeader) and aggregates traffic into bidirectional 5-tuple connection flows with idle pruning.
- Zero Runtime Dependencies: Built using only the Python 3.10+ standard library (`socket`, `asyncio`, `struct`, `sqlite3`). Total memory footprint is under 15 MB on a headless Raspberry Pi.

Code and architecture details: https://github.com/za-m-an/Focus-Guard

Feedback and critiques welcome!
```

---

## 3. DietPi Community Forum Template

**Post Title:**
*FocusGuard — Lightweight Network-Wide Focus & Distraction Blocker for DietPi*

**Category:**
*Software Showcase / Community Projects*

**Post Body:**
```markdown
Hi DietPi community,

I'd like to share **FocusGuard**, an open-source project tailored specifically for DietPi home servers:
https://github.com/za-m-an/Focus-Guard

### Why DietPi?
DietPi is famous for being minimal, extremely efficient, and reliable on SBCs. FocusGuard was architected with the exact same philosophy:
- **Zero PIP dependencies:** Pure Python standard library implementation.
- **Lightweight footprint:** Uses less than 15 MB of RAM and negligible CPU cycles.
- **Systemd Integration:** Runs as a standard background systemd service (`focusguardd.service`) with non-root capability separation (`CAP_NET_BIND_SERVICE`, `CAP_NET_RAW`).
- **Interactive Terminal UI:** Run `focusguard` over SSH to manage everything through a clean, menu-driven interface with ANSI color cards.

### Features
- Dual-stack DNS sinkholing (IPv4 & IPv6).
- Tamper-resistant locked focus sessions (survives reboots and SSH disconnects).
- Service-level distraction blocking (YouTube, Instagram, TikTok, Xbox, PlayStation, Steam, Discord, etc.).
- Optional transparent gateway redirection with iptables.
- Live packet and flow monitoring (`focusguard packet-monitor`).
- Comprehensive diagnostics via `focusguard doctor`.

Automated installation script is included:
```bash
git clone https://github.com/za-m-an/Focus-Guard.git
cd Focus-Guard
sudo bash scripts/install.sh
```

Thanks to the DietPi team for creating such an amazing lightweight OS!
```
