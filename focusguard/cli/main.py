"""Main CLI entrypoint for FocusGuard."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from focusguard.cli.client import FocusGuardClient, DaemonError, ServiceNotRunningError
from focusguard.cli.formatter import (
    format_status_card,
    format_locked_banner,
    format_doctor_report,
    format_monitor_header,
    format_monitor_row,
    format_stats_card,
    BOLD,
    CYAN,
    GREEN,
    RED,
    YELLOW,
    RESET,
    DIM,
)
from focusguard.cli.interactive import run_interactive_menu
from focusguard.version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="focusguard",
        description="DietPi Network-Wide FocusGuard Distraction Blocker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--socket", help="Path to IPC Unix socket")
    parser.add_argument("-v", "--version", action="version", version=f"FocusGuard {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # status
    subparsers.add_parser("status", help="Display appliance and focus session status")

    # add
    add_parser = subparsers.add_parser("add", help="Add a domain to permanent blocklist")
    add_parser.add_argument("domain", help="Domain to block (e.g. youtube.com)")
    add_parser.add_argument("--no-companions", action="store_true", help="Do not include companion CDN/API domains")

    # remove
    rem_parser = subparsers.add_parser("remove", help="Remove a domain from permanent blocklist")
    rem_parser.add_argument("domain", help="Domain to remove")

    # list
    subparsers.add_parser("list", help="List configured and active blocked domains")

    # start
    start_parser = subparsers.add_parser("start", help="Start a locked focus session")
    start_parser.add_argument("-d", "--duration", help="Session duration (e.g. '4h', '45m', '1h30m')")
    start_parser.add_argument("-u", "--until", help="Session end time (e.g. '23:30' or '2026-09-10T23:30:00')")
    start_parser.add_argument("--domains", nargs="+", help="Specific domains for this session (default: permanent blocklist)")
    start_parser.add_argument("--no-companions", action="store_true", help="Do not include companion domains")

    # stop
    subparsers.add_parser("stop", help="Stop the active focus session (strictly rejected if locked)")

    # session
    subparsers.add_parser("session", help="Show active focus session countdown and domains")

    # doctor
    subparsers.add_parser("doctor", help="Run comprehensive network, DNS, and system diagnostics")

    # logs
    log_parser = subparsers.add_parser("logs", help="View recent audit and operational event logs")
    log_parser.add_argument("-n", "--limit", type=int, default=20, help="Number of entries to show (default: 20)")
    log_parser.add_argument("-c", "--category", help="Filter by category (session, policy, dns_block)")

    # monitor
    mon_parser = subparsers.add_parser("monitor", help="Stream live network flow events in real-time")
    mon_parser.add_argument("-b", "--blocked", action="store_true", help="Show only blocked queries")
    mon_parser.add_argument("--device", help="Filter events by client device IP")
    mon_parser.add_argument("--domain", help="Filter events by domain name substring")

    # stats
    stats_parser = subparsers.add_parser("stats", help="Display traffic analytics and blocking statistics")
    stats_parser.add_argument("-s", "--session", action="store_true", help="Scope statistics to the active focus session")

    # gateway
    gw_parser = subparsers.add_parser("gateway", help="Manage transparent network redirection and gateway mode")
    gw_parser.add_argument("action", choices=["status", "enable", "disable"], nargs="?", default="status", help="Gateway action (status, enable, disable)")

    # network
    subparsers.add_parser("network", help="Inspect network interfaces and router DNS setup guide")

    # menu
    subparsers.add_parser("menu", help="Launch interactive terminal menu")

    return parser


def cmd_monitor(client: FocusGuardClient, args: argparse.Namespace) -> None:
    """Run live network traffic monitor."""
    print(format_monitor_header())
    params = {
        "blocked_only": args.blocked,
        "device": args.device or "",
        "domain": args.domain or "",
    }

    try:
        for event in client.stream_monitor(params):
            print(format_monitor_row(event))
    except KeyboardInterrupt:
        print(f"\n{CYAN}Monitor closed.{RESET}\n")


def cmd_stats(client: FocusGuardClient, args: argparse.Namespace) -> None:
    """Print traffic analytics and top blocked domains."""
    stats = client.send_command("stats", {"session_scoped": args.session})
    print("\n" + format_stats_card(stats) + "\n")


def cmd_gateway(client: FocusGuardClient, args: argparse.Namespace) -> None:
    """Inspect or toggle transparent network gateway redirection."""
    action = args.action
    if action == "status":
        gw = client.send_command("gateway_status")
        mode = gw.get("mode", "STANDARD_DNS")
        fwd = gw.get("ip_forwarding", False)
        redir = gw.get("transparent_redirection", False)

        print(f"\n{CYAN}{BOLD}FocusGuard Network Gateway Status{RESET}")
        print(f"{CYAN}{'─' * 42}{RESET}")
        print(f"  {BOLD}Operating Mode:{RESET}             {GREEN if redir else BLUE}{mode}{RESET}")
        print(f"  {BOLD}Kernel IP Forwarding:{RESET}       {'Enabled' if fwd else 'Disabled'}")
        print(f"  {BOLD}Transparent Redirection:{RESET}   {GREEN + 'ACTIVE' if redir else YELLOW + 'INACTIVE'}{RESET}")
        print(f"  {BOLD}Local DNS Port:{RESET}             {gw.get('dns_port', 53)}")
        print(f"{CYAN}{'─' * 42}{RESET}\n")

    elif action == "enable":
        res = client.send_command("gateway_enable")
        print(f"{GREEN}✓ {res}{RESET}")

    elif action == "disable":
        res = client.send_command("gateway_disable")
        print(f"{GREEN}✓ {res}{RESET}")


def cmd_network(client: FocusGuardClient) -> None:
    """Print network routing and router DHCP configuration guide."""
    report = client.send_command("doctor")
    checks = {c["name"]: c for c in report.get("checks", [])}
    if_info = checks.get("Network Interfaces", {}).get("details", "Detecting...")

    print(f"\n{CYAN}{BOLD}FocusGuard Network Appliance Guide{RESET}")
    print(f"{CYAN}{'═' * 52}{RESET}")
    print(f"{BOLD}Local Interfaces:{RESET} {if_info}")
    print(f"{BOLD}DNS Port:{RESET}         53 (UDP/TCP dual-stack)")
    print("")
    print(f"{BOLD}How to enable network-wide blocking on your home router:{RESET}")
    print(" 1. Log in to your home router web interface (e.g., http://192.168.1.1).")
    print(" 2. Navigate to LAN / DHCP Server Settings.")
    print(" 3. Set Primary DNS Server to this DietPi server's IPv4 address.")
    print(" 4. Leave Secondary DNS Server EMPTY (or point it to this same DietPi IP).")
    print(f"    {YELLOW}{BOLD}WARNING:{RESET} If you configure 8.8.8.8 or 1.1.1.1 as secondary DNS,")
    print("    client devices will randomly bypass FocusGuard!")
    print(" 5. If IPv6 is active, configure DHCPv6 / RDNSS with DietPi's IPv6 address,")
    print("    or disable IPv6 on the router if you only use IPv4.")
    print(" 6. Save router settings and reconnect client devices (toggle Wi-Fi).")
    print(f"{CYAN}{'═' * 52}{RESET}\n")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    client = FocusGuardClient(socket_path=args.socket)

    # If no command provided or 'menu' command: launch interactive TUI
    if not args.command or args.command == "menu":
        try:
            run_interactive_menu(client)
        except KeyboardInterrupt:
            print("\nExiting FocusGuard.")
        return

    try:
        if args.command == "status":
            status = client.send_command("status")
            print(format_status_card(status))

        elif args.command == "add":
            res = client.send_command("add", {
                "domain": args.domain,
                "include_companions": not args.no_companions,
            })
            added = res.get("added", [])
            print(f"{GREEN}✓ Added to blocklist:{RESET} {', '.join(added)}")

        elif args.command == "remove":
            res = client.send_command("remove", {"domain": args.domain})
            print(f"{GREEN}✓ Removed from blocklist:{RESET} {res.get('removed')}")

        elif args.command == "list":
            res = client.send_command("list")
            perms = res.get("permanent_domains", [])
            sess = res.get("session_domains", [])
            print(f"\n{BOLD}Permanent Blocklist ({len(perms)}):{RESET}")
            for d in perms:
                print(f"  • {d}")
            if sess:
                print(f"\n{YELLOW}{BOLD}Active Session Blocklist ({len(sess)}):{RESET}")
                for d in sess:
                    print(f"  • {d}")
            print()

        elif args.command == "start":
            if not args.duration and not args.until:
                print(f"{YELLOW}Specify either --duration (e.g. -d 4h) or --until (e.g. -u 23:30).{RESET}")
                sys.exit(1)

            summary = client.send_command("start", {
                "duration": args.duration,
                "until": args.until,
                "domains": args.domains,
                "include_companions": not args.no_companions,
            })
            print("\n" + format_locked_banner(
                summary.get("created_at"),
                summary.get("expires_at"),
                summary.get("remaining_formatted", ""),
                summary.get("domain_count", 0),
            ) + "\n")

        elif args.command == "stop":
            res = client.send_command("stop")
            print(f"{GREEN}✓ {res}{RESET}")

        elif args.command == "session":
            summary = client.send_command("session")
            if summary.get("status") == "LOCKED":
                print("\n" + format_locked_banner(
                    summary.get("created_at"),
                    summary.get("expires_at"),
                    summary.get("remaining_formatted", ""),
                    summary.get("domain_count", 0),
                ) + "\n")
            else:
                print(f"{GREEN}● No active focus session (IDLE).{RESET}")

        elif args.command == "doctor":
            report = client.send_command("doctor")
            print("\n" + format_doctor_report(report))

        elif args.command == "logs":
            logs = client.send_command("logs", {"limit": args.limit, "category": args.category})
            print(f"\n{BOLD}Operational Logs (Latest {len(logs)}):{RESET}")
            for evt in logs:
                ts = evt.get("timestamp", "")[:19].replace("T", " ")
                cat = evt.get("category", "")
                act = evt.get("action", "")
                det = evt.get("details", "")
                print(f"  {DIM}{ts}{RESET} [{cat:<10}] {BOLD}{act:<22}{RESET} {det}")
            print()

        elif args.command == "monitor":
            cmd_monitor(client, args)

        elif args.command == "stats":
            cmd_stats(client, args)

        elif args.command == "gateway":
            cmd_gateway(client, args)

        elif args.command == "network":
            cmd_network(client)

    except DaemonError as e:
        print(f"\n{RED}{BOLD}ERROR:{RESET} {e}\n", file=sys.stderr)
        sys.exit(2)
    except ServiceNotRunningError as e:
        print(f"\n{RED}{BOLD}SERVICE NOT RUNNING:{RESET}\n{e}\n", file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        print(f"\n{RED}{BOLD}UNEXPECTED ERROR:{RESET} {e}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
