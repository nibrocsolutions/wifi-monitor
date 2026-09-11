from app.concerns import analyze, score_concerns
from app.models import (
    AccessPoint,
    InternetStatus,
    LanDevice,
    NearbyNetwork,
    NetworkInterface,
    Snapshot,
    SystemInfo,
    WirelessLink,
)
from app.parsers import (
    parse_iw_link,
    parse_iw_scan,
    parse_iwconfig,
    parse_ping,
    parse_proc_net_dev,
    parse_proc_net_table,
    parse_resolv_conf,
    parse_ss,
)
from app.util import freq_to_band, freq_to_channel, normalize_mac, signal_quality_percent
from app.vendors import vendor_from_mac


IW_LINK = """
Connected to 78:8a:20:4c:21:a1 (on wlan0)
	SSID: Corbin-Home
	freq: 5180.0
	RX: 482331001 bytes (644201 packets)
	TX: 31822044 bytes (210334 packets)
	signal: -49 dBm
	rx bitrate: 866.7 MBit/s
	tx bitrate: 866.7 MBit/s
	bss flags: short-slot-time
	dtim period: 3
	beacon int: 100
"""

IWCONFIG = """
wlan0     IEEE 802.11  ESSID:"Corbin-Home"
          Mode:Managed  Frequency:5.18 GHz  Access Point: 78:8A:20:4C:21:A1
          Bit Rate=866.7 Mb/s   Tx-Power=31 dBm
          Retry short limit:7   RTS thr:off   Fragment thr:off
          Power Management:on
          Link Quality=61/70  Signal level=-49 dBm
          Rx invalid nwid:0  Rx invalid crypt:0  Rx invalid frag:0
          Tx excessive retries:12  Invalid misc:0   Missed beacon:0
"""

IW_SCAN = """
BSS 78:8a:20:4c:21:a1(on wlan0)
	freq: 5180
	signal: -49.00 dBm
	SSID: Corbin-Home
	RSN:	 * Version: 1
		 * Group cipher: CCMP
		 * Pairwise ciphers: CCMP
		 * Authentication suites: PSK SAE
BSS aa:bb:cc:dd:ee:ff(on wlan0)
	freq: 2437
	signal: -72.00 dBm
	SSID: xfinitywifi
	capability: ESS (0x0001)
BSS 11:22:33:44:55:66(on wlan0)
	freq: 2412
	signal: -88.00 dBm
	SSID: OldLinksys
	capability: ESS Privacy (0x0011)
"""


def test_normalize_mac():
    assert normalize_mac("78-8A-20-4C-21-A1") == "78:8a:20:4c:21:a1"
    assert normalize_mac("bad") is None


def test_freq_helpers():
    assert freq_to_channel(5180) == 36
    assert freq_to_band(5180) == "5 GHz"
    assert freq_to_channel(2437) == 6
    assert 80 < signal_quality_percent(-49) < 90


def test_parse_iw_link():
    data = parse_iw_link(IW_LINK, "wlan0")
    assert data["connected"] is True
    assert data["ssid"] == "Corbin-Home"
    assert data["bssid"] == "78:8a:20:4c:21:a1"
    assert data["channel"] == 36
    assert data["signal_dbm"] == -49
    assert data["tx_bitrate_mbps"] == 866.7


def test_parse_iwconfig():
    data = parse_iwconfig(IWCONFIG)
    assert data["ssid"] == "Corbin-Home"
    assert data["power_save"] is True
    assert data["tx_retries"] == 12
    assert data["link_quality"] == "61/70"


def test_parse_iw_scan_security():
    nets = parse_iw_scan(IW_SCAN)
    assert len(nets) == 3
    by_ssid = {n["ssid"]: n for n in nets}
    assert by_ssid["Corbin-Home"]["security"] == "WPA2/WPA3"
    assert by_ssid["xfinitywifi"]["security"] == "Open"
    assert by_ssid["OldLinksys"]["security"] == "WEP"


def test_parse_ping_and_resolv():
    ping = parse_ping(
        "3 packets transmitted, 3 received, 0% packet loss, time 2002ms\n"
        "rtt min/avg/max/mdev = 10.1/14.2/18.3/2.0 ms"
    )
    assert ping["packet_loss_percent"] == 0
    assert ping["rtt_avg_ms"] == 14.2
    assert parse_resolv_conf("nameserver 1.1.1.1\nnameserver 192.168.1.1\n") == [
        "1.1.1.1",
        "192.168.1.1",
    ]


def test_parse_proc_net_dev():
    text = (
        "Inter-|   Receive                                                |  Transmit\n"
        " face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed\n"
        "  eth0: 1000 1 2 3 0 0 0 0 2000 4 5 6 0 0 0 0\n"
    )
    stats = parse_proc_net_dev(text)
    assert stats["eth0"]["rx_bytes"] == 1000
    assert stats["eth0"]["tx_errors"] == 5


def test_parse_sockets():
    proc = (
        "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
        "   0: 1801A8C0:1F95 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 1\n"
        "   1: 1801A8C0:C000 0101A8C0:01BB 01 00000000:00000000 00:00000000 00000000     0        0 2\n"
    )
    rows = parse_proc_net_table(proc, "tcp")
    listen = rows[0]
    assert listen["state"] == "LISTEN"
    assert listen["local_ip"] == "192.168.1.24"
    assert listen["local_port"] == 8085
    est = rows[1]
    assert est["remote_ip"] == "192.168.1.1"
    assert est["remote_port"] == 443
    ss = parse_ss(
        "tcp   ESTAB 0 0 192.168.1.24:44190 1.1.1.1:443 users:((\"chrome\",pid=1,fd=3))\n"
        "udp   UNCONN 0 0 0.0.0.0:5353 0.0.0.0:*\n"
    )
    assert ss[0]["remote_ip"] == "1.1.1.1"
    assert ss[0]["process"] == "chrome"
    assert ss[1]["local_port"] == 5353


def test_vendor_lookup():
    assert vendor_from_mac("d8:3a:dd:00:00:01") == "Raspberry Pi"
    assert vendor_from_mac("d8:3a:dd:00:00:01") == "Raspberry Pi"


def _snap(**kwargs) -> Snapshot:
    data = dict(
        generated_at="2026-01-01T00:00:00+00:00",
        link=WirelessLink(connected=True, ssid="Home", bssid="aa:aa:aa:aa:aa:aa", signal_dbm=-50, security="WPA2-PSK", channel=36, band="5 GHz"),
        access_point=AccessPoint(ssid="Home", bssid="aa:aa:aa:aa:aa:aa", security="WPA2-PSK", channel=36, band="5 GHz"),
        internet=InternetStatus(online=True, dns_ok=True, latency_ms=20, packet_loss_percent=0, gateway_reachable=True),
        system=SystemInfo(temperature_c=42, memory_percent=30),
        interfaces=[
            NetworkInterface(name="wlan0", rx_errors=0, tx_errors=0, is_wireless=True),
        ],
    )
    data.update(kwargs)
    return Snapshot(**data)


def test_open_network_is_critical():
    snap = _snap(access_point=AccessPoint(ssid="Home", security="Open"), link=WirelessLink(connected=True, ssid="Home", security="Open", signal_dbm=-50))
    concerns = analyze(snap)
    assert any(c.id == "open-own" and c.severity == "critical" for c in concerns)


def test_evil_twin_and_weak_signal():
    snap = _snap(
        link=WirelessLink(connected=True, ssid="Home", bssid="aa:aa:aa:aa:aa:aa", signal_dbm=-82, channel=6, band="2.4 GHz", security="WPA2-PSK"),
        nearby=[
            NearbyNetwork(ssid="Home", bssid="aa:aa:aa:aa:aa:aa", channel=6, band="2.4 GHz", security="WPA2-PSK"),
            NearbyNetwork(ssid="Home", bssid="bb:bb:bb:bb:bb:bb", channel=11, band="2.4 GHz", security="WPA2-PSK"),
        ],
    )
    ids = {c.id for c in analyze(snap)}
    assert "evil-twin" in ids
    assert "signal-critical" in ids
    twin = next(c for c in analyze(snap) if c.id == "evil-twin")
    bssid_links = [link for link in twin.links if link.kind == "bssid"]
    assert {link.value for link in bssid_links} == {"aa:aa:aa:aa:aa:aa", "bb:bb:bb:bb:bb:bb"}


def test_duplicate_ssid_links_all_bssids():
    bssids = [f"aa:aa:aa:aa:aa:0{i}" for i in range(6)]
    snap = _snap(
        link=WirelessLink(connected=True, ssid="nibrocsolutions", bssid=bssids[0], signal_dbm=-50, security="WPA2-PSK"),
        nearby=[
            NearbyNetwork(ssid="nibrocsolutions", bssid=mac, channel=36, band="5 GHz", security="WPA2-PSK")
            for mac in bssids
        ],
    )
    twin = next(c for c in analyze(snap) if c.id == "evil-twin")
    assert "6 different BSSIDs" in twin.detail
    assert [link.value for link in twin.links if link.kind == "bssid"] == bssids


def test_demo_snapshot_has_chart_history():
    from datetime import datetime, timezone

    from app.demo import demo_snapshot
    from app.models import Snapshot, TrafficPoint

    sparse = Snapshot(
        generated_at=datetime.now(timezone.utc).isoformat(),
        history=[TrafficPoint(ts=1, rx_bps=0, tx_bps=0, signal_dbm=-50)],
    )
    demo = demo_snapshot(sparse)
    assert len(demo.history) >= 30
    assert demo.history[10].rx_bps > 0
    assert demo.link.ssid


def test_new_device_and_health_score():
    snap = _snap(devices=[LanDevice(ip="192.168.1.50", mac="11:22:33:44:55:66", new=True)])
    concerns = analyze(snap)
    assert any(c.id == "new-devices" for c in concerns)
    score = score_concerns(concerns)
    assert 0 <= score < 100
