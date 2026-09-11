from __future__ import annotations

from datetime import datetime, timezone

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
from .vendors import vendor_from_mac


def demo_snapshot(base: Snapshot) -> Snapshot:
    """Fill wireless-centric sections with a realistic home network."""
    now = datetime.now(timezone.utc).isoformat()
    link = WirelessLink(
        interface="wlan0",
        connected=True,
        ssid="Corbin-Home",
        bssid="78:8a:20:4c:21:a1",
        frequency_mhz=5180,
        channel=36,
        band="5 GHz",
        signal_dbm=-49,
        noise_dbm=-92,
        link_quality="61/70",
        link_quality_percent=87.1,
        tx_bitrate_mbps=866.7,
        rx_bitrate_mbps=866.7,
        tx_power_dbm=31,
        mode="Managed",
        security="WPA2/WPA3",
        power_save=True,
        tx_retries=4,
        invalid_misc=0,
        missed_beacons=0,
        beacon_interval=100,
        dtim_period=3,
    )
    ap = AccessPoint(
        ssid=link.ssid,
        bssid=link.bssid,
        vendor=vendor_from_mac(link.bssid),
        channel=link.channel,
        frequency_mhz=link.frequency_mhz,
        band=link.band,
        signal_dbm=link.signal_dbm,
        security=link.security,
        pairwise_ciphers=["CCMP"],
        group_cipher="CCMP",
        auth_suites=["PSK", "SAE"],
        hidden=False,
    )
    nearby = [
        NearbyNetwork(
            **ap.model_dump(),
            is_associated=True,
            width_mhz=80,
        ),
        NearbyNetwork(
            ssid="Corbin-Home",
            bssid="78:8a:20:4c:21:a2",
            vendor="Ubiquiti",
            channel=149,
            frequency_mhz=5745,
            band="5 GHz",
            signal_dbm=-63,
            security="WPA2/WPA3",
            pairwise_ciphers=["CCMP"],
            group_cipher="CCMP",
            auth_suites=["PSK", "SAE"],
            is_duplicate_ssid=True,
            width_mhz=80,
        ),
        NearbyNetwork(
            ssid="xfinitywifi",
            bssid="7c:2e:bd:11:08:c4",
            vendor="Google",
            channel=6,
            frequency_mhz=2437,
            band="2.4 GHz",
            signal_dbm=-71,
            security="Open",
            hidden=False,
        ),
        NearbyNetwork(
            ssid="NETGEAR-Guest",
            bssid="20:4e:7f:90:12:44",
            vendor="Netgear",
            channel=11,
            frequency_mhz=2462,
            band="2.4 GHz",
            signal_dbm=-78,
            security="WPA2-PSK",
            pairwise_ciphers=["CCMP"],
            group_cipher="CCMP",
            auth_suites=["PSK"],
        ),
        NearbyNetwork(
            ssid=None,
            bssid="a0:63:91:22:10:0b",
            vendor="NETGEAR",
            channel=44,
            frequency_mhz=5220,
            band="5 GHz",
            signal_dbm=-82,
            security="WPA2-PSK",
            hidden=True,
        ),
        NearbyNetwork(
            ssid="OldLinksys",
            bssid="c8:3a:35:01:aa:10",
            vendor="Tenda",
            channel=1,
            frequency_mhz=2412,
            band="2.4 GHz",
            signal_dbm=-86,
            security="WEP",
        ),
        NearbyNetwork(
            ssid="Cafe-Free",
            bssid="50:c7:bf:77:02:19",
            vendor="TP-Link",
            channel=6,
            frequency_mhz=2437,
            band="2.4 GHz",
            signal_dbm=-88,
            security="Open",
        ),
    ]
    devices = [
        LanDevice(
            ip="192.168.1.1",
            mac="78:8a:20:4c:21:a1",
            vendor="Ubiquiti",
            hostname="udm-pro",
            interface="wlan0",
            state="REACHABLE",
            is_gateway=True,
        ),
        LanDevice(
            ip="192.168.1.24",
            mac="d8:3a:dd:5e:10:22",
            vendor="Raspberry Pi",
            hostname="wifi-monitor",
            interface="wlan0",
            state="REACHABLE",
            is_self=True,
        ),
        LanDevice(
            ip="192.168.1.18",
            mac="88:1f:a1:9c:44:10",
            vendor="Apple",
            hostname="roberts-macbook",
            interface="wlan0",
            state="REACHABLE",
        ),
        LanDevice(
            ip="192.168.1.32",
            mac="a4:83:e7:02:11:8c",
            vendor="Apple",
            hostname="iphone",
            interface="wlan0",
            state="STALE",
            new=True,
        ),
        LanDevice(
            ip="192.168.1.40",
            mac="ac:3a:7a:88:21:03",
            vendor="Roku",
            hostname="living-room-tv",
            interface="wlan0",
            state="REACHABLE",
        ),
        LanDevice(
            ip="192.168.1.55",
            mac="18:b4:30:6a:01:f2",
            vendor="Nest",
            hostname="thermostat",
            interface="wlan0",
            state="DELAY",
        ),
    ]
    if not base.interfaces:
        interfaces = [
            NetworkInterface(
                name="wlan0",
                mac="d8:3a:dd:5e:10:22",
                state="up",
                mtu=1500,
                ipv4=["192.168.1.24/24"],
                ipv6=["fe80::da3a:ddff:fe5e:1022/64"],
                rx_bytes=482331001,
                tx_bytes=31822044,
                rx_packets=644201,
                tx_packets=210334,
                is_wireless=True,
                is_default=True,
            ),
            NetworkInterface(
                name="eth0",
                mac="e4:5f:01:22:10:ab",
                state="down",
                mtu=1500,
                is_wireless=False,
            ),
            NetworkInterface(
                name="lo",
                mac="00:00:00:00:00:00",
                state="up",
                mtu=65536,
                ipv4=["127.0.0.1/8"],
                ipv6=["::1/128"],
            ),
        ]
    else:
        interfaces = base.interfaces

    routes = base.routes or [
        RouteInfo(
            destination="default",
            gateway="192.168.1.1",
            interface="wlan0",
            metric=600,
            protocol="dhcp",
            source="192.168.1.24",
        ),
        RouteInfo(
            destination="192.168.1.0/24",
            interface="wlan0",
            protocol="kernel",
            source="192.168.1.24",
        ),
    ]
    internet = InternetStatus(
        online=True,
        public_ip="73.184.12.40",
        dns_ok=True,
        dns_servers=["192.168.1.1", "1.1.1.1"],
        dns_resolved=["142.250.190.78"],
        ping_targets=[
            {
                "host": "1.1.1.1",
                "ok": True,
                "rtt_avg_ms": 14.2,
                "packet_loss_percent": 0,
            },
            {
                "host": "8.8.8.8",
                "ok": True,
                "rtt_avg_ms": 18.6,
                "packet_loss_percent": 0,
            },
        ],
        latency_ms=16.4,
        packet_loss_percent=0,
        gateway_reachable=True,
    )
    traffic = [
        TrafficSample(
            interface="wlan0",
            rx_bps=2_450_000,
            tx_bps=180_000,
            rx_bytes=482331001,
            tx_bytes=31822044,
        )
    ]
    history = list(base.history)
    if len(history) < 12:
        import math

        now_ts = datetime.now(timezone.utc).timestamp()
        history = [
            TrafficPoint(
                ts=now_ts - (59 - i) * 5,
                rx_bps=1_800_000 + math.sin(i / 6) * 600_000,
                tx_bps=120_000 + math.cos(i / 8) * 40_000,
                signal_dbm=-48 - abs(math.sin(i / 9)) * 4,
            )
            for i in range(60)
        ]
    system = base.system.model_copy(
        update={
            "hostname": base.system.hostname or "wifi-monitor",
            "model": base.system.model or "Raspberry Pi 5 Model B Rev 1.0",
            "app_version": base.system.app_version or "1.0.0",
        }
    )
    if system.model is None:
        system = SystemInfo(**{**system.model_dump(), "model": "Raspberry Pi 5 Model B Rev 1.0"})

    return Snapshot(
        generated_at=now,
        demo=True,
        link=link,
        access_point=ap,
        nearby=nearby,
        devices=devices,
        interfaces=interfaces,
        routes=routes,
        internet=internet,
        traffic=traffic,
        history=history,
        system=system,
        gateway_ip="192.168.1.1",
        local_ip="192.168.1.24",
        wireless_interface="wlan0",
        subnet="192.168.1.0/24",
        capabilities={**base.capabilities, "demo": True},
    )
