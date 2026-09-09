"""Interactive terminal menu for FocusGuard."""

from __future__ import annotations

import sys
from focusguard.cli.client import FocusGuardClient, DaemonError, ServiceNotRunningError
from focusguard.cli.formatter import (
    format_status_card,
    format_locked_banner,
    format_doctor_report,
    BOLD,
    CYAN,
    GREEN,
    RED,
    YELLOW,
    RESET,
)


def run_interactive_menu(client: FocusGuardClient) -> None:
    """Run interactive menu loop."""
    while True:
        print("\n" + f"{CYAN}{BOLD}FocusGuard Appliance Console{RESET}")
        print(f"{CYAN}{'─' * 32}{RESET}")
        print("1. View Appliance Status")
        print("2. List Blocked Domains")
        print("3. Add Blocked Domain")
        print("4. Remove Blocked Domain")
        print("5. Start Locked Focus Session")
        print("6. View Active Session")
        print("7. Run Diagnostics (Doctor)")
        print("8. View Audit Logs")
        print("9. Exit")
        print(f"{CYAN}{'─' * 32}{RESET}")

        choice = input(f"{BOLD}Select an option [1-9]: {RESET}").strip()

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
                logs = client.send_command("logs", {"limit": 15})
                print(f"\n{BOLD}Recent Events (Newest First):{RESET}")
                for evt in logs:
                    ts = evt.get("timestamp", "")[:19].replace("T", " ")
                    cat = evt.get("category", "")
                    act = evt.get("action", "")
                    det = evt.get("details", "")
                    print(f"  {DIM}{ts}{RESET} [{cat}] {BOLD}{act}{RESET}: {det}")

            elif choice in ("9", "q", "exit"):
                print("Goodbye.")
                break

            else:
                print(f"{RED}Invalid selection. Please choose 1-9.{RESET}")

        except DaemonError as e:
            print(f"\n{RED}{BOLD}ERROR:{RESET} {e}\n")
        except ServiceNotRunningError as e:
            print(f"\n{RED}{BOLD}SERVICE ERROR:{RESET}\n{e}\n")
            break
