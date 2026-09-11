from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Severity = Literal["critical", "warning", "info"]
HealthLevel = Literal["excellent", "good", "fair", "poor", "critical"]


class ConcernLink(BaseModel):
    label: str
    href: str
    kind: str = "item"
    value: str = ""
    meta: str | None = None


class Concern(BaseModel):
    id: str
    severity: Severity
    title: str
    detail: str
    section: str
    recommendation: str
    links: list[ConcernLink] = Field(default_factory=list)


class WirelessLink(BaseModel):
    interface: str | None = None
    connected: bool = False
    ssid: str | None = None
    bssid: str | None = None
    frequency_mhz: float | None = None
    channel: int | None = None
    band: str | None = None
    signal_dbm: float | None = None
    noise_dbm: float | None = None
    link_quality: str | None = None
    link_quality_percent: float | None = None
    tx_bitrate_mbps: float | None = None
    rx_bitrate_mbps: float | None = None
    tx_power_dbm: float | None = None
    mode: str | None = None
    security: str | None = None
    power_save: bool | None = None
    tx_retries: int | None = None
    invalid_misc: int | None = None
    missed_beacons: int | None = None
    rx_bytes: int | None = None
    tx_bytes: int | None = None
    beacon_interval: int | None = None
    dtim_period: int | None = None


class AccessPoint(BaseModel):
    ssid: str | None = None
    bssid: str | None = None
    vendor: str | None = None
    channel: int | None = None
    frequency_mhz: float | None = None
    band: str | None = None
    signal_dbm: float | None = None
    security: str | None = None
    pairwise_ciphers: list[str] = Field(default_factory=list)
    group_cipher: str | None = None
    auth_suites: list[str] = Field(default_factory=list)
    hidden: bool = False


class NearbyNetwork(AccessPoint):
    last_seen_s: float | None = None
    width_mhz: int | None = None
    is_associated: bool = False
    is_duplicate_ssid: bool = False


class LanDevice(BaseModel):
    ip: str | None = None
    mac: str | None = None
    vendor: str | None = None
    hostname: str | None = None
    interface: str | None = None
    state: str | None = None
    is_gateway: bool = False
    is_self: bool = False
    first_seen: str | None = None
    last_seen: str | None = None
    new: bool = False


class NetworkInterface(BaseModel):
    name: str
    mac: str | None = None
    state: str | None = None
    mtu: int | None = None
    ipv4: list[str] = Field(default_factory=list)
    ipv6: list[str] = Field(default_factory=list)
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_packets: int = 0
    tx_packets: int = 0
    rx_errors: int = 0
    tx_errors: int = 0
    rx_dropped: int = 0
    tx_dropped: int = 0
    is_wireless: bool = False
    is_default: bool = False


class RouteInfo(BaseModel):
    destination: str
    gateway: str | None = None
    interface: str | None = None
    metric: int | None = None
    protocol: str | None = None
    source: str | None = None


class InternetStatus(BaseModel):
    online: bool = False
    public_ip: str | None = None
    dns_ok: bool = False
    dns_servers: list[str] = Field(default_factory=list)
    dns_resolved: list[str] = Field(default_factory=list)
    ping_targets: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: float | None = None
    packet_loss_percent: float | None = None
    gateway_reachable: bool | None = None


class TrafficSample(BaseModel):
    interface: str
    rx_bps: float = 0
    tx_bps: float = 0
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_errors: int = 0
    tx_errors: int = 0


class TrafficPoint(BaseModel):
    ts: float
    rx_bps: float
    tx_bps: float
    signal_dbm: float | None = None


class SocketFlow(BaseModel):
    protocol: str
    state: str | None = None
    local_ip: str | None = None
    local_port: int | None = None
    remote_ip: str | None = None
    remote_port: int | None = None
    service: str | None = None
    direction: str = "unknown"
    scope: str = "unknown"
    recv_q: int = 0
    send_q: int = 0
    process: str | None = None
    new: bool = False
    unusual: bool = False
    notes: list[str] = Field(default_factory=list)


class RemoteTalker(BaseModel):
    ip: str
    count: int = 0
    ports: list[int] = Field(default_factory=list)
    scope: str = "unknown"
    service_hint: str | None = None


class PortCount(BaseModel):
    port: int
    protocol: str
    count: int
    service: str | None = None


class LiveTraffic(BaseModel):
    captured_at: str | None = None
    source: str | None = None
    established: int = 0
    listen: int = 0
    udp: int = 0
    syn_sent: int = 0
    unique_remotes: int = 0
    wan_remotes: int = 0
    lan_remotes: int = 0
    flows: list[SocketFlow] = Field(default_factory=list)
    listeners: list[SocketFlow] = Field(default_factory=list)
    top_remotes: list[RemoteTalker] = Field(default_factory=list)
    top_ports: list[PortCount] = Field(default_factory=list)


class SystemInfo(BaseModel):
    hostname: str | None = None
    os: str | None = None
    kernel: str | None = None
    arch: str | None = None
    model: str | None = None
    uptime_s: float | None = None
    load_avg: list[float] = Field(default_factory=list)
    cpu_percent: float | None = None
    cpu_count: int | None = None
    memory_total_mb: float | None = None
    memory_used_mb: float | None = None
    memory_percent: float | None = None
    temperature_c: float | None = None
    python: str | None = None
    app_version: str | None = None


class Snapshot(BaseModel):
    generated_at: str
    demo: bool = False
    health_score: int = 0
    health_level: HealthLevel = "poor"
    summary: str = ""
    concerns: list[Concern] = Field(default_factory=list)
    link: WirelessLink = Field(default_factory=WirelessLink)
    access_point: AccessPoint = Field(default_factory=AccessPoint)
    nearby: list[NearbyNetwork] = Field(default_factory=list)
    devices: list[LanDevice] = Field(default_factory=list)
    interfaces: list[NetworkInterface] = Field(default_factory=list)
    routes: list[RouteInfo] = Field(default_factory=list)
    internet: InternetStatus = Field(default_factory=InternetStatus)
    traffic: list[TrafficSample] = Field(default_factory=list)
    history: list[TrafficPoint] = Field(default_factory=list)
    live_traffic: LiveTraffic = Field(default_factory=LiveTraffic)
    system: SystemInfo = Field(default_factory=SystemInfo)
    gateway_ip: str | None = None
    local_ip: str | None = None
    wireless_interface: str | None = None
    subnet: str | None = None
    capabilities: dict[str, bool] = Field(default_factory=dict)
