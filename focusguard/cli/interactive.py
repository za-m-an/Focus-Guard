"""Interactive terminal menu for FocusGuard."""

from __future__ import annotations

import sys
from focusguard.cli.client import FocusGuardClient, DaemonError, ServiceNotRunningError
from focusguard.cli.formatter import (
    format_status_card,
    format_locked_banner,
    format_doctor_report,
    format_monitor_header,
    format_monitor_row,
    format_stats_card,
    format_bypass_status,
    format_devices_table,
    format_services_card,
    format_packet_stats,
    format_packet_stream_row,
    BOLD,
    CYAN,
    GREEN,
    RED,
    YELLOW,
    RESET,
    DIM,
)



def run_interactive_menu(client: FocusGuardClient) -> None:
    """Run interactive menu loop."""
    while True:
        print("\n" + f"{CYAN}{BOLD}FocusGuard Appliance Console{RESET}")
        print(f"{CYAN}{'─' * 38}{RESET}")
        print(" 1. View Appliance Status")
        print(" 2. List Blocked Domains")
        print(" 3. Add Blocked Domain")
        print(" 4. Remove Blocked Domain")
        print(" 5. Start Locked Focus Session")
        print(" 6. View Active Session")
        print(" 7. Run Diagnostics (Doctor)")
        print(" 8. Live Network Flow Monitor")
        print(" 9. Traffic Analytics & Statistics")
        print("10. Gateway & Transparent Redirection")
        print("11. Distraction Services (YouTube, IG, etc.)")
        print("12. Discovered Network Client Devices")
        print("13. VPN & Encrypted DNS Bypass Defense")
        print("14. Packet Monitor & Traffic Statistics")
        print("15. View Operational Audit Logs")
        print("16. Exit")
        print(f"{CYAN}{'─' * 38}{RESET}")

        choice = input(f"{BOLD}Select an option [1-16]: {RESET}").strip()


        try:
            if choice == "1":
                status = client.send_command("status")
                print("\n" + format_status_card(status))

            elif choice == "2":
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

            elif choice == "3":
                domain = input("Enter domain to block (e.g. youtube.com): ").strip()
                if domain:
                    res = client.send_command("add", {"domain": domain})
                    added = res.get("added", [])
                    print(f"{GREEN}✓ Added to blocklist:{RESET} {', '.join(added)}")

            elif choice == "4":
                domain = input("Enter domain to remove: ").strip()
                if domain:
                    res = client.send_command("remove", {"domain": domain})
                    print(f"{GREEN}✓ Removed from blocklist:{RESET} {res.get('removed')}")

            elif choice == "5":
                print("\nChoose focus session target:")
                print("1. Set Duration (e.g. 4h, 45m, 1h30m)")
                print("2. Set Absolute End Time (e.g. 23:30)")
                sub = input("Selection [1-2]: ").strip()

                duration = None
                until = None
                if sub == "1":
                    duration = input("Enter duration (e.g. 2h, 45m): ").strip()
                elif sub == "2":
                    until = input("Enter end time (e.g. 23:30): ").strip()
                else:
                    print("Invalid selection.")
                    continue

                custom_str = input("Custom domains (comma-separated, or leave blank to use permanent list): ").strip()
                custom_domains = [d.strip() for d in custom_str.split(",") if d.strip()] if custom_str else None

                summary = client.send_command(
                    "start",
                    {"duration": duration, "until": until, "domains": custom_domains},
                )
                print("\n" + format_locked_banner(
                    summary.get("created_at"),
                    summary.get("expires_at"),
                    summary.get("remaining_formatted", ""),
                    summary.get("domain_count", 0),
                ))

            elif choice == "6":
                summary = client.send_command("session")
                if summary.get("status") == "LOCKED":
                    print("\n" + format_locked_banner(
                        summary.get("created_at"),
                        summary.get("expires_at"),
                        summary.get("remaining_formatted", ""),
                        summary.get("domain_count", 0),
                    ))
                else:
                    print(f"\n{GREEN}● No active focus session (IDLE).{RESET}")

            elif choice == "7":
                print("\nRunning diagnostics...")
                report = client.send_command("doctor")
                print("\n" + format_doctor_report(report))

            elif choice == "8":
                print(format_monitor_header())
                print(f"{DIM}Streaming live network flows (Press Ctrl+C to exit)...{RESET}\n")
                try:
                    for event in client.stream_monitor({}):
                        print(format_monitor_row(event))
                except KeyboardInterrupt:
                    print(f"\n{CYAN}Monitor stopped.{RESET}")

            elif choice == "9":
                stats = client.send_command("stats")
                print("\n" + format_stats_card(stats))

            elif choice == "10":
                gw = client.send_command("gateway_status")
                mode = gw.get("mode", "STANDARD_DNS")
                fwd = gw.get("ip_forwarding", False)
                redir = gw.get("transparent_redirection", False)

                print(f"\n{CYAN}{BOLD}Gateway & Transparent Redirection{RESET}")
                print(f"{'─' * 38}")
                print(f"  Mode:           {GREEN if redir else BLUE}{mode}{RESET}")
                print(f"  IP Forwarding:  {'Enabled' if fwd else 'Disabled'}")
                print(f"  Redirection:    {GREEN + 'ACTIVE' if redir else YELLOW + 'INACTIVE'}{RESET}")
                print(f"{'─' * 38}")
                print("1. Enable Transparent Redirection (Redirect port 53)")
                print("2. Disable Transparent Redirection")
                print("3. Back to Main Menu")
                gw_choice = input("Select [1-3]: ").strip()
                if gw_choice == "1":
                    res = client.send_command("gateway_enable")
                    print(f"{GREEN}✓ {res}{RESET}")
                elif gw_choice == "2":
                    res = client.send_command("gateway_disable")
                    print(f"{GREEN}✓ {res}{RESET}")

            elif choice == "11":
                services = client.send_command("services_list")
                print(format_services_card(services))
                print("1. Block a service")
                print("2. Unblock a service")
                print("3. Return to main menu")
                s_opt = input("Select [1-3]: ").strip()
                if s_opt == "1":
                    s_name = input("Enter service identifier (e.g. youtube, instagram): ").strip()
                    if s_name:
                        res = client.send_command("service_block", {"service": s_name})
                        print(f"{GREEN}✓ Blocked service: {res.get('name')}{RESET}")
                elif s_opt == "2":
                    s_name = input("Enter service identifier to unblock: ").strip()
                    if s_name:
                        res = client.send_command("service_unblock", {"service": s_name})
                        print(f"{GREEN}✓ Unblocked service: {res}{RESET}")

            elif choice == "12":
                devices = client.send_command("devices_list")
                print(format_devices_table(devices))

            elif choice == "13":
                bypass = client.send_command("bypass_status")
                print("\n" + format_bypass_status(bypass) + "\n")

            elif choice == "14":
                print("\n1. View Packet Statistics Breakdown")
                print("2. Stream Live Packet Monitor")
                sub = input("Select [1-2]: ").strip()
                if sub == "1":
                    stats = client.send_command("packet_stats")
                    print(format_packet_stats(stats))
                elif sub == "2":
                    print(f"\n{CYAN}Streaming live packet metadata (Press Ctrl+C to stop)...{RESET}\n")
                    try:
                        for pkt in client.stream_packet_monitor():
                            print(format_packet_stream_row(pkt))
                    except KeyboardInterrupt:
                        print(f"\n{CYAN}Packet monitor stopped.{RESET}")

            elif choice == "15":
                logs = client.send_command("logs", {"limit": 15})
                print(f"\n{BOLD}Recent Events (Newest First):{RESET}")
                for evt in logs:
                    ts = evt.get("timestamp", "")[:19].replace("T", " ")
                    cat = evt.get("category", "")
                    act = evt.get("action", "")
                    det = evt.get("details", "")
                    print(f"  {DIM}{ts}{RESET} [{cat}] {BOLD}{act}{RESET}: {det}")

            elif choice in ("16", "q", "exit"):
                print("Goodbye.")
                break

            else:
                print(f"{RED}Invalid selection. Please choose 1-16.{RESET}")


        except DaemonError as e:
            print(f"\n{RED}{BOLD}ERROR:{RESET} {e}\n")
        except ServiceNotRunningError as e:
            print(f"\n{RED}{BOLD}SERVICE ERROR:{RESET}\n{e}\n")
            break
