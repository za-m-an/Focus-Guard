# Router Configuration Guide for Network-Wide Blocking

To enforce FocusGuard across every device on your home Wi-Fi and Ethernet (PCs, phones, tablets, smart TVs, consoles) without installing client software on every device, your home router's DHCP service must distribute the DietPi server's IP address as the Primary DNS server.

---

## 1. Prerequisites: Assign a Static IP to DietPi

Before configuring your router, ensure your DietPi server has a fixed IP address that will never change:

1. On your DietPi server, run:
   ```bash
   dietpi-config
   ```
2. Navigate to **7 : Network Options: Adapters** -> Select your interface (Ethernet `eth0` or Wi-Fi `wlan0`).
3. Select **Change Mode** -> Choose **STATIC**.
4. Note your DietPi IP address (e.g., `192.168.1.50`).

---

## 2. Router DHCP Configuration

### The Golden Rule of Secondary DNS
> **CRITICAL WARNING:** 
> In your router's DHCP settings, **LEAVE THE SECONDARY DNS FIELD EMPTY** (or enter the same DietPi IP address again).
> If you enter `8.8.8.8` or `1.1.1.1` as secondary DNS, client devices (especially iOS and Android) will query both servers concurrently or randomly fall back, completely bypassing your FocusGuard blocks!

---

### Step-by-Step for Major Router Brands

#### ASUS Routers (Asuswrt / Merlin)
1. Open your browser and go to `http://192.168.1.1` (or your router IP).
2. Go to **LAN** in the left sidebar -> click the **DHCP Server** tab.
3. Under **DNS and WINS Server Setting**:
   - **DNS Server 1**: Enter your DietPi IP (`192.168.1.50`).
   - **DNS Server 2**: Leave **BLANK**.
   - **Advertise router's IP in addition to user-specified DNS**: Set to **No**.
4. Click **Apply**.

#### TP-Link Routers
1. Log in to `http://192.168.0.1` or `http://tplinkwifi.net`.
2. Go to **Advanced** -> **Network** -> **DHCP Server**.
3. Under DHCP Settings:
   - **Primary DNS**: Enter your DietPi IP (`192.168.1.50`).
   - **Secondary DNS**: Enter `0.0.0.0` or leave **BLANK**.
4. Click **Save**.

#### Netgear Routers
1. Log in to `http://192.168.1.1` or `http://routerlogin.net`.
2. Go to **Advanced** -> **Setup** -> **LAN Setup**.
3. Under **LAN TCP/IP Setup**, set Primary DNS to DietPi IP.
4. Click **Apply**.

#### OpenWrt
1. Log in to LuCI at `http://192.168.1.1`.
2. Go to **Network** -> **Interfaces** -> click **Edit** on **LAN**.
3. Click **DHCP Server** tab -> **Advanced Settings**.
4. Under **DHCP-Options**, add: `6,192.168.1.50` (Option 6 informs DHCP clients of the DNS server).
5. Click **Save & Apply**.

---

## 3. IPv6 Configuration (Preventing IPv6 Bypasses)

If your ISP provides IPv6, devices might query external IPv6 DNS servers provided by your router's Router Advertisement (RDNSS):

- **Option A (Recommended if IPv6 is enabled)**: In your router's IPv6 LAN settings, set the DNSv6 server to your DietPi's IPv6 address (run `focusguard network` to find it).
- **Option B (Simplest)**: If you do not require IPv6 inside your local home network, disable IPv6 in your router settings. All traffic will use IPv4 and be 100% covered by FocusGuard.

---

## 4. Browser Encrypted DNS (DoH) Mitigations

Modern browsers (Chrome, Firefox, Edge, Brave) sometimes enable "Secure DNS" by default:

1. **In Google Chrome / Edge**: Go to `chrome://settings/security` -> Under **Use secure DNS**, select **"With your current service provider"** (or toggle Off).
2. **In Firefox**: Go to `about:preferences#privacy` -> Scroll to **DNS over HTTPS** -> Choose **Off** or **Default Protection**.
3. **On Android Devices**: Go to **Settings** -> **Network & Internet** -> **Private DNS** -> Set to **Off** (or Automatic).

---

## 5. Verification: How to Test

After updating your router:
1. Disconnect and reconnect your computer or phone from Wi-Fi (to renew DHCP lease).
2. On your computer terminal, test normal resolution:
   ```bash
   nslookup wikipedia.org
   ```
   *Verify that the Server IP listed is your DietPi server.*
3. On DietPi, add a test domain:
   ```bash
   focusguard add example.com
   focusguard start --duration 15m
   ```
4. On your laptop or phone, try visiting `http://example.com`. The connection should immediately fail.
