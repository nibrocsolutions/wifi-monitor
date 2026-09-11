from __future__ import annotations

from collections import defaultdict

from .models import AccessPoint, Concern, ConcernLink, InternetStatus, NearbyNetwork, Snapshot, SocketFlow, WirelessLink


def health_level(score: int) -> str:
    if score >= 90:
        return "excellent"
    if score >= 75:
        return "good"
    if score >= 55:
        return "fair"
    if score >= 35:
        return "poor"
    return "critical"


def _add(
    items: list[Concern],
    *,
    cid: str,
    severity: str,
    title: str,
    detail: str,
    section: str,
    recommendation: str,
    links: list[ConcernLink] | None = None,
) -> None:
    items.append(
        Concern(
            id=cid,
            severity=severity,  # type: ignore[arg-type]
            title=title,
            detail=detail,
            section=section,
            recommendation=recommendation,
            links=links or [],
        )
    )


def _section_link(section: str, label: str) -> ConcernLink:
    path = "/" if section == "overview" else f"/{section}"
    return ConcernLink(label=label, href=path, kind="section", value=section)


def _nearby_link(net: NearbyNetwork) -> ConcernLink:
    bits: list[str] = []
    if net.channel:
        bits.append(f"ch {net.channel}")
    if net.band:
        bits.append(net.band)
    if net.signal_dbm is not None:
        bits.append(f"{net.signal_dbm:.0f} dBm")
    if net.vendor:
        bits.append(net.vendor)
    if net.security:
        bits.append(net.security)
    if net.is_associated:
        bits.append("associated")
    return ConcernLink(
        label=net.bssid or net.ssid or "unknown BSS",
        href=f"/nearby?focus={net.bssid or ''}",
        kind="bssid",
        value=net.bssid or "",
        meta=" · ".join(bits) or None,
    )


def _device_link(device) -> ConcernLink:
    focus = device.mac or device.ip or ""
    bits = [part for part in (device.ip, device.vendor, device.hostname) if part]
    return ConcernLink(
        label=device.hostname or device.ip or device.mac or "device",
        href=f"/devices?focus={focus}",
        kind="device",
        value=focus,
        meta=" · ".join(bits) or None,
    )


def _flow_link(flow: SocketFlow) -> ConcernLink:
    remote = f"{flow.remote_ip}:{flow.remote_port}" if flow.remote_ip else f"local:{flow.local_port}"
    service = flow.service or f"port {flow.remote_port or flow.local_port}"
    return ConcernLink(
        label=f"{flow.protocol.upper()} {remote}",
        href=f"/traffic?focus={flow.remote_ip or flow.local_ip or ''}",
        kind="flow",
        value=flow.remote_ip or flow.local_ip or "",
        meta=f"{service} · {flow.direction} · {flow.scope}",
    )


def analyze(snapshot: Snapshot) -> list[Concern]:
    concerns: list[Concern] = []
    link: WirelessLink = snapshot.link
    ap: AccessPoint = snapshot.access_point
    nearby: list[NearbyNetwork] = snapshot.nearby
    internet: InternetStatus = snapshot.internet

    if snapshot.demo:
        _add(
            concerns,
            cid="demo-mode",
            severity="info",
            title="Running in demonstration mode",
            detail="Live wireless hardware was not available, so the dashboard is showing a realistic sample network for preview.",
            section="system",
            recommendation="On a Raspberry Pi, run with host networking and privileged mode so WiFi Monitor can read the real radio.",
        )

    if not link.connected and not snapshot.demo:
        _add(
            concerns,
            cid="wifi-disconnected",
            severity="critical",
            title="Not associated with a Wi‑Fi network",
            detail="No active wireless association was detected on this host.",
                section="connection",
                recommendation="Confirm the Pi is joined to the intended SSID before relying on this monitor.",
                links=[_section_link("connection", "Open connection")],
        )

    if link.signal_dbm is not None:
        if link.signal_dbm <= -80:
            _add(
                concerns,
                cid="signal-critical",
                severity="critical",
                title="Wi‑Fi signal is very weak",
                detail=f"RSSI is {link.signal_dbm:.0f} dBm. Associations in this range drop packets and roam poorly.",
                section="connection",
                recommendation="Move the Pi closer to the access point, or add a mesh node / better antenna.",
                links=[_section_link("connection", "Open connection")],
            )
        elif link.signal_dbm <= -70:
            _add(
                concerns,
                cid="signal-weak",
                severity="warning",
                title="Wi‑Fi signal is weak",
                detail=f"RSSI is {link.signal_dbm:.0f} dBm. Throughput and latency may suffer.",
                section="connection",
                recommendation="Improve placement or switch to a less congested band if the AP supports it.",
                links=[_section_link("connection", "Open connection")],
            )

    security = (ap.security or link.security or "").upper()
    if link.connected and security:
        if security == "OPEN":
            _add(
                concerns,
                cid="open-own",
                severity="critical",
                title="Current network has no encryption",
                detail=f"SSID “{link.ssid or 'unknown'}” is open. Traffic can be observed by anyone nearby.",
                section="access-point",
                recommendation="Enable WPA2-PSK or WPA3 on the router and reconnect every device.",
                links=[_section_link("access-point", "Open access point")],
            )
        elif security == "WEP":
            _add(
                concerns,
                cid="wep-own",
                severity="critical",
                title="Current network uses broken WEP encryption",
                detail="WEP can be recovered quickly and should not be used on any production network.",
                section="access-point",
                recommendation="Replace WEP with WPA2-PSK (AES) or WPA3 immediately.",
                links=[_section_link("access-point", "Open access point")],
            )
        elif security == "WPA":
            _add(
                concerns,
                cid="wpa1-own",
                severity="warning",
                title="Current network uses legacy WPA",
                detail="WPA (TKIP) is deprecated and weaker than WPA2/WPA3.",
                section="access-point",
                recommendation="Set the router to WPA2-PSK (AES) or WPA3-Personal.",
                links=[_section_link("access-point", "Open access point")],
            )

    if link.power_save:
        _add(
            concerns,
            cid="power-save",
            severity="info",
            title="Wireless power save is enabled",
            detail="Power management can add latency for a always-on monitor.",
            section="connection",
            recommendation="Disable Wi‑Fi power save on the Pi if you need the most consistent latency.",
        )

    if link.tx_retries and link.tx_retries > 50:
        _add(
            concerns,
            cid="tx-retries",
            severity="warning",
            title="High wireless transmit retries",
            detail=f"{link.tx_retries} excessive TX retries were reported. This often means interference or a weak link.",
            section="connection",
            recommendation="Check channel congestion and physical placement of the Pi.",
        )

    if link.missed_beacons and link.missed_beacons > 10:
        _add(
            concerns,
            cid="missed-beacons",
            severity="warning",
            title="Missed access-point beacons",
            detail=f"{link.missed_beacons} missed beacons were counted. The radio may be drifting off the AP.",
            section="connection",
            recommendation="Reduce interference or move closer to the access point.",
        )

    ssid_map: dict[str, list[NearbyNetwork]] = defaultdict(list)
    channel_map: dict[tuple[str | None, int | None], int] = defaultdict(int)
    for net in nearby:
        if net.ssid:
            ssid_map[net.ssid].append(net)
        if net.channel:
            channel_map[(net.band, net.channel)] += 1

    if link.ssid and len({n.bssid for n in ssid_map.get(link.ssid, []) if n.bssid}) > 1:
        twins = sorted(
            [n for n in ssid_map[link.ssid] if n.bssid],
            key=lambda n: n.signal_dbm if n.signal_dbm is not None else -999,
            reverse=True,
        )
        if len(twins) > 1:
            _add(
                concerns,
                cid="evil-twin",
                severity="critical",
                title="Duplicate SSID detected",
                detail=(
                    f"SSID “{link.ssid}” is advertised by {len(twins)} different BSSIDs. "
                    "This can be a mesh network, or an impersonating access point."
                ),
                section="nearby",
                recommendation="Confirm every BSSID belongs to your equipment. Rename the network if you see an unknown radio.",
                links=[_section_link("nearby", "Open nearby networks")] + [_nearby_link(n) for n in twins],
            )

    own_key = (link.band, link.channel)
    if link.channel and channel_map.get(own_key, 0) >= 4:
        crowded = [n for n in nearby if n.band == link.band and n.channel == link.channel]
        _add(
            concerns,
            cid="channel-congestion",
            severity="warning",
            title="Current channel is crowded",
            detail=f"{channel_map[own_key]} nearby networks are sharing {link.band} channel {link.channel}.",
            section="nearby",
            recommendation="In the router, pick a quieter channel or move clients to 5 GHz / 6 GHz.",
            links=[_section_link("nearby", "Open nearby networks")] + [_nearby_link(n) for n in crowded[:12]],
        )

    open_nets = [n for n in nearby if (n.security or "").lower() == "open"]
    if open_nets:
        _add(
            concerns,
            cid="open-nearby",
            severity="info",
            title=f"{len(open_nets)} open network{'s' if len(open_nets) != 1 else ''} nearby",
            detail="Unencrypted networks around the Pi increase the chance of accidental joins and local snooping.",
            section="nearby",
            recommendation="Keep the Pi locked to your SSID and avoid unknown open hotspots.",
            links=[_section_link("nearby", "Open nearby networks")] + [_nearby_link(n) for n in open_nets],
        )

    wep_nets = [n for n in nearby if (n.security or "").upper() == "WEP"]
    if wep_nets:
        _add(
            concerns,
            cid="wep-nearby",
            severity="info",
            title="Legacy WEP networks are visible",
            detail=f"{len(wep_nets)} nearby BSS still advertise WEP.",
            section="nearby",
            recommendation="This is informational unless one of those BSSIDs is yours.",
            links=[_section_link("nearby", "Open nearby networks")] + [_nearby_link(n) for n in wep_nets],
        )

    hidden_nets = [n for n in nearby if n.hidden]
    if hidden_nets:
        _add(
            concerns,
            cid="hidden-ssids",
            severity="info",
            title=f"{len(hidden_nets)} hidden SSID{'s' if len(hidden_nets) != 1 else ''} in range",
            detail="Hidden networks still leak in probe traffic and are not a security control.",
            section="nearby",
            recommendation="Prefer a normal SSID with strong WPA2/WPA3 rather than hiding the name.",
            links=[_section_link("nearby", "Open nearby networks")] + [_nearby_link(n) for n in hidden_nets],
        )

    if link.band == "2.4 GHz" and link.connected:
        two_g = sum(1 for n in nearby if n.band == "2.4 GHz")
        if two_g >= 8:
            _add(
                concerns,
                cid="band-24-crowded",
                severity="info",
                title="2.4 GHz band is busy",
                detail=f"{two_g} networks were seen on 2.4 GHz, which has only three clean channels.",
                section="nearby",
                recommendation="Use 5 GHz for the Pi if the access point and distance allow it.",
            )

    new_devices = [d for d in snapshot.devices if d.new and not d.is_self]
    if new_devices:
        names = ", ".join(
            (d.hostname or d.vendor or d.ip or d.mac or "unknown") for d in new_devices[:4]
        )
        _add(
            concerns,
            cid="new-devices",
            severity="warning",
            title=f"{len(new_devices)} new device{'s' if len(new_devices) != 1 else ''} on the LAN",
            detail=f"First seen this session: {names}.",
            section="devices",
            recommendation="Confirm each new host is expected. Unknown phones, cameras, or IoT gear should be reviewed.",
            links=[_section_link("devices", "Open LAN devices")] + [_device_link(d) for d in new_devices],
        )

    if not internet.online:
        _add(
            concerns,
            cid="internet-down",
            severity="critical",
            title="Internet reachability failed",
            detail="Outbound probes did not receive replies. Local Wi‑Fi may still be up.",
            section="internet",
            recommendation="Check the gateway, WAN modem, and DNS before assuming the radio is at fault.",
            links=[_section_link("internet", "Open internet")],
        )
    elif internet.latency_ms is not None and internet.latency_ms >= 150:
        _add(
            concerns,
            cid="high-latency",
            severity="warning",
            title="WAN latency is elevated",
            detail=f"Average probe RTT is {internet.latency_ms:.0f} ms.",
            section="internet",
            recommendation="If this persists, inspect ISP path quality and 2.4 GHz interference.",
            links=[_section_link("internet", "Open internet")],
        )

    if internet.packet_loss_percent is not None and internet.packet_loss_percent >= 10:
        _add(
            concerns,
            cid="packet-loss",
            severity="warning",
            title="Packet loss on internet probes",
            detail=f"{internet.packet_loss_percent:.0f}% loss was measured to public targets.",
            section="internet",
            recommendation="Look at retries, signal, and the gateway before escalating to the ISP.",
            links=[_section_link("internet", "Open internet")],
        )

    if not internet.dns_ok:
        _add(
            concerns,
            cid="dns-failure",
            severity="critical" if internet.online else "warning",
            title="DNS resolution failed",
            detail="The monitor could not resolve a well-known hostname.",
            section="internet",
            recommendation="Verify DHCP DNS servers on the router, or set a known resolver such as 1.1.1.1.",
            links=[_section_link("internet", "Open internet")],
        )

    if internet.gateway_reachable is False:
        _add(
            concerns,
            cid="gateway-down",
            severity="critical",
            title="Default gateway is not responding",
            detail=f"No reply from {snapshot.gateway_ip or 'the gateway'}.",
            section="access-point",
            recommendation="Reboot or check the router if LAN clients cannot reach it either.",
            links=[_section_link("access-point", "Open access point")],
        )

    for iface in snapshot.interfaces:
        if iface.name in {"lo", "docker0"}:
            continue
        if iface.rx_errors + iface.tx_errors > 0:
            _add(
                concerns,
                cid=f"iface-errors-{iface.name}",
                severity="warning",
                title=f"Interface {iface.name} is counting errors",
                detail=f"RX errors {iface.rx_errors}, TX errors {iface.tx_errors}.",
                section="interfaces",
                recommendation="Check cabling for Ethernet, or wireless interference for Wi‑Fi adapters.",
                links=[ConcernLink(label=iface.name, href=f"/interfaces?focus={iface.name}", kind="interface", value=iface.name)],
            )
        if iface.rx_dropped + iface.tx_dropped > 100:
            _add(
                concerns,
                cid=f"iface-drops-{iface.name}",
                severity="info",
                title=f"Interface {iface.name} is dropping frames",
                detail=f"RX dropped {iface.rx_dropped}, TX dropped {iface.tx_dropped}.",
                section="interfaces",
                recommendation="Sustained drops can mean CPU pressure or a saturated link.",
                links=[ConcernLink(label=iface.name, href=f"/interfaces?focus={iface.name}", kind="interface", value=iface.name)],
            )

    if snapshot.system.temperature_c is not None and snapshot.system.temperature_c >= 80:
        _add(
            concerns,
            cid="pi-hot",
            severity="warning",
            title="Raspberry Pi is running hot",
            detail=f"SoC temperature is {snapshot.system.temperature_c:.1f} °C.",
            section="system",
            recommendation="Add airflow or a heatsink. Thermal throttling will slow scans and the UI.",
            links=[_section_link("system", "Open system")],
        )

    if snapshot.system.memory_percent is not None and snapshot.system.memory_percent >= 90:
        _add(
            concerns,
            cid="memory-pressure",
            severity="warning",
            title="Host memory is nearly full",
            detail=f"Memory use is {snapshot.system.memory_percent:.0f}%.",
            section="system",
            recommendation="Close other containers or add swap before the monitor is OOM-killed.",
            links=[_section_link("system", "Open system")],
        )

    _analyze_traffic(concerns, snapshot)
    return concerns


def _analyze_traffic(concerns: list[Concern], snapshot: Snapshot) -> None:
    live = snapshot.live_traffic
    if not live.flows and not live.listeners:
        return
    dns_servers = set(snapshot.internet.dns_servers or [])
    dns_flows = [
        f
        for f in live.flows
        if f.remote_port == 53 and f.remote_ip and f.remote_ip not in dns_servers and f.scope == "wan"
    ]
    if dns_flows:
        remotes = sorted({f.remote_ip for f in dns_flows if f.remote_ip})
        _add(
            concerns,
            cid="dns-bypass",
            severity="warning",
            title="DNS is leaving the configured resolvers",
            detail=(
                "This host has DNS flows to "
                + ", ".join(remotes)
                + ". That can be a device using hardcoded resolvers, or a sign to check DHCP DNS."
            ),
            section="traffic",
            recommendation="Compare these destinations with the DNS servers listed under Internet. If they are unexpected, check the Pi and any IoT gear for hardcoded resolvers.",
            links=[_section_link("traffic", "Open live traffic")] + [_flow_link(f) for f in dns_flows[:8]],
        )
    review_flows = [f for f in live.flows if f.unusual]
    if review_flows:
        _add(
            concerns,
            cid="unusual-ports",
            severity="warning",
            title=f"{len(review_flows)} flow{'s' if len(review_flows) != 1 else ''} on ports worth reviewing",
            detail="Cleartext admin, file-sharing, or rarely used remote-access ports are active. Confirm each one is a service you intended to run.",
            section="traffic",
            recommendation="Open each linked flow. If you do not recognize the remote host or the local listener, stop the service and check the LAN device that owns that IP.",
            links=[_section_link("traffic", "Open live traffic")] + [_flow_link(f) for f in review_flows[:12]],
        )
    new_wan = [f for f in live.flows if f.new and f.scope == "wan"]
    if len({f.remote_ip for f in new_wan}) >= 4:
        remotes = sorted({f.remote_ip for f in new_wan if f.remote_ip})
        _add(
            concerns,
            cid="new-wan-peers",
            severity="info",
            title=f"{len(remotes)} new WAN peers this session",
            detail="New public destinations appeared in the socket table. Normal browsing does this; a sudden burst without anyone using the network is worth a look.",
            section="traffic",
            recommendation="Sort live traffic by new WAN flows. Expected destinations are CDNs, NTP, and app backends. Unknown IPs should be matched to a LAN device that initiated them.",
            links=[_section_link("traffic", "Open live traffic")]
            + [
                ConcernLink(label=ip, href=f"/traffic?focus={ip}", kind="flow", value=ip)
                for ip in remotes[:10]
            ],
        )
    if live.syn_sent >= 8:
        syns = [f for f in live.flows if (f.state or "").upper() == "SYN_SENT"]
        _add(
            concerns,
            cid="syn-sent-burst",
            severity="warning",
            title="Many unfinished outbound connections",
            detail=f"{live.syn_sent} sockets are in SYN-SENT. That often means a destination is refusing or dropping the handshake.",
            section="traffic",
            recommendation="Check whether those remotes are still expected (failed updates, stale IoT clouds). A burst to many ports on one host can mean a misconfigured scanner on your own LAN.",
            links=[_section_link("traffic", "Open live traffic")] + [_flow_link(f) for f in syns[:8]],
        )
    if live.wan_remotes >= 40:
        _add(
            concerns,
            cid="wide-wan-fanout",
            severity="info",
            title="Unusually wide set of WAN destinations",
            detail=f"This host currently has sockets to {live.wan_remotes} distinct public addresses.",
            section="traffic",
            recommendation="Wide fan-out is common on a desktop. On a Raspberry Pi that only runs this monitor, it can mean another container or process is calling home.",
            links=[_section_link("traffic", "Open live traffic")],
        )
    noisy = [t for t in live.top_remotes if t.count >= 8]
    if noisy:
        _add(
            concerns,
            cid="chatty-peer",
            severity="info",
            title="A remote peer is holding many sockets",
            detail="Repeated connections to the same IP can be an app heartbeat, a mesh controller, or something looping. Confirm the owner.",
            section="traffic",
            recommendation="Open the linked remote. If it is not your router, a known cloud, or a CDN, identify which LAN device opened the sockets.",
            links=[_section_link("traffic", "Open live traffic")]
            + [
                ConcernLink(
                    label=f"{t.ip} ×{t.count}",
                    href=f"/traffic?focus={t.ip}",
                    kind="flow",
                    value=t.ip,
                    meta=t.service_hint,
                )
                for t in noisy[:6]
            ],
        )


def score_concerns(concerns: list[Concern]) -> int:
    score = 100
    for item in concerns:
        if item.id == "demo-mode":
            continue
        if item.severity == "critical":
            score -= 18
        elif item.severity == "warning":
            score -= 8
        else:
            score -= 2
    return max(0, min(100, score))


def summarize(snapshot: Snapshot) -> str:
    if snapshot.demo:
        return "Demonstration data is loaded so you can explore every section before deploying to a Pi."
    if not snapshot.link.connected:
        return "The host is not associated with a wireless network. Connect the Pi to Wi‑Fi and refresh."
    ssid = snapshot.link.ssid or "the local network"
    critical = sum(1 for c in snapshot.concerns if c.severity == "critical")
    warnings = sum(1 for c in snapshot.concerns if c.severity == "warning")
    if critical:
        return f"{ssid} has {critical} critical issue{'s' if critical != 1 else ''} that need attention."
    if warnings:
        return f"{ssid} is up, with {warnings} warning{'s' if warnings != 1 else ''} to review."
    return f"{ssid} looks healthy. Signal, LAN, and internet probes are within expected ranges."
