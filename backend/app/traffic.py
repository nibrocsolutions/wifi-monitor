from __future__ import annotations

import time
from collections import Counter
from datetime import datetime, timezone

from .models import LiveTraffic, PortCount, RemoteTalker, SocketFlow
from .parsers import parse_proc_net_table, parse_ss
from .util import read_text, run_cmd, which

# Well-known ports used to label flows for an administrator reviewing their own LAN.
SERVICE_PORTS: dict[int, str] = {
    20: "ftp-data",
    21: "ftp",
    22: "ssh",
    23: "telnet",
    25: "smtp",
    53: "dns",
    67: "dhcp",
    68: "dhcp",
    80: "http",
    110: "pop3",
    123: "ntp",
    137: "netbios",
    138: "netbios",
    139: "smb",
    143: "imap",
    161: "snmp",
    389: "ldap",
    443: "https",
    445: "smb",
    465: "smtps",
    500: "ipsec",
    514: "syslog",
    587: "submission",
    631: "ipp",
    853: "dot",
    993: "imaps",
    995: "pop3s",
    1433: "mssql",
    1883: "mqtt",
    1900: "ssdp",
    3306: "mysql",
    3389: "rdp",
    4070: "spotify",
    5353: "mdns",
    5432: "postgres",
    5555: "adb",
    5900: "vnc",
    6379: "redis",
    8080: "http-alt",
    8085: "wifi-monitor",
    8443: "https-alt",
    8883: "mqtts",
}

# Ports that deserve a closer look on a home/office LAN (cleartext, remote-admin, or commonly abused).
REVIEW_PORTS = {21, 23, 137, 138, 139, 445, 1433, 3306, 3389, 5555, 5900, 6666, 6667, 12345, 31337}

LOOPBACK_PREFIXES = ("127.", "::1", "0.0.0.0", "::")


def _is_loopback(ip: str | None) -> bool:
    if not ip:
        return True
    return ip.startswith("127.") or ip in {"::1", "::", "0.0.0.0", "*"}


def _is_private(ip: str | None) -> bool:
    if not ip or _is_loopback(ip):
        return True
    if ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("169.254."):
        return True
    if ip.startswith("172."):
        try:
            second = int(ip.split(".")[1])
        except (IndexError, ValueError):
            return False
        return 16 <= second <= 31
    if ip.startswith("fd") or ip.startswith("fe80"):
        return True
    return False


def _scope(ip: str | None) -> str:
    if not ip or _is_loopback(ip):
        return "loopback"
    if _is_private(ip):
        return "lan"
    return "wan"


def _service(port: int | None) -> str | None:
    if port is None:
        return None
    return SERVICE_PORTS.get(port)


def _direction(state: str | None, remote_ip: str | None, remote_port: int | None, local_port: int | None) -> str:
    if (state or "").upper() == "LISTEN" or not remote_ip or remote_ip in {"0.0.0.0", "::", "*"}:
        return "listen"
    if remote_port and remote_port in SERVICE_PORTS and (not local_port or local_port > 1024):
        return "outbound"
    if local_port and local_port in SERVICE_PORTS:
        return "inbound"
    if local_port and local_port < 1024:
        return "inbound"
    return "outbound"


def _classify(raw: dict) -> SocketFlow:
    local_ip = raw.get("local_ip")
    remote_ip = raw.get("remote_ip")
    local_port = raw.get("local_port")
    remote_port = raw.get("remote_port")
    state = raw.get("state")
    direction = _direction(state, remote_ip, remote_port, local_port)
    service_port = remote_port if direction == "outbound" else local_port
    notes: list[str] = []
    unusual = False
    if service_port in REVIEW_PORTS:
        unusual = True
        notes.append(f"Port {service_port} ({_service(service_port) or 'unknown'}) is worth reviewing on a home LAN.")
    if direction == "listen" and local_port and local_port not in {22, 53, 67, 68, 80, 443, 5353, 8085} and local_port < 1024:
        unusual = True
        notes.append(f"Privileged listener on {local_port}.")
    scope = _scope(remote_ip if direction != "listen" else local_ip)
    return SocketFlow(
        protocol=raw.get("protocol") or "tcp",
        state=state,
        local_ip=local_ip,
        local_port=local_port,
        remote_ip=None if direction == "listen" else remote_ip,
        remote_port=None if direction == "listen" else remote_port,
        service=_service(service_port),
        direction=direction,
        scope=scope,
        recv_q=int(raw.get("recv_q") or 0),
        send_q=int(raw.get("send_q") or 0),
        process=raw.get("process"),
        unusual=unusual,
        notes=notes,
    )


def collect_live_traffic(seen_remotes: dict[str, float] | None = None) -> LiveTraffic:
    seen_remotes = seen_remotes if seen_remotes is not None else {}
    rows: list[dict] = []
    source = None
    if which("ss"):
        code, out, _ = run_cmd(["ss", "-H", "-tuanap"], timeout=4)
        if code == 0 and out.strip():
            rows = parse_ss(out)
            source = "ss"
    if not rows:
        tcp = read_text("/proc/net/tcp") or ""
        udp = read_text("/proc/net/udp") or ""
        rows = parse_proc_net_table(tcp, "tcp") + parse_proc_net_table(udp, "udp")
        source = "proc"
    flows = [_classify(row) for row in rows]
    now = time.time()
    for flow in flows:
        if flow.direction == "listen" or not flow.remote_ip or _is_loopback(flow.remote_ip):
            continue
        first = seen_remotes.get(flow.remote_ip)
        if first is None:
            seen_remotes[flow.remote_ip] = now
            flow.new = True
        elif now - first < 600:
            flow.new = True
    listeners = [f for f in flows if f.direction == "listen"]
    established = [f for f in flows if (f.state or "").upper() == "ESTABLISHED"]
    udp = [f for f in flows if f.protocol == "udp" and f.direction != "listen"]
    remotes = [f.remote_ip for f in flows if f.remote_ip and f.direction != "listen" and not _is_loopback(f.remote_ip)]
    unique = sorted(set(remotes))
    talker_map: dict[str, RemoteTalker] = {}
    for flow in flows:
        if not flow.remote_ip or flow.direction == "listen" or _is_loopback(flow.remote_ip):
            continue
        item = talker_map.setdefault(
            flow.remote_ip,
            RemoteTalker(ip=flow.remote_ip, scope=flow.scope, service_hint=flow.service),
        )
        item.count += 1
        if flow.remote_port and flow.remote_port not in item.ports:
            item.ports.append(flow.remote_port)
        if not item.service_hint and flow.service:
            item.service_hint = flow.service
    port_counter: Counter[tuple[str, int]] = Counter()
    for flow in flows:
        port = flow.remote_port if flow.direction == "outbound" else flow.local_port
        if port:
            port_counter[(flow.protocol, port)] += 1
    top_ports = [
        PortCount(protocol=proto, port=port, count=count, service=_service(port))
        for (proto, port), count in port_counter.most_common(12)
    ]
    active_flows = [
        f
        for f in flows
        if f.direction != "listen" and (f.protocol == "tcp" or (f.remote_ip and not _is_loopback(f.remote_ip)))
    ]
    active_flows.sort(key=lambda f: (not f.unusual, not f.new, f.scope != "wan", f.remote_ip or ""))
    return LiveTraffic(
        captured_at=datetime.now(timezone.utc).isoformat(),
        source=source,
        established=len(established),
        listen=len(listeners),
        udp=len(udp),
        syn_sent=sum(1 for f in flows if (f.state or "").upper() == "SYN_SENT"),
        unique_remotes=len(unique),
        wan_remotes=sum(1 for ip in unique if _scope(ip) == "wan"),
        lan_remotes=sum(1 for ip in unique if _scope(ip) == "lan"),
        flows=active_flows[:200],
        listeners=sorted(listeners, key=lambda f: (f.local_port or 0)),
        top_remotes=sorted(talker_map.values(), key=lambda t: t.count, reverse=True)[:15],
        top_ports=top_ports,
    )
