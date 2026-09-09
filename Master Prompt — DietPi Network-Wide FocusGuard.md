# MASTER PROMPT
# FocusGuard — DietPi Network-Wide Distraction Blocking System

## ROLE

You are a senior Linux systems engineer, network engineer, cybersecurity engineer, software architect, and production-grade CLI application developer.

Your task is to design and build a **production-quality, self-hosted, network-wide distraction-blocking system** intended to run entirely on a **DietPi home server**.

The purpose of the system is simple:

> Allow the authorized owner of a private home network to temporarily block distracting websites across the entire network so they can focus on study or work.

The application must be designed as a **server appliance**, not as a Windows application.

There must be:

- NO Windows control panel
- NO desktop GUI requirement
- NO browser extension requirement
- NO cloud account requirement
- NO mandatory client application on every device
- NO dependence on a desktop computer remaining powered on

The only normal management interface should be a **terminal CLI accessed over SSH**.

---

# 1. CORE CONCEPT

The entire system runs on the DietPi server.

The user connects through SSH:

```bash
ssh user@server
```

and then runs the application's CLI.

For example:

```bash
focusguard start
```

The user can configure websites, start a focus session, inspect status, and manage the system entirely through the terminal.

Once a focus session begins, the user should be able to disconnect from SSH.

The DietPi server must continue enforcing the policy independently.

Conceptually:

```text
                    INTERNET
                       │
                       ▼
                 HOME ROUTER
                       │
                       ▼
                ┌─────────────┐
                │   DietPi    │
                │   SERVER    │
                │             │
                │ FocusGuard  │
                │             │
                │ CLI         │
                │ Policy      │
                │ Scheduler   │
                │ Lock Engine │
                │ DNS/Network │
                │ Enforcement │
                │ Persistence │
                └──────┬──────┘
                       │
                     HOME LAN
            ┌──────────┼──────────┐
            ▼          ▼          ▼
         Laptop       Phone      TV
```

---

# 2. IMPORTANT NETWORK REQUIREMENT

The objective is **network-wide blocking**.

A hosts-file modification or browser extension is NOT sufficient.

Do not design the primary system around:

- `/etc/hosts`
- Windows hosts file
- browser extensions
- browser settings
- per-device firewall rules
- client-side scripts

Those can be optional fallback mechanisms, but they are NOT the primary architecture.

The system must operate at an appropriate network-level enforcement point.

Investigate and choose the best legitimate architecture for a DietPi home server.

Potential mechanisms may include:

- local DNS filtering
- local recursive DNS resolver
- DNS proxy
- gateway/router integration
- DHCP-based DNS assignment
- transparent network enforcement
- DietPi acting as a gateway
- another technically sound network-level approach

Choose the architecture based on:

- reliability
- security
- maintainability
- performance
- cross-device coverage
- IPv4 support
- IPv6 support
- encrypted DNS considerations
- ease of recovery

Do NOT assume that all routers provide the same capabilities.

---

# 3. DIETPI IS THE PRIMARY HOST

Treat DietPi as the permanent appliance.

The application should run as a persistent Linux service.

It must continue functioning when:

- SSH disconnects
- the terminal is closed
- the user logs out
- no SSH session exists
- the CLI is not open
- the user's laptop is turned off

The core blocking engine must never depend on the SSH session remaining alive.

Use an appropriate Linux service manager such as the system's native service infrastructure if that is the most appropriate choice.

The application must start automatically after reboot where appropriate.

---

# 4. NO DESKTOP CONTROL PANEL

Do not build a Windows GUI.

Do not build a desktop application unless it is absolutely necessary for some future optional feature.

The system must be fully usable through the terminal.

The CLI should be intuitive and professional.

Example:

```bash
focusguard status
focusguard add youtube.com
focusguard remove youtube.com
focusguard list
focusguard start
focusguard stop
focusguard session
focusguard schedule
focusguard logs
focusguard doctor
```

The exact command structure may be improved during architecture design.

---

# 5. SSH-FIRST WORKFLOW

The expected workflow is:

```bash
ssh user@dietpi
```

Then:

```bash
focusguard
```

The application may provide either:

1. a traditional command-based CLI, or
2. an interactive terminal UI / menu,

or support both.

The user must be able to accomplish all important tasks without opening another device.

---

# 6. BASIC WEBSITE BLOCKING

The user must be able to add domains.

Examples:

```text
youtube.com
facebook.com
instagram.com
reddit.com
tiktok.com
```

Support user input such as:

```text
youtube.com
www.youtube.com
https://youtube.com
https://www.youtube.com/watch?v=123
```

Normalize the input into a valid domain/policy representation.

Do not treat a full URL path as though it were a unique network-level domain rule.

Explain limitations clearly.

---

# 7. DOMAIN AND SUBDOMAIN BEHAVIOR

Provide sensible domain matching.

For example:

```text
youtube.com
```

may be interpreted as applying to the domain and relevant subdomains, depending on the selected policy model.

Clearly communicate the behavior.

Do not falsely claim that blocking one domain automatically blocks all third-party domains used by that website.

For complex services such as video platforms, identify that multiple domains/CDNs/API endpoints may be involved.

---

# 8. FOCUS SESSION

The defining feature of the application is the **Focus Session**.

The user should be able to create a temporary blocking session.

Example:

```text
focusguard start
```

Then:

```text
Enter domains:
youtube.com
facebook.com
instagram.com
reddit.com

Session duration:
4h
```

The system should display:

```text
╔══════════════════════════════════════╗
║        🔒 LOCKED FOCUS SESSION       ║
╠══════════════════════════════════════╣
║ Started: 20:00                       ║
║ Ends:    00:00                       ║
║ Remaining: 03:59:58                  ║
║                                      ║
║ Blocked domains: 4                   ║
║ Status: ACTIVE                       ║
╚══════════════════════════════════════╝
```

After the user starts the session, they can disconnect from SSH.

The server continues operating.

---

# 9. TIMESTAMP-BASED LOCK

The user specifically requires the ability to specify a timestamp.

Support both:

### Duration

```text
2h
45m
6h
```

and:

### Absolute end time

For example:

```text
Ends at:
23:30
```

or an appropriate absolute date/time format.

Store the session as an **absolute expiration timestamp**.

Do NOT rely solely on an in-memory countdown.

For example:

```text
session_started = 2026-09-09T20:00:00
session_expires = 2026-09-09T23:30:00
```

This ensures correct behavior after:

- server reboot
- service restart
- crash
- SSH disconnect
- terminal closure

---

# 10. LOCKED MODE

This requirement is CRITICAL.

When a Focus Session is active, the user must NOT be able to normally cancel the session through the application.

During the locked period:

```text
focusguard stop
```

must not disable blocking.

Likewise:

```text
focusguard pause
focusguard clear
focusguard remove youtube.com
focusguard edit
focusguard reset
```

must not bypass the session.

The CLI should respond with something similar to:

```text
ERROR: Focus session is locked.

Blocking cannot be modified until:
2026-09-10 00:00:00

Time remaining:
02:14:32
```

The exact wording is your choice.

---

# 11. WHAT "LOCKED" MEANS

During a locked session:

### Disabled:

- pause
- stop
- remove blocked domains
- modify active blocking rules
- disable the enforcement backend
- change session expiration
- reset policy
- bypass the session through normal application commands

### Allowed:

- view status
- view remaining time
- view logs
- inspect configuration
- check network health
- run diagnostic commands that do not alter enforcement

The user should still be able to safely inspect the state of the system.

---

# 12. ANTI-IMPULSE DESIGN

The purpose of the lock is behavioral:

> Prevent the user from casually deciding to disable the blocker when they become distracted.

Do not turn this into malware.

Do not attempt to make the machine physically or cryptographically impossible for its authorized administrator to control.

A root administrator can always ultimately terminate a Linux service or alter the machine.

That is acceptable.

The system should instead make **normal, impulsive bypassing difficult**.

Document this distinction clearly.

---

# 13. PERSISTENCE OF LOCKED SESSION

The locked session state must be stored persistently.

If the DietPi server reboots while a session is active:

1. The service starts.
2. The saved session is loaded.
3. The current time is compared against the expiration timestamp.
4. If the session has not expired, blocking is restored.
5. If it has expired, the session is released automatically.
6. If the system clock changed unexpectedly, handle the situation safely.

Never assume the process will remain alive continuously.

---

# 14. AUTOMATIC SESSION EXPIRATION

When the timestamp is reached:

```text
23:30
```

the system should automatically:

1. End the locked session.
2. Release temporary focus-session rules.
3. Restore the previous policy state where appropriate.
4. Record the event in the log.
5. Report the session as completed.

Example:

```text
✓ Focus session completed.

Started: 20:00
Ended:   23:30
Duration: 3h 30m
```

The user should not need to reconnect to SSH to release it.

---

# 15. BACKGROUND OPERATION

The CLI is only a control mechanism.

The actual application must run in the background.

For example:

```text
SSH terminal
     │
     ▼
FocusGuard CLI
     │
     ▼
Persistent FocusGuard Service
     │
     ├── Policy Engine
     ├── Scheduler
     ├── Lock Manager
     └── Network Enforcement
```

After:

```bash
exit
```

the service must continue.

---

# 16. NETWORK-WIDE ENFORCEMENT

The system must clearly distinguish between:

```text
Network-wide enforcement
```

and:

```text
Server-local enforcement
```

If the DietPi server is only running a DNS service but client devices do not actually use it, do not claim network-wide protection.

The application should verify as much as technically possible that the selected enforcement mechanism is active.

The status command should communicate the real state.

Example:

```text
Network Enforcement
────────────────────────
Status: ACTIVE
Method: DNS Gateway
IPv4:   Protected
IPv6:   Protected
```

or:

```text
Status: WARNING

DNS filtering is active on the server,
but devices may bypass it through
external DNS configuration.
```

---

# 17. ROUTER ARCHITECTURE

Analyze two major possibilities:

### Architecture A

DietPi provides network-wide DNS filtering while the router remains the primary gateway.

### Architecture B

DietPi becomes the actual network gateway between the router/Internet and LAN.

Choose the architecture that is most appropriate for the user's physical network.

Do not force gateway mode if the hardware/network topology makes it inappropriate.

If the chosen design requires:

- two network interfaces
- VLANs
- routing
- DHCP
- static addressing
- router configuration

explain exactly why.

---

# 18. IPV4 AND IPV6

IPv6 must not be ignored.

If IPv6 is enabled on the network, the application must determine whether traffic can bypass the enforcement layer.

The system must either:

1. correctly cover IPv6, or
2. explicitly identify IPv6 as unprotected and explain how to configure the network properly.

Never display:

```text
NETWORK-WIDE PROTECTION: ACTIVE
```

while an obvious IPv6 bypass exists.

---

# 19. ENCRYPTED DNS

Modern systems may use:

- DNS over HTTPS
- DNS over TLS
- browser-level secure DNS
- hardcoded DNS providers

The system must analyze these bypasses.

Where appropriate and legitimate for the user's own network:

- document mitigations
- provide configuration guidance
- detect likely bypass conditions
- report limitations

Do NOT decrypt HTTPS traffic.

Do NOT install unauthorized certificates.

Do NOT perform malicious man-in-the-middle interception.

---

# 20. HTTPS

The system should operate without inspecting HTTPS content.

The preferred architecture should block websites through domain/network policy rather than decrypting user traffic.

Clearly explain:

```text
DNS/domain filtering
≠
HTTPS content inspection
```

Privacy must be preserved.

---

# 21. VPN AND OTHER NETWORK BYPASSES

Recognize that devices can potentially bypass network filtering through:

- VPNs
- proxies
- mobile data
- encrypted DNS
- alternate domains
- IPv6
- other networks

Document these.

Where technically appropriate, provide legitimate network-administration mitigations.

Do not attempt covert surveillance or malicious interception.

---

# 22. CATEGORY SUPPORT

Architect the policy engine so future categories are possible.

Examples:

```text
Social Media
Streaming
Gaming
News
Shopping
Entertainment
```

Categories are optional for the MVP.

Do not make the architecture dependent on hard-coded category lists.

---

# 23. ALLOWLIST MODE

Optionally support a restrictive study mode:

```text
Only approved domains are accessible.
```

For example:

```text
bracu.ac.bd
github.com
stackoverflow.com
wikipedia.org
```

This should be implemented as a separate policy mode.

Clearly warn the user that allowlist mode is substantially more restrictive.

---

# 24. SCHEDULING

Support recurring study schedules as a future or advanced feature.

Example:

```text
Monday-Friday
08:00-12:00
14:00-18:00
```

Schedules should operate server-side.

They must not depend on an active SSH session.

---

# 25. POLICY ENGINE

Use a clean internal abstraction.

Conceptually:

```text
Policy
 ├── blocked_domains
 ├── allowed_domains
 ├── categories
 ├── schedules
 ├── active_session
 ├── expiration_time
 └── exceptions
```

Keep policy logic separate from network implementation.

---

# 26. ENFORCEMENT BACKENDS

Design the system so the network enforcement layer is modular.

Conceptually:

```text
EnforcementBackend
 ├── DNS
 ├── Router
 ├── Gateway
 └── LocalFallback
```

The exact architecture is up to you.

The purpose is future extensibility.

---

# 27. CLI DESIGN

The CLI should be polished.

Possible commands:

```bash
focusguard status
focusguard add DOMAIN
focusguard remove DOMAIN
focusguard list

focusguard start
focusguard start --duration 4h
focusguard start --until 23:30

focusguard session
focusguard stop

focusguard schedule
focusguard logs

focusguard doctor
focusguard network

focusguard config
```

Design the exact syntax based on good CLI conventions.

Provide:

- help
- version
- clear errors
- sensible exit codes
- machine-readable output where useful

---

# 28. INTERACTIVE CLI

An interactive mode would also be useful.

For example:

```text
FocusGuard
──────────

1. View status
2. Manage blocked websites
3. Start focus session
4. View active session
5. View network status
6. View logs
7. Diagnostics
8. Exit
```

This is optional if the standard command-based CLI is sufficiently intuitive.

---

# 29. STATUS COMMAND

The status output should provide a clear overview.

For example:

```text
FocusGuard Status
────────────────────────────

Service:           ACTIVE
Network Filter:    ACTIVE
Policy:            FOCUS SESSION
Session:           LOCKED

Started:           20:00
Expires:           23:30
Remaining:         02:17:42

Blocked Domains:   7

IPv4:              PROTECTED
IPv6:              PROTECTED

DNS Enforcement:   ACTIVE
```

The displayed information must reflect reality.

---

# 30. LOGGING

Maintain useful operational logs.

Examples:

```text
20:00 Focus session started
20:00 youtube.com added to active policy
20:00 Network enforcement activated
21:13 DNS request blocked
23:30 Focus session expired
23:30 Previous policy restored
```

Do not build a browsing surveillance system.

Avoid storing unnecessary browsing history.

Do not store page contents.

Do not store credentials.

Do not capture packet payloads.

Provide reasonable log retention.

---

# 31. PRIVACY

The system should be local-first.

Do not require:

- cloud accounts
- telemetry
- advertising
- third-party analytics
- remote tracking

The user's network data should remain on the server unless explicitly configured otherwise.

---

# 32. SECURITY MODEL

Treat FocusGuard as a security-sensitive network service.

Requirements:

- validate all domains
- sanitize all input
- prevent command injection
- avoid unsafe shell interpolation
- use safe subprocess APIs
- minimize privileges
- isolate privileged network operations
- secure configuration files
- restrict management interfaces
- authenticate privileged network APIs where necessary
- prevent unauthorized LAN access to management functions
- fail safely
- handle malformed input
- protect against configuration corruption

Never expose an unauthenticated management API on the LAN.

---

# 33. ROOT PRIVILEGES

If network configuration requires elevated privileges, separate privileged operations from ordinary CLI functionality.

Do not run the entire application as root merely because one component needs elevated privileges.

Use least privilege where practical.

Clearly document which operations require elevated access.

---

# 34. INSTALLATION

Create a clean DietPi installation process.

The installer should:

1. Detect operating system.
2. Verify required packages.
3. Verify network configuration.
4. Assign or validate a stable server address if required.
5. Install the service.
6. Configure required network components.
7. Save existing configuration before changing it.
8. Enable startup at boot.
9. Run a health check.
10. Explain any required router configuration.

---

# 35. SAFE NETWORK CHANGES

Before modifying:

- DNS
- DHCP
- routes
- firewall rules
- gateway settings
- resolver configuration

the software should save the previous state.

Every change must have a rollback path.

---

# 36. RECOVERY MODE

Provide a reliable emergency recovery mechanism.

Examples:

```bash
focusguard doctor
focusguard restore
```

The exact implementation is up to you.

The user must have a documented way to recover from an incorrect network configuration.

Do not lock the user permanently out of their own network.

---

# 37. NETWORK CHANGE HANDLING

The service should detect relevant network changes.

Examples:

- DHCP address changes
- interface changes
- Wi-Fi/Ethernet changes
- gateway changes
- DNS changes
- IPv6 state changes

It should re-evaluate the enforcement configuration where appropriate.

---

# 38. SERVER REBOOT BEHAVIOR

After reboot:

1. Start FocusGuard.
2. Load persistent configuration.
3. Determine current network state.
4. Determine whether a focus session was active.
5. Compare current time with expiration timestamp.
6. Restore active blocking if the session remains valid.
7. Automatically release expired sessions.
8. Log recovery behavior.

The system must recover safely.

---

# 39. TIME HANDLING

Time is critical because locked sessions depend on it.

Handle:

- timezone
- NTP synchronization
- daylight-saving changes where applicable
- system clock changes
- reboot
- suspended systems
- invalid timestamps

Prefer robust absolute-time representations.

Do not rely purely on `sleep(14400)` or an in-memory countdown.

---

# 40. CLOCK TAMPERING

Consider what happens if the user changes the server clock during a locked session.

The system should detect suspicious time changes where practical.

Do not claim impossible protection.

Document the limitation.

Use a sensible monotonic/absolute-time strategy appropriate to Linux.

---

# 41. TESTING

Build automated tests for:

### Domain normalization

```text
youtube.com
www.youtube.com
https://youtube.com
https://youtube.com/path
```

### Policy behavior

- add domain
- remove domain
- activate policy
- deactivate policy
- active session
- expired session

### Lock behavior

Verify:

```text
stop → rejected
pause → rejected
remove → rejected
edit → rejected
```

while locked.

### Persistence

Test:

- service restart
- application restart
- server reboot
- SSH disconnect

### Time

Test:

- duration sessions
- absolute timestamps
- expiration
- timezone handling
- clock changes

### Networking

Test:

- IPv4
- IPv6
- DNS failures
- gateway failures
- DNS bypass
- network changes

---

# 42. REAL NETWORK TEST

The final system should be tested with multiple actual devices.

Example:

```text
DietPi server
Windows laptop
Android phone
Smart TV
Another PC
```

Start:

```text
Block youtube.com
```

Then verify access behavior from every device.

Remove the rule after testing and verify normal connectivity returns.

Do not consider the project complete merely because the server itself cannot resolve a blocked domain.

---

# 43. SECURITY TESTING

Perform security review for:

- command injection
- privilege escalation
- unauthorized API access
- configuration tampering
- malformed domains
- malicious input
- service permissions
- local socket permissions
- exposed ports
- DNS poisoning considerations
- DNS rebinding
- API authentication
- log injection

The system should not introduce unnecessary network attack surfaces.

---

# 44. DOCUMENTATION

Create a complete README.

Include:

## What it is

A self-hosted network-wide focus/distraction blocker for private networks.

## Architecture

Explain the DietPi server and network flow.

## Installation

Explain setup step-by-step.

## Usage

Explain every major CLI command.

## Focus sessions

Explain duration and absolute timestamp modes.

## Locked sessions

Explain exactly what becomes unavailable during an active lock.

## Networking

Explain router, DNS, gateway, IPv4, IPv6, and encrypted DNS requirements.

## Limitations

Be honest.

## Recovery

Explain how to restore networking.

## Security

Document the threat model.

## Development

Document project structure and testing.

---

# 45. MVP

The first implementation should focus on:

1. DietPi deployment
2. Persistent background service
3. CLI
4. Domain management
5. Network-level DNS/domain blocking
6. Focus sessions
7. Duration-based sessions
8. Absolute timestamp sessions
9. Locked session state
10. Persistent expiration
11. Automatic expiration
12. Status
13. Logs
14. Safe rollback
15. Reboot recovery
16. IPv4/IPv6 analysis
17. Documentation

Do NOT waste time initially building:

- desktop GUIs
- mobile apps
- cloud dashboards
- accounts
- social features
- unnecessary analytics

---

# 46. DEVELOPMENT PHILOSOPHY

Do not blindly choose a programming language or framework.

Select technologies based on:

- DietPi/Linux compatibility
- reliability
- low resource consumption
- networking capabilities
- long-term maintainability
- security
- ease of installation
- CLI quality
- service integration
- debugging ability

The software should comfortably run on modest hardware.

Avoid unnecessary dependencies.

Prefer mature, well-maintained technologies.

---

# 47. RESOURCE EFFICIENCY

DietPi is designed for lightweight deployments.

The application should therefore be:

- low CPU usage
- low RAM usage
- efficient
- stable over long periods
- suitable for always-on operation

Do not build a heavyweight application when a lightweight service will work.

---

# 48. ARCHITECTURE BEFORE CODE

Before writing the implementation, produce:

1. Requirements analysis
2. Technical constraints
3. Architecture comparison
4. Selected architecture
5. Network topology
6. DNS/network flow
7. Security model
8. Privilege model
9. Project structure
10. Data model
11. CLI design
12. Locked-session state machine
13. Failure/recovery model
14. Testing plan

Then implement.

---

# 49. LOCKED SESSION STATE MACHINE

Model the session explicitly.

For example:

```text
                    ┌─────────────┐
                    │    IDLE     │
                    └──────┬──────┘
                           │
                     START SESSION
                           │
                           ▼
                 ┌──────────────────┐
                 │      ACTIVE      │
                 │      LOCKED      │
                 └───────┬──────────┘
                         │
                  TIME EXPIRES
                         │
                         ▼
                 ┌──────────────────┐
                 │     EXPIRED      │
                 └───────┬──────────┘
                         │
                         ▼
                     RESTORED
```

The exact state machine may be more sophisticated.

The important thing is that the locked state must be explicit and persistent.

---

# 50. ACTIVE POLICY VS SESSION POLICY

Separate:

### Permanent configuration

Example:

```text
User's normal blocklist
```

from:

### Temporary session policy

Example:

```text
Temporary 4-hour study block
```

When the focus session expires, restore the appropriate previous policy state.

Do not accidentally delete the user's permanent configuration.

---

# 51. ADMINISTRATIVE SAFETY

The software is intended for its authorized administrator.

Therefore:

- do not attempt to lock the administrator permanently out of the operating system
- do not modify SSH configuration unnecessarily
- do not disable emergency local access
- do not hide the service
- do not use stealth persistence techniques

The service should be transparent and auditable.

---

# 52. NO MALWARE-LIKE BEHAVIOR

Do NOT implement:

- stealth persistence
- hidden processes
- credential theft
- keylogging
- packet sniffing for private content
- unauthorized device control
- certificate installation for HTTPS interception
- remote exploitation
- privilege escalation techniques
- covert surveillance

This is a legitimate self-hosted network administration and productivity tool.

---

# 53. TECHNICAL HONESTY

This is mandatory.

Never say a feature works unless it has actually been tested or verified.

Use states such as:

```text
SUPPORTED
PARTIALLY SUPPORTED
REQUIRES MANUAL CONFIGURATION
ROUTER DEPENDENT
NOT SUPPORTED
```

Be especially honest about:

- IPv6
- encrypted DNS
- VPNs
- router compatibility
- gateway requirements
- devices using alternate networks

---

# 54. OBSERVABILITY

Provide:

```bash
focusguard status
```

and:

```bash
focusguard doctor
```

The diagnostic system should check:

- service health
- network interface
- gateway
- DNS
- resolver
- policy engine
- enforcement backend
- IPv4
- IPv6
- current session
- expiration timestamp
- configuration integrity

Return useful recommendations.

---

# 55. PROJECT STRUCTURE

Use a clean modular project structure.

Conceptually:

```text
focusguard/
│
├── cli/
├── core/
│   ├── policy/
│   ├── sessions/
│   ├── scheduler/
│   └── configuration/
│
├── network/
│   ├── dns/
│   ├── gateway/
│   └── detection/
│
├── service/
├── security/
├── logging/
├── tests/
├── docs/
└── installer/
```

The actual structure is up to you.

---

# 56. FINAL PRODUCT EXPERIENCE

The finished product should feel like a lightweight Linux network appliance.

A typical session should feel like:

```text
$ focusguard start --until 23:30

✓ Network enforcement verified

Blocked:
  • youtube.com
  • facebook.com
  • instagram.com
  • reddit.com

🔒 LOCKED FOCUS SESSION

Started: 20:00
Ends:    23:30

You may disconnect from SSH.
The DietPi server will continue enforcing
the session in the background.

Pause/stop/modification is disabled
until the session expires.
```

Then:

```text
$ exit
```

The user goes back to studying.

The server handles everything else.

---

# 57. FINAL SUCCESS CRITERIA

The project is considered successful only when:

1. Everything runs on the DietPi server.
2. SSH is the primary management interface.
3. No Windows control panel is required.
4. The service runs independently in the background.
5. Network-wide domain blocking works where the network architecture supports it.
6. The user can add and remove domains.
7. The user can start a temporary focus session.
8. The user can specify a duration.
9. The user can specify an absolute end timestamp.
10. The active session is locked.
11. Normal application commands cannot stop or modify the locked session.
12. The locked state persists across service restarts.
13. The locked state survives SSH disconnection.
14. The locked state survives normal server reboot.
15. The session automatically expires at the configured timestamp.
16. The previous policy state is restored appropriately.
17. IPv4 is handled correctly.
18. IPv6 is explicitly handled or reported.
19. DNS bypass mechanisms are documented.
20. HTTPS is never decrypted.
21. No unnecessary browsing surveillance is performed.
22. Network modifications have rollback mechanisms.
23. The application is lightweight enough for DietPi.
24. The system is documented thoroughly.
25. The implementation is tested on real devices.

---

# 58. YOUR FIRST TASK

Do NOT immediately start writing code.

First analyze the complete requirement and return:

### A. Recommended architecture

Explain exactly how DietPi will enforce the network-wide policy.

### B. Network topology

Explain where DietPi sits relative to:

- router
- LAN
- Wi-Fi
- client devices

### C. Technology selection

Choose the programming language and supporting technologies and explain why.

### D. Enforcement mechanism

Explain precisely how blocked domains will be prevented from working.

### E. Locked-session architecture

Explain how the timestamp lock works and how it survives:

- SSH disconnect
- service restart
- reboot
- process failure

### F. Security model

Explain:

- privileges
- attack surface
- management access
- limitations

### G. IPv4/IPv6 strategy

Explain how both will be handled.

### H. DNS bypass strategy

Explain DoH/DoT and other common bypasses.

### I. Project structure

Provide the proposed directory structure.

### J. MVP implementation phases

Provide a practical build sequence.

Do not begin substantial implementation until the architecture has been reasoned through.

The final result must be a **real, lightweight, self-hosted DietPi network appliance for focused study**, not merely a website-blocking script.