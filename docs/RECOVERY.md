# Emergency Recovery & Troubleshooting Guide

If something goes wrong with your home network or DietPi server, this guide explains how to restore connectivity immediately.

---

## 1. Quick Emergency Restore (Instant Network Recovery)

If your DietPi server is powered down or offline and client devices cannot browse the web:

### Method A: Router Fallback (Affects Whole Network)
1. Log in to your router web admin (e.g., `http://192.168.1.1` from any device connected to the network).
2. Go to **DHCP Settings**.
3. Change Primary DNS from the DietPi IP to a public resolver:
   - `1.1.1.1` (Cloudflare)
   - `8.8.8.8` (Google)
   - `9.9.9.9` (Quad9)
4. Save and reboot the router. All devices will immediately regain internet access.

### Method B: Single Device Temporary Override
If you need immediate access on a single computer without modifying the router:
- **Windows**: Settings -> Network & Internet -> Wi-Fi/Ethernet -> Edit DNS -> Set Manual DNS to `1.1.1.1`.
- **macOS**: System Settings -> Network -> Wi-Fi -> Details -> DNS -> Add `1.1.1.1`.
- **Android**: Settings -> Network -> Private DNS -> Set to `dns.google`.
- **iOS**: Settings -> Wi-Fi -> (i) icon -> Configure DNS -> Manual -> Add `1.1.1.1`.

---

## 2. Server-Side Diagnostics & Service Recovery

If you can SSH into DietPi (`ssh user@dietpi`):

### Check Service Status
```bash
focusguard doctor
```
or via systemd:
```bash
sudo systemctl status focusguard
```

### Restart Service
```bash
sudo systemctl restart focusguard
```

### View Live Service Logs
```bash
sudo journalctl -u focusguard -f
```

---

## 3. Safe State Reset

If the state file is corrupted or you need to wipe rules cleanly:

1. Stop the service:
   ```bash
   sudo systemctl stop focusguard
   ```
2. Reset state file to fresh default:
   ```bash
   sudo rm -f /var/lib/focusguard/state.json
   ```
3. Restart service:
   ```bash
   sudo systemctl start focusguard
   ```
   FocusGuard will regenerate a clean, unblocked default configuration.

---

## 4. Full Uninstallation
To completely remove FocusGuard from the DietPi server:
```bash
sudo /opt/focusguard/scripts/uninstall.sh
```
*(or run `sudo ./scripts/uninstall.sh` from the cloned repository).*
