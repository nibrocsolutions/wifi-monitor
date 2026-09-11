from __future__ import annotations

import re
from typing import Any

from .util import freq_to_band, freq_to_channel, normalize_mac, parse_bitrate, signal_quality_percent


def parse_iw_dev(output: str) -> list[dict[str, str]]:
    devices: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    phy = None
    for raw in output.splitlines():
        line = raw.rstrip()
        phy_match = re.match(r"^phy#(\d+)", line)
        if phy_match:
            phy = phy_match.group(1)
            continue
        iface = re.match(r"^\s+Interface\s+(\S+)", line)
        if iface:
            current = {"name": iface.group(1), "phy": phy or ""}
            devices.append(current)
            continue
        if current is None:
            continue
        kv = re.match(r"^\s+(\w+)\s+(.+)$", line)
        if kv:
            current[kv.group(1)] = kv.group(2).strip()
    return devices


def parse_iw_link(output: str, interface: str) -> dict[str, Any]:
    data: dict[str, Any] = {
        "interface": interface,
        "connected": False,
        "ssid": None,
        "bssid": None,
        "frequency_mhz": None,
        "signal_dbm": None,
        "tx_bitrate_mbps": None,
        "rx_bitrate_mbps": None,
        "rx_bytes": None,
        "tx_bytes": None,
        "beacon_interval": None,
        "dtim_period": None,
    }
    if "Not connected" in output:
        return data
    connected = re.search(r"Connected to\s+([0-9a-fA-F:]{11,17})", output)
    if connected:
        data["connected"] = True
        data["bssid"] = normalize_mac(connected.group(1))
    ssid = re.search(r"^\s+SSID:\s+(.*)$", output, re.M)
    if ssid:
        data["ssid"] = ssid.group(1).strip() or None
    freq = re.search(r"^\s+freq:\s+([\d.]+)", output, re.M)
    if freq:
        data["frequency_mhz"] = float(freq.group(1))
        data["channel"] = freq_to_channel(data["frequency_mhz"])
        data["band"] = freq_to_band(data["frequency_mhz"])
    signal = re.search(r"^\s+signal:\s+(-?[\d.]+)", output, re.M)
    if signal:
        data["signal_dbm"] = float(signal.group(1))
        data["link_quality_percent"] = signal_quality_percent(data["signal_dbm"])
    rx_br = re.search(r"^\s+rx bitrate:\s+(.+)$", output, re.M)
    if rx_br:
        data["rx_bitrate_mbps"] = parse_bitrate(rx_br.group(1))
    tx_br = re.search(r"^\s+tx bitrate:\s+(.+)$", output, re.M)
    if tx_br:
        data["tx_bitrate_mbps"] = parse_bitrate(tx_br.group(1))
    rx = re.search(r"^\s+RX:\s+(\d+)\s+bytes", output, re.M)
    if rx:
        data["rx_bytes"] = int(rx.group(1))
    tx = re.search(r"^\s+TX:\s+(\d+)\s+bytes", output, re.M)
    if tx:
        data["tx_bytes"] = int(tx.group(1))
    beacon = re.search(r"^\s+beacon int:\s+(\d+)", output, re.M)
    if beacon:
        data["beacon_interval"] = int(beacon.group(1))
    dtim = re.search(r"^\s+dtim period:\s+(\d+)", output, re.M)
    if dtim:
        data["dtim_period"] = int(dtim.group(1))
    return data


def parse_iwconfig(output: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    iface = re.match(r"^(\S+)\s+", output)
    if iface:
        data["interface"] = iface.group(1)
    if re.search(r'ESSID:off/any', output):
        data["connected"] = False
    ssid = re.search(r'ESSID:"([^"]*)"', output)
    if ssid:
        data["ssid"] = ssid.group(1) or None
        data["connected"] = bool(data["ssid"])
    bssid = re.search(r"Access Point:\s+([0-9A-Fa-f:]{11,17}|Not-Associated)", output)
    if bssid and bssid.group(1) != "Not-Associated":
        data["bssid"] = normalize_mac(bssid.group(1))
        data["connected"] = True
    freq = re.search(r"Frequency:([\d.]+)\s*GHz", output)
    if freq:
        data["frequency_mhz"] = float(freq.group(1)) * 1000.0
        data["channel"] = freq_to_channel(data["frequency_mhz"])
        data["band"] = freq_to_band(data["frequency_mhz"])
    signal = re.search(r"Signal level=(-?\d+)\s*dBm", output)
    if signal:
        data["signal_dbm"] = float(signal.group(1))
        data["link_quality_percent"] = signal_quality_percent(data["signal_dbm"])
    quality = re.search(r"Link Quality=(\d+)/(\d+)", output)
    if quality:
        data["link_quality"] = f"{quality.group(1)}/{quality.group(2)}"
        data["link_quality_percent"] = round(
            int(quality.group(1)) / int(quality.group(2)) * 100.0, 1
        )
    bitrate = re.search(r"Bit Rate=([\d.]+)\s*Mb/s", output)
    if bitrate:
        data["tx_bitrate_mbps"] = float(bitrate.group(1))
    power = re.search(r"Tx-Power=(\d+)\s*dBm", output)
    if power:
        data["tx_power_dbm"] = float(power.group(1))
    mode = re.search(r"Mode:(\S+)", output)
    if mode:
        data["mode"] = mode.group(1)
    pm = re.search(r"Power Management:(\S+)", output)
    if pm:
        data["power_save"] = pm.group(1).lower() in {"on", "enabled"}
    retries = re.search(r"Tx excessive retries:(\d+)", output)
    if retries:
        data["tx_retries"] = int(retries.group(1))
    invalid = re.search(r"Invalid misc:(\d+)", output)
    if invalid:
        data["invalid_misc"] = int(invalid.group(1))
    missed = re.search(r"Missed beacon:(\d+)", output)
    if missed:
        data["missed_beacons"] = int(missed.group(1))
    return data


def _security_from_block(block: str) -> tuple[str, list[str], str | None, list[str]]:
    pairwise: list[str] = []
    auth: list[str] = []
    group = None
    rsn = "RSN:" in block or "RSN:" in block.replace("\t", "")
    wpa = bool(re.search(r"^\s+WPA:", block, re.M))
    privacy = bool(re.search(r"capability:.*Privacy", block))
    if re.search(r"Authentication suites:\s*(.+)", block):
        for match in re.finditer(r"Authentication suites:\s*(.+)", block):
            auth.extend(part.strip() for part in match.group(1).split() if part.strip())
    if re.search(r"Pairwise ciphers:\s*(.+)", block):
        for match in re.finditer(r"Pairwise ciphers:\s*(.+)", block):
            pairwise.extend(part.strip() for part in match.group(1).split() if part.strip())
    group_match = re.search(r"Group cipher:\s*(\S+)", block)
    if group_match:
        group = group_match.group(1)
    sae = any(a.upper() == "SAE" for a in auth)
    psk = any("PSK" in a.upper() for a in auth)
    if sae and psk:
        label = "WPA2/WPA3"
    elif sae:
        label = "WPA3"
    elif rsn and psk:
        label = "WPA2-PSK"
    elif wpa and not rsn:
        label = "WPA"
    elif privacy and not rsn and not wpa:
        label = "WEP"
    elif privacy:
        label = "Secured"
    else:
        label = "Open"
    return label, pairwise, group, auth


def parse_iw_scan(output: str) -> list[dict[str, Any]]:
    networks: list[dict[str, Any]] = []
    blocks = re.split(r"\nBSS ", output)
    for raw in blocks:
        if not raw.strip():
            continue
        block = raw if raw.startswith("BSS ") else "BSS " + raw
        bssid_match = re.search(r"BSS\s+([0-9a-fA-F:]{11,17})", block)
        if not bssid_match:
            continue
        ssid_match = re.search(r"^\s+SSID:\s+(.*)$", block, re.M)
        ssid = ssid_match.group(1).strip() if ssid_match else ""
        freq_match = re.search(r"^\s+freq:\s+([\d.]+)", block, re.M)
        freq = float(freq_match.group(1)) if freq_match else None
        signal_match = re.search(r"^\s+signal:\s+(-?[\d.]+)", block, re.M)
        last_seen = re.search(r"last seen:\s+([\d.]+)", block)
        width = re.search(r"\*\s+channel width:\s+(\d+)", block)
        security, pairwise, group, auth = _security_from_block(block)
        networks.append(
            {
                "bssid": normalize_mac(bssid_match.group(1)),
                "ssid": ssid or None,
                "hidden": not bool(ssid),
                "frequency_mhz": freq,
                "channel": freq_to_channel(freq),
                "band": freq_to_band(freq),
                "signal_dbm": float(signal_match.group(1)) if signal_match else None,
                "last_seen_s": float(last_seen.group(1)) if last_seen else None,
                "width_mhz": int(width.group(1)) if width else None,
                "security": security,
                "pairwise_ciphers": pairwise,
                "group_cipher": group,
                "auth_suites": auth,
            }
        )
    return networks


def parse_ip_addr(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    interfaces: list[dict[str, Any]] = []
    for item in payload:
        addrs4: list[str] = []
        addrs6: list[str] = []
        for addr in item.get("addr_info") or []:
            local = addr.get("local")
            prefix = addr.get("prefixlen")
            if not local:
                continue
            formatted = f"{local}/{prefix}" if prefix is not None else str(local)
            if addr.get("family") == "inet":
                addrs4.append(formatted)
            elif addr.get("family") == "inet6":
                addrs6.append(formatted)
        interfaces.append(
            {
                "name": item.get("ifname"),
                "mac": normalize_mac(item.get("address")),
                "state": (item.get("operstate") or "").lower() or None,
                "mtu": item.get("mtu"),
                "ipv4": addrs4,
                "ipv6": addrs6,
            }
        )
    return interfaces


def parse_ip_route(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    for item in payload:
        dest = item.get("dst") or "default"
        routes.append(
            {
                "destination": dest,
                "gateway": item.get("gateway"),
                "interface": item.get("dev"),
                "metric": item.get("metric"),
                "protocol": item.get("protocol"),
                "source": item.get("prefsrc"),
            }
        )
    return routes


def parse_ip_neigh(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    neighbors: list[dict[str, Any]] = []
    for item in payload:
        ip = item.get("dst")
        mac = normalize_mac(item.get("lladdr"))
        if not ip:
            continue
        neighbors.append(
            {
                "ip": ip,
                "mac": mac,
                "interface": item.get("dev"),
                "state": (item.get("state")[0] if item.get("state") else None),
            }
        )
    return neighbors


def parse_proc_net_dev(text: str) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {}
    for line in text.splitlines()[2:]:
        if ":" not in line:
            continue
        name, rest = line.split(":", 1)
        parts = rest.split()
        if len(parts) < 16:
            continue
        stats[name.strip()] = {
            "rx_bytes": int(parts[0]),
            "rx_packets": int(parts[1]),
            "rx_errors": int(parts[2]),
            "rx_dropped": int(parts[3]),
            "tx_bytes": int(parts[8]),
            "tx_packets": int(parts[9]),
            "tx_errors": int(parts[10]),
            "tx_dropped": int(parts[11]),
        }
    return stats


def parse_resolv_conf(text: str) -> list[str]:
    servers: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^\s*nameserver\s+(\S+)", line)
        if match:
            servers.append(match.group(1))
    return servers


def parse_ping(output: str) -> dict[str, Any]:
    loss = re.search(r"(\d+(?:\.\d+)?)% packet loss", output)
    rtt = re.search(r"rtt [^=]+= ([\d.]+)/([\d.]+)/([\d.]+)", output)
    transmitted = re.search(r"(\d+) packets transmitted", output)
    received = re.search(r"(\d+) received", output)
    return {
        "packet_loss_percent": float(loss.group(1)) if loss else None,
        "rtt_min_ms": float(rtt.group(1)) if rtt else None,
        "rtt_avg_ms": float(rtt.group(2)) if rtt else None,
        "rtt_max_ms": float(rtt.group(3)) if rtt else None,
        "transmitted": int(transmitted.group(1)) if transmitted else None,
        "received": int(received.group(1)) if received else None,
    }


def parse_arp_scan(output: str) -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    for line in output.splitlines():
        match = re.match(
            r"^(\d+\.\d+\.\d+\.\d+)\s+([0-9A-Fa-f:]{11,17})(?:\s+(.*))?$",
            line.strip(),
        )
        if not match:
            continue
        devices.append(
            {
                "ip": match.group(1),
                "mac": normalize_mac(match.group(2)),
                "vendor": (match.group(3) or "").strip() or None,
            }
        )
    return devices


def parse_nmap_ping_scan(output: str) -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    current_ip = None
    current_host = None
    for line in output.splitlines():
        report = re.match(r"Nmap scan report for (?:(\S+) \()?(\d+\.\d+\.\d+\.\d+)\)?", line)
        if report:
            current_host = report.group(1)
            current_ip = report.group(2)
            continue
        mac = re.search(r"MAC Address:\s+([0-9A-Fa-f:]{11,17})(?:\s+\((.+)\))?", line)
        if mac and current_ip:
            devices.append(
                {
                    "ip": current_ip,
                    "mac": normalize_mac(mac.group(1)),
                    "hostname": current_host,
                    "vendor": (mac.group(2) or "").strip() or None,
                }
            )
            current_ip = None
            current_host = None
        elif line.startswith("Host is up") and current_ip:
            devices.append(
                {
                    "ip": current_ip,
                    "mac": None,
                    "hostname": current_host,
                    "vendor": None,
                }
            )
            current_ip = None
            current_host = None
    return devices


def parse_meminfo(text: str) -> tuple[float | None, float | None]:
    total = re.search(r"MemTotal:\s+(\d+)", text)
    avail = re.search(r"MemAvailable:\s+(\d+)", text)
    if not total:
        return None, None
    total_mb = int(total.group(1)) / 1024.0
    used_mb = None
    if avail:
        used_mb = (int(total.group(1)) - int(avail.group(1))) / 1024.0
    return total_mb, used_mb
