from __future__ import annotations

from collections import defaultdict

from .models import AccessPoint, Concern, InternetStatus, NearbyNetwork, Snapshot, WirelessLink


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
) -> None:
    items.append(
        Concern(
            id=cid,
            severity=severity,  # type: ignore[arg-type]
            title=title,
            detail=detail,
            section=section,
            recommendation=recommendation,
        )
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
    open_nearby = 0
    wep_nearby = 0
    hidden = 0
    for net in nearby:
        if net.ssid:
            ssid_map[net.ssid].append(net)
        if net.channel:
            channel_map[(net.band, net.channel)] += 1
        if (net.security or "").lower() == "open":
            open_nearby += 1
        if (net.security or "").upper() == "WEP":
            wep_nearby += 1
        if net.hidden:
            hidden += 1

    if link.ssid and len({n.bssid for n in ssid_map.get(link.ssid, []) if n.bssid}) > 1:
        extras = [n for n in ssid_map[link.ssid] if n.bssid and n.bssid != link.bssid]
        if extras:
            _add(
                concerns,
                cid="evil-twin",
                severity="critical",
                title="Duplicate SSID detected",
                detail=(
                    f"SSID “{link.ssid}” is advertised by {len(extras) + 1} different BSSIDs. "
                    "This can be a mesh network, or an impersonating access point."
                ),
                section="nearby",
                recommendation="Confirm every BSSID belongs to your equipment. Rename the network if you see an unknown radio.",
            )

    own_key = (link.band, link.channel)
    if link.channel and channel_map.get(own_key, 0) >= 4:
        _add(
            concerns,
            cid="channel-congestion",
            severity="warning",
            title="Current channel is crowded",
            detail=f"{channel_map[own_key]} nearby networks are sharing {link.band} channel {link.channel}.",
            section="nearby",
            recommendation="In the router, pick a quieter channel or move clients to 5 GHz / 6 GHz.",
        )

    if open_nearby:
        _add(
            concerns,
            cid="open-nearby",
            severity="info",
            title=f"{open_nearby} open network{'s' if open_nearby != 1 else ''} nearby",
            detail="Unencrypted networks around the Pi increase the chance of accidental joins and local snooping.",
            section="nearby",
            recommendation="Keep the Pi locked to your SSID and avoid unknown open hotspots.",
        )

    if wep_nearby:
        _add(
            concerns,
            cid="wep-nearby",
            severity="info",
            title="Legacy WEP networks are visible",
            detail=f"{wep_nearby} nearby BSS still advertise WEP.",
            section="nearby",
            recommendation="This is informational unless one of those BSSIDs is yours.",
        )

    if hidden:
        _add(
            concerns,
            cid="hidden-ssids",
            severity="info",
            title=f"{hidden} hidden SSID{'s' if hidden != 1 else ''} in range",
            detail="Hidden networks still leak in probe traffic and are not a security control.",
            section="nearby",
            recommendation="Prefer a normal SSID with strong WPA2/WPA3 rather than hiding the name.",
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
        )

    return concerns


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
