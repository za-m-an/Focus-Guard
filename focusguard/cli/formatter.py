"""Rich terminal formatting: Unicode box banners, status cards, live monitor, and stats."""

from __future__ import annotations

import sys
from typing import Any

# ANSI Colors & Styles
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"


def format_locked_banner(
    started_iso: str | None,
    ends_iso: str | None,
    remaining_str: str,
    domain_count: int,
) -> str:
    """Format the signature Locked Focus Session banner."""
    start_disp = started_iso[:19].replace("T", " ") if started_iso else "Unknown"
    ends_disp = ends_iso[:19].replace("T", " ") if ends_iso else "Unknown"

    lines = [
        f"{RED}╔═══════════════════════════════════════════════════════╗{RESET}",
        f"{RED}║               🔒 LOCKED FOCUS SESSION                 ║{RESET}",
        f"{RED}╠═══════════════════════════════════════════════════════╣{RESET}",
        f"{RED}║{RESET}  {BOLD}Status:{RESET}      {RED}{BOLD}LOCKED (Anti-Impulse Active){RESET}       {RED}║{RESET}",
        f"{RED}║{RESET}  {BOLD}Started:{RESET}     {WHITE}{start_disp:<38}{RESET}{RED}║{RESET}",
        f"{RED}║{RESET}  {BOLD}Ends:{RESET}        {YELLOW}{BOLD}{ends_disp:<38}{RESET}{RED}║{RESET}",
        f"{RED}║{RESET}  {BOLD}Remaining:{RESET}   {CYAN}{BOLD}{remaining_str:<38}{RESET}{RED}║{RESET}",
        f"{RED}║{RESET}  {BOLD}Domains:{RESET}     {GREEN}{domain_count:<38}{RESET}{RED}║{RESET}",
        f"{RED}╚═══════════════════════════════════════════════════════╝{RESET}",
        "",
        f"  {DIM}You may safely disconnect from SSH.{RESET}",
        f"  {DIM}The DietPi server will enforce this session in the background.{RESET}",
        f"  {RED}{BOLD}Pause / stop / edit is disabled until the session expires.{RESET}",
    ]
    return "\n".join(lines)


def format_status_card(status_dict: dict[str, Any]) -> str:
    """Format detailed status overview card."""
    session = status_dict.get("session", {})
    policy = status_dict.get("policy", {})
    dns = status_dict.get("dns", {})
    gateway = status_dict.get("gateway", {})

    is_locked = session.get("status") == "LOCKED"
    status_label = f"{RED}{BOLD}LOCKED{RESET}" if is_locked else f"{GREEN}IDLE{RESET}"

    lines = [
        f"{CYAN}{BOLD}FocusGuard Appliance Status{RESET}",
        f"{CYAN}{'─' * 46}{RESET}",
        f"  {BOLD}Service Daemon:{RESET}        {GREEN}● ACTIVE{RESET}",
        f"  {BOLD}Network DNS Filter:{RESET}    {GREEN}● RUNNING (Port {dns.get('port', 53)}){RESET}",
        f"  {BOLD}Policy Mode:{RESET}           {'Allowlist Only' if policy.get('allowlist_mode') else 'Blocklist Engine'}",
        f"  {BOLD}Session Status:{RESET}        {status_label}",
    ]

    if is_locked:
        started = session.get("created_at", "")[:19].replace("T", " ")
        expires = session.get("expires_at", "")[:19].replace("T", " ")
        remaining = session.get("remaining_formatted", "00:00:00")
        lines.extend([
            f"  {BOLD}Session Started:{RESET}       {started}",
            f"  {BOLD}Session Expires:{RESET}       {YELLOW}{BOLD}{expires}{RESET}",
            f"  {BOLD}Time Remaining:{RESET}        {CYAN}{BOLD}{remaining}{RESET}",
            f"  {BOLD}Session Domains:{RESET}       {session.get('domain_count', 0)} active",
        ])

    lines.extend([
        f"  {BOLD}Permanent Blocklist:{RESET}   {policy.get('permanent_count', 0)} domains",
        f"  {BOLD}Total Active Blocked:{RESET}  {BOLD}{policy.get('active_blocked_count', 0)}{RESET}",
        f"  {BOLD}DoH / DoT Guard:{RESET}       {'Active' if policy.get('block_doh') else 'Disabled'}",
    ])

    if gateway:
        gw_mode = gateway.get("mode", "STANDARD_DNS")
        gw_label = f"{GREEN}● ACTIVE (Transparent Redirection){RESET}" if gw_mode == "TRANSPARENT_GATEWAY" else f"{BLUE}STANDARD_DNS{RESET}"
        lines.append(f"  {BOLD}Gateway Enforcement:{RESET}  {gw_label}")

    lines.append(f"{CYAN}{'─' * 46}{RESET}")
    return "\n".join(lines)


def format_doctor_report(report: dict[str, Any]) -> str:
    """Format diagnostics check table."""
    summary = report.get("summary_status", "UNKNOWN")
    summary_color = GREEN if summary == "OPTIMAL" else YELLOW
    checks = report.get("checks", [])

    lines = [
        f"{BOLD}FocusGuard System & Network Diagnostics (Doctor){RESET}",
        f"{CYAN}{'═' * 62}{RESET}",
        f"Overall Health: {summary_color}{BOLD}{summary}{RESET}",
        "",
    ]

    for c in checks:
        st = c.get("status", "INFO")
        if st == "PASS":
            badge = f"{GREEN}[✓ PASS]{RESET}"
        elif st == "LOCKED":
            badge = f"{RED}[🔒 LOCKED]{RESET}"
        elif st == "WARN":
            badge = f"{YELLOW}[! WARN]{RESET}"
        elif st == "FAIL":
            badge = f"{RED}[✗ FAIL]{RESET}"
        else:
            badge = f"{BLUE}[i INFO]{RESET}"

        lines.append(f"  {badge} {BOLD}{c.get('name')}{RESET}")
        lines.append(f"         {c.get('details')}")
        if c.get("recommendation"):
            lines.append(f"         {YELLOW}→ Recommendation:{RESET} {c.get('recommendation')}")
        lines.append("")

    lines.append(f"{CYAN}{'═' * 62}{RESET}")
    return "\n".join(lines)


def format_monitor_header() -> str:
    """Renders the Live Network Monitor header."""
    return (
        f"\n{CYAN}{BOLD}FOCUSGUARD LIVE NETWORK MONITOR{RESET}\n"
        f"{CYAN}{'─' * 74}{RESET}\n"
        f"{BOLD}{'TIME':<10} {'DEVICE':<17} {'DESTINATION':<26} {'ACTION':<10} {'REASON'}{RESET}\n"
        f"{CYAN}{'─' * 74}{RESET}"
    )


def format_monitor_row(event: dict[str, Any]) -> str:
    """Renders a single flow event row."""
    ts = event.get("timestamp", "")
    time_str = ts[11:19] if len(ts) >= 19 else "00:00:00"
    device = event.get("client_ip", "")[:15]
    domain = event.get("domain", "")[:24]
    action = event.get("action", "ALLOWED")
    reason = event.get("reason", "")[:18]

    if action == "BLOCKED":
        action_fmt = f"{RED}{BOLD}BLOCKED{RESET}"
    else:
        action_fmt = f"{GREEN}ALLOWED{RESET}"

    return f"{DIM}{time_str:<10}{RESET} {device:<17} {domain:<26} {action_fmt:<19} {reason}"


def format_stats_card(stats: dict[str, Any], session_info: dict[str, Any] | None = None) -> str:
    """Renders traffic and blocking analytics."""
    total = stats.get("total_queries", 0)
    blocked = stats.get("blocked_queries", 0)
    allowed = stats.get("allowed_queries", 0)
    rate = stats.get("block_rate_percent", 0.0)
    devices = stats.get("unique_devices", 0)
    top_domains = stats.get("top_blocked_domains", [])
    device_breakdown = stats.get("device_breakdown", [])

    lines = [
        f"{CYAN}{BOLD}FocusGuard Traffic Analytics & Statistics{RESET}",
        f"{CYAN}{'═' * 52}{RESET}",
        f"  {BOLD}Total Queries:{RESET}      {total}",
        f"  {BOLD}Blocked Queries:{RESET}    {RED}{BOLD}{blocked}{RESET} ({rate}% block rate)",
        f"  {BOLD}Allowed Queries:{RESET}    {GREEN}{allowed}{RESET}",
        f"  {BOLD}Active Devices:{RESET}     {devices}",
        "",
        f"{BOLD}Top Blocked Domains:{RESET}",
        f"{'─' * 38}",
    ]

    if not top_domains:
        lines.append("  (No blocked queries recorded yet)")
    else:
        for item in top_domains:
            dom = item.get("domain", "")
            cnt = item.get("count", 0)
            lines.append(f"  • {dom:<26} {RED}{BOLD}{cnt:>6}{RESET}")

    lines.extend([
        "",
        f"{BOLD}Device Activity Breakdown:{RESET}",
        f"{'─' * 46}",
        f"  {'IP Address':<18} {'Total':<10} {'Blocked'}",
    ])

    if not device_breakdown:
        lines.append("  (No device traffic recorded yet)")
    else:
        for dev in device_breakdown:
            ip = dev.get("client_ip", "")
            t_q = dev.get("total_queries", 0)
            b_q = dev.get("blocked_queries", 0)
            lines.append(f"  {ip:<18} {t_q:<10} {RED}{b_q}{RESET}")

    lines.append(f"{CYAN}{'═' * 52}{RESET}")
    return "\n".join(lines)
