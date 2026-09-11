from __future__ import annotations

import ipaddress
import json
import os
import platform
import socket
import time
from datetime import datetime, timezone
from typing import Any

from . import parsers
from .demo import demo_snapshot
from .history import DeviceRegistry, HistoryStore
from .models import (
    AccessPoint,
    InternetStatus,
    LanDevice,
    NearbyNetwork,
    NetworkInterface,
    RouteInfo,
    Snapshot,
    SystemInfo,
    TrafficPoint,
    TrafficSample,
    WirelessLink,
)
from .util import freq_to_band, freq_to_channel, normalize_mac, read_text, run_cmd, which
from .vendors import vendor_from_mac

WIRELESS_HINTS = ("wlan", "wlp", "wlx", "wifi")


class Collector:
    def __init__(self, data_dir: str, demo: bool = False) -> None:
        self.data_dir = data_dir
        self.force_demo = demo
        self.history = HistoryStore()
        self.devices = DeviceRegistry(os.path.join(data_dir, "devices.json"))
        self._last_stats: dict[str, dict[str, int]] = {}
        self._last_stats_at: float | None = None
        self._cpu_sample: tuple[float, float] | None = None

    def capabilities(self) -> dict[str, bool]:
        return {
            "iw": which("iw") is not None,
            "iwconfig": which("iwconfig") is not None,
            "ip": which("ip") is not None,
            "ping": which("ping") is not None,
            "arp-scan": which("arp-scan") is not None,
            "nmap": which("nmap") is not None,
            "demo": self.force_demo,
        }

    def collect(self) -> Snapshot:
        generated = datetime.now(timezone.utc).isoformat()
        caps = self.capabilities()
        if self.force_demo:
            interfaces = self._interfaces()
            traffic = self._traffic(interfaces)
            system = self._system()
            point = TrafficPoint(
                ts=time.time(),
                rx_bps=sum(item.rx_bps for item in traffic if item.interface != "lo"),
                tx_bps=sum(item.tx_bps for item in traffic if item.interface != "lo"),
                signal_dbm=-49,
            )
            self.history.add(point)
            base = Snapshot(
                generated_at=generated,
                demo=True,
                interfaces=interfaces,
                traffic=traffic,
                history=self.history.snapshot(),
                system=system,
                capabilities=caps,
            )
            demo = demo_snapshot(base)
            demo.capabilities = caps
            demo.system = system.model_copy(
                update={"model": system.model or demo.system.model, "hostname": system.hostname}
            )
            return demo
        interfaces = self._interfaces()
        wireless_name = self._pick_wireless(interfaces)
        link = self._wireless_link(wireless_name)
        nearby = self._nearby(wireless_name, link)
        routes = self._routes()
        gateway_ip = next((r.gateway for r in routes if r.destination in {"default", "0.0.0.0/0"} and r.gateway), None)
        default_iface = next((r.interface for r in routes if r.destination in {"default", "0.0.0.0/0"}), None)
        for iface in interfaces:
            if default_iface and iface.name == default_iface:
                iface.is_default = True
            if wireless_name and iface.name == wireless_name:
                iface.is_wireless = True
        local_ip = self._local_ip(interfaces, default_iface or wireless_name)
        subnet = self._subnet(interfaces, default_iface or wireless_name)
        devices = self._devices(gateway_ip, local_ip, interfaces, subnet)
        devices = self.devices.observe(devices)
        internet = self._internet(gateway_ip)
        traffic = self._traffic(interfaces)
        system = self._system()
        associated = next((n for n in nearby if n.bssid and n.bssid == link.bssid), None)
        access_point = AccessPoint(
            ssid=link.ssid,
            bssid=link.bssid,
            vendor=vendor_from_mac(link.bssid),
            channel=link.channel,
            frequency_mhz=link.frequency_mhz,
            band=link.band,
            signal_dbm=link.signal_dbm,
            security=link.security or (associated.security if associated else None),
            pairwise_ciphers=associated.pairwise_ciphers if associated else [],
            group_cipher=associated.group_cipher if associated else None,
            auth_suites=associated.auth_suites if associated else [],
            hidden=not bool(link.ssid),
        )
        if associated:
            associated.is_associated = True
        point = TrafficPoint(
            ts=time.time(),
            rx_bps=sum(item.rx_bps for item in traffic if item.interface != "lo"),
            tx_bps=sum(item.tx_bps for item in traffic if item.interface != "lo"),
            signal_dbm=link.signal_dbm,
        )
        self.history.add(point)
        snapshot = Snapshot(
            generated_at=generated,
            demo=False,
            link=link,
            access_point=access_point,
            nearby=nearby,
            devices=devices,
            interfaces=interfaces,
            routes=routes,
            internet=internet,
            traffic=traffic,
            history=self.history.snapshot(),
            system=system,
            gateway_ip=gateway_ip,
            local_ip=local_ip,
            wireless_interface=wireless_name,
            subnet=subnet,
            capabilities=caps,
        )
        return snapshot

    def _pick_wireless(self, interfaces: list[NetworkInterface]) -> str | None:
        env = os.environ.get("WIFI_MONITOR_IFACE")
        if env:
            return env
        for iface in interfaces:
            if iface.is_wireless or any(iface.name.startswith(hint) for hint in WIRELESS_HINTS):
                return iface.name
        iw_devs = self._iw_interfaces()
        if iw_devs:
            return iw_devs[0]
        return None

    def _iw_interfaces(self) -> list[str]:
        if not which("iw"):
            return []
        code, out, _ = run_cmd(["iw", "dev"], timeout=4)
        if code != 0:
            return []
        return [item["name"] for item in parsers.parse_iw_dev(out) if item.get("name")]

    def _wireless_link(self, interface: str | None) -> WirelessLink:
        data: dict[str, Any] = {"interface": interface, "connected": False}
        if interface and which("iw"):
            code, out, _ = run_cmd(["iw", "dev", interface, "link"], timeout=4)
            if code == 0:
                data.update(parsers.parse_iw_link(out, interface))
        if interface and which("iwconfig"):
            code, out, _ = run_cmd(["iwconfig", interface], timeout=4)
            if code == 0:
                parsed = parsers.parse_iwconfig(out)
                for key, value in parsed.items():
                    if value is not None and data.get(key) in {None, False, ""}:
                        data[key] = value
        if data.get("frequency_mhz") and not data.get("channel"):
            data["channel"] = freq_to_channel(data["frequency_mhz"])
            data["band"] = freq_to_band(data["frequency_mhz"])
        return WirelessLink(**{k: v for k, v in data.items() if k in WirelessLink.model_fields})

    def _nearby(self, interface: str | None, link: WirelessLink) -> list[NearbyNetwork]:
        results: list[dict[str, Any]] = []
        if interface and which("iw"):
            code, out, _ = run_cmd(["iw", "dev", interface, "scan"], timeout=12)
            if code == 0 and "BSS " in out:
                results = parsers.parse_iw_scan(out)
        networks: list[NearbyNetwork] = []
        ssid_counts: dict[str, int] = {}
        for item in results:
            ssid = item.get("ssid")
            if ssid:
                ssid_counts[ssid] = ssid_counts.get(ssid, 0) + 1
        for item in results:
            vendor = vendor_from_mac(item.get("bssid"))
            is_dup = bool(item.get("ssid") and ssid_counts.get(item["ssid"], 0) > 1)
            networks.append(
                NearbyNetwork(
                    ssid=item.get("ssid"),
                    bssid=item.get("bssid"),
                    vendor=vendor,
                    channel=item.get("channel"),
                    frequency_mhz=item.get("frequency_mhz"),
                    band=item.get("band"),
                    signal_dbm=item.get("signal_dbm"),
                    security=item.get("security"),
                    pairwise_ciphers=item.get("pairwise_ciphers") or [],
                    group_cipher=item.get("group_cipher"),
                    auth_suites=item.get("auth_suites") or [],
                    hidden=bool(item.get("hidden")),
                    last_seen_s=item.get("last_seen_s"),
                    width_mhz=item.get("width_mhz"),
                    is_associated=bool(link.bssid and item.get("bssid") == link.bssid),
                    is_duplicate_ssid=is_dup,
                )
            )
        networks.sort(key=lambda n: n.signal_dbm if n.signal_dbm is not None else -999, reverse=True)
        return networks

    def _interfaces(self) -> list[NetworkInterface]:
        payload: list[dict[str, Any]] = []
        if which("ip"):
            code, out, _ = run_cmd(["ip", "-j", "addr"], timeout=4)
            if code == 0 and out.strip().startswith("["):
                try:
                    payload = json.loads(out)
                except json.JSONDecodeError:
                    payload = []
        parsed = parsers.parse_ip_addr(payload) if payload else []
        stats_text = read_text("/proc/net/dev") or ""
        stats = parsers.parse_proc_net_dev(stats_text) if stats_text else {}
        wireless_names = set(self._iw_interfaces())
        interfaces: list[NetworkInterface] = []
        for item in parsed:
            name = item.get("name")
            if not name:
                continue
            st = stats.get(name, {})
            wireless = name in wireless_names or any(name.startswith(h) for h in WIRELESS_HINTS)
            if os.path.exists(f"/sys/class/net/{name}/wireless"):
                wireless = True
            interfaces.append(
                NetworkInterface(
                    name=name,
                    mac=item.get("mac"),
                    state=item.get("state"),
                    mtu=item.get("mtu"),
                    ipv4=item.get("ipv4") or [],
                    ipv6=item.get("ipv6") or [],
                    rx_bytes=st.get("rx_bytes", 0),
                    tx_bytes=st.get("tx_bytes", 0),
                    rx_packets=st.get("rx_packets", 0),
                    tx_packets=st.get("tx_packets", 0),
                    rx_errors=st.get("rx_errors", 0),
                    tx_errors=st.get("tx_errors", 0),
                    rx_dropped=st.get("rx_dropped", 0),
                    tx_dropped=st.get("tx_dropped", 0),
                    is_wireless=wireless,
                )
            )
        return interfaces

    def _routes(self) -> list[RouteInfo]:
        if not which("ip"):
            return []
        code, out, _ = run_cmd(["ip", "-j", "route"], timeout=4)
        if code != 0 or not out.strip().startswith("["):
            return []
        try:
            payload = json.loads(out)
        except json.JSONDecodeError:
            return []
        return [RouteInfo(**item) for item in parsers.parse_ip_route(payload)]

    def _local_ip(self, interfaces: list[NetworkInterface], preferred: str | None) -> str | None:
        ordered = sorted(interfaces, key=lambda i: (i.name != preferred, i.name == "lo"))
        for iface in ordered:
            for addr in iface.ipv4:
                ip = addr.split("/")[0]
                if not ip.startswith("127."):
                    return ip
        return None

    def _subnet(self, interfaces: list[NetworkInterface], preferred: str | None) -> str | None:
        for iface in interfaces:
            if preferred and iface.name != preferred:
                continue
            for addr in iface.ipv4:
                try:
                    net = ipaddress.ip_interface(addr).network
                    if net.is_private:
                        return str(net)
                except ValueError:
                    continue
        for iface in interfaces:
            for addr in iface.ipv4:
                try:
                    net = ipaddress.ip_interface(addr).network
                    if net.is_private:
                        return str(net)
                except ValueError:
                    continue
        return None

    def _devices(
        self,
        gateway_ip: str | None,
        local_ip: str | None,
        interfaces: list[NetworkInterface],
        subnet: str | None,
    ) -> list[LanDevice]:
        found: dict[str, LanDevice] = {}

        def upsert(item: dict[str, Any]) -> None:
            ip = item.get("ip")
            mac = normalize_mac(item.get("mac"))
            key = (mac or ip or "").lower()
            if not key:
                return
            existing = found.get(key)
            hostname = item.get("hostname")
            vendor = item.get("vendor") or vendor_from_mac(mac)
            device = LanDevice(
                ip=ip or (existing.ip if existing else None),
                mac=mac or (existing.mac if existing else None),
                vendor=vendor or (existing.vendor if existing else None),
                hostname=hostname or (existing.hostname if existing else None),
                interface=item.get("interface") or (existing.interface if existing else None),
                state=item.get("state") or (existing.state if existing else None),
                is_gateway=bool(gateway_ip and ip == gateway_ip),
                is_self=bool(local_ip and ip == local_ip),
            )
            found[key] = device

        if which("ip"):
            code, out, _ = run_cmd(["ip", "-j", "neigh"], timeout=4)
            if code == 0 and out.strip().startswith("["):
                try:
                    for row in parsers.parse_ip_neigh(json.loads(out)):
                        upsert(row)
                except json.JSONDecodeError:
                    pass

        if which("arp-scan") and subnet:
            code, out, _ = run_cmd(
                ["arp-scan", "--localnet", "--plain", "--retry=1", "--timeout=200"],
                timeout=12,
            )
            if code == 0:
                for row in parsers.parse_arp_scan(out):
                    upsert(row)

        if which("nmap") and subnet and len(found) < 2:
            code, out, _ = run_cmd(
                [
                    "nmap",
                    "-sn",
                    "-n",
                    "--max-retries",
                    "1",
                    "--host-timeout",
                    "2s",
                    subnet,
                ],
                timeout=20,
            )
            if code == 0:
                for row in parsers.parse_nmap_ping_scan(out):
                    upsert(row)

        self_mac = None
        for iface in interfaces:
            if local_ip and any(addr.split("/")[0] == local_ip for addr in iface.ipv4):
                self_mac = iface.mac
                upsert(
                    {
                        "ip": local_ip,
                        "mac": iface.mac,
                        "hostname": socket.gethostname(),
                        "interface": iface.name,
                        "state": "self",
                        "vendor": vendor_from_mac(iface.mac),
                    }
                )
                break
        devices = list(found.values())
        for device in devices:
            if self_mac and device.mac == self_mac:
                device.is_self = True
            if gateway_ip and device.ip == gateway_ip:
                device.is_gateway = True
            if device.hostname is None and device.ip:
                device.hostname = self._reverse_dns(device.ip)
        devices.sort(key=lambda d: (not d.is_gateway, not d.is_self, d.ip or ""))
        return devices

    def _reverse_dns(self, ip: str) -> str | None:
        try:
            name, _, _ = socket.gethostbyaddr(ip)
            if name and name != ip:
                return name.rstrip(".")
        except OSError:
            return None
        return None

    def _internet(self, gateway_ip: str | None) -> InternetStatus:
        dns_servers = parsers.parse_resolv_conf(read_text("/etc/resolv.conf") or "")
        resolved: list[str] = []
        dns_ok = False
        try:
            for info in socket.getaddrinfo("example.com", 80, socket.AF_INET):
                ip = info[4][0]
                if ip not in resolved:
                    resolved.append(ip)
            dns_ok = bool(resolved)
        except OSError:
            dns_ok = False

        ping_targets = []
        losses = []
        rtts = []
        for host in ("1.1.1.1", "8.8.8.8"):
            result = self._ping(host)
            ping_targets.append({"host": host, **result})
            if result.get("packet_loss_percent") is not None:
                losses.append(result["packet_loss_percent"])
            if result.get("rtt_avg_ms") is not None:
                rtts.append(result["rtt_avg_ms"])
        gateway_reachable = None
        if gateway_ip:
            gw = self._ping(gateway_ip, count=2)
            gateway_reachable = bool(gw.get("received"))
        online = any(t.get("ok") for t in ping_targets)
        public_ip = self._public_ip() if online else None
        return InternetStatus(
            online=online,
            public_ip=public_ip,
            dns_ok=dns_ok,
            dns_servers=dns_servers,
            dns_resolved=resolved,
            ping_targets=ping_targets,
            latency_ms=sum(rtts) / len(rtts) if rtts else None,
            packet_loss_percent=sum(losses) / len(losses) if losses else None,
            gateway_reachable=gateway_reachable,
        )

    def _ping(self, host: str, count: int = 3) -> dict[str, Any]:
        if not which("ping"):
            return {"ok": False, "error": "ping not installed"}
        code, out, err = run_cmd(["ping", "-n", "-c", str(count), "-W", "2", host], timeout=count * 2 + 3)
        parsed = parsers.parse_ping(out or err)
        received = parsed.get("received") or 0
        parsed["ok"] = code == 0 and received > 0
        return parsed

    def _public_ip(self) -> str | None:
        import urllib.request

        urls = (
            "https://api.ipify.org",
            "https://ifconfig.me/ip",
        )
        for url in urls:
            try:
                with urllib.request.urlopen(url, timeout=4) as response:
                    text = response.read().decode("utf-8").strip()
                if text and " " not in text and len(text) < 48:
                    return text
            except OSError:
                continue
        return None

    def _traffic(self, interfaces: list[NetworkInterface]) -> list[TrafficSample]:
        now = time.time()
        samples: list[TrafficSample] = []
        elapsed = (now - self._last_stats_at) if self._last_stats_at else None
        for iface in interfaces:
            rx_bps = 0.0
            tx_bps = 0.0
            prev = self._last_stats.get(iface.name)
            if prev and elapsed and elapsed > 0:
                rx_bps = max(0.0, (iface.rx_bytes - prev.get("rx_bytes", 0)) * 8 / elapsed)
                tx_bps = max(0.0, (iface.tx_bytes - prev.get("tx_bytes", 0)) * 8 / elapsed)
            samples.append(
                TrafficSample(
                    interface=iface.name,
                    rx_bps=rx_bps,
                    tx_bps=tx_bps,
                    rx_bytes=iface.rx_bytes,
                    tx_bytes=iface.tx_bytes,
                    rx_errors=iface.rx_errors,
                    tx_errors=iface.tx_errors,
                )
            )
            self._last_stats[iface.name] = {"rx_bytes": iface.rx_bytes, "tx_bytes": iface.tx_bytes}
        self._last_stats_at = now
        return samples

    def _system(self) -> SystemInfo:
        load: list[float] = []
        try:
            load = [round(x, 2) for x in os.getloadavg()]
        except OSError:
            load = []
        mem_text = read_text("/proc/meminfo") or ""
        total_mb, used_mb = parsers.parse_meminfo(mem_text) if mem_text else (None, None)
        percent = None
        if total_mb and used_mb is not None and total_mb > 0:
            percent = round(used_mb / total_mb * 100.0, 1)
        uptime = None
        up_text = read_text("/proc/uptime")
        if up_text:
            try:
                uptime = float(up_text.split()[0])
            except ValueError:
                uptime = None
        model = read_text("/proc/device-tree/model")
        if model:
            model = model.replace("\x00", "").strip()
        os_release = read_text("/etc/os-release") or ""
        pretty = None
        for line in os_release.splitlines():
            if line.startswith("PRETTY_NAME="):
                pretty = line.split("=", 1)[1].strip().strip('"')
        temp = self._temperature()
        return SystemInfo(
            hostname=socket.gethostname(),
            os=pretty or platform.platform(),
            kernel=platform.release(),
            arch=platform.machine(),
            model=model,
            uptime_s=uptime,
            load_avg=load,
            cpu_percent=self._cpu_percent(),
            cpu_count=os.cpu_count(),
            memory_total_mb=round(total_mb, 1) if total_mb else None,
            memory_used_mb=round(used_mb, 1) if used_mb is not None else None,
            memory_percent=percent,
            temperature_c=temp,
            python=platform.python_version(),
            app_version="1.0.0",
        )

    def _temperature(self) -> float | None:
        candidates = [
            "/sys/class/thermal/thermal_zone0/temp",
            "/sys/class/hwmon/hwmon0/temp1_input",
        ]
        for path in candidates:
            text = read_text(path)
            if not text:
                continue
            try:
                value = float(text.strip())
            except ValueError:
                continue
            if value > 1000:
                value = value / 1000.0
            return round(value, 1)
        code, out, _ = run_cmd(["vcgencmd", "measure_temp"], timeout=2)
        if code == 0 and "temp=" in out:
            try:
                return float(out.split("=")[1].split("'")[0])
            except (IndexError, ValueError):
                return None
        return None

    def _cpu_percent(self) -> float | None:
        text = read_text("/proc/stat")
        if not text:
            return None
        parts = text.splitlines()[0].split()
        if len(parts) < 5:
            return None
        idle = float(parts[4])
        total = sum(float(x) for x in parts[1:])
        prev = self._cpu_sample
        self._cpu_sample = (idle, total)
        if not prev:
            return None
        idle_delta = idle - prev[0]
        total_delta = total - prev[1]
        if total_delta <= 0:
            return None
        return round(max(0.0, min(100.0, (1.0 - idle_delta / total_delta) * 100.0)), 1)
