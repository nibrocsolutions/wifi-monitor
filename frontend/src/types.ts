export type Severity = "critical" | "warning" | "info";
export type HealthLevel = "excellent" | "good" | "fair" | "poor" | "critical";

export interface Concern {
  id: string;
  severity: Severity;
  title: string;
  detail: string;
  section: string;
  recommendation: string;
}

export interface WirelessLink {
  interface: string | null;
  connected: boolean;
  ssid: string | null;
  bssid: string | null;
  frequency_mhz: number | null;
  channel: number | null;
  band: string | null;
  signal_dbm: number | null;
  noise_dbm: number | null;
  link_quality: string | null;
  link_quality_percent: number | null;
  tx_bitrate_mbps: number | null;
  rx_bitrate_mbps: number | null;
  tx_power_dbm: number | null;
  mode: string | null;
  security: string | null;
  power_save: boolean | null;
  tx_retries: number | null;
  invalid_misc: number | null;
  missed_beacons: number | null;
  rx_bytes: number | null;
  tx_bytes: number | null;
  beacon_interval: number | null;
  dtim_period: number | null;
}

export interface AccessPoint {
  ssid: string | null;
  bssid: string | null;
  vendor: string | null;
  channel: number | null;
  frequency_mhz: number | null;
  band: string | null;
  signal_dbm: number | null;
  security: string | null;
  pairwise_ciphers: string[];
  group_cipher: string | null;
  auth_suites: string[];
  hidden: boolean;
}

export interface NearbyNetwork extends AccessPoint {
  last_seen_s: number | null;
  width_mhz: number | null;
  is_associated: boolean;
  is_duplicate_ssid: boolean;
}

export interface LanDevice {
  ip: string | null;
  mac: string | null;
  vendor: string | null;
  hostname: string | null;
  interface: string | null;
  state: string | null;
  is_gateway: boolean;
  is_self: boolean;
  first_seen: string | null;
  last_seen: string | null;
  new: boolean;
}

export interface NetworkInterface {
  name: string;
  mac: string | null;
  state: string | null;
  mtu: number | null;
  ipv4: string[];
  ipv6: string[];
  rx_bytes: number;
  tx_bytes: number;
  rx_packets: number;
  tx_packets: number;
  rx_errors: number;
  tx_errors: number;
  rx_dropped: number;
  tx_dropped: number;
  is_wireless: boolean;
  is_default: boolean;
}

export interface RouteInfo {
  destination: string;
  gateway: string | null;
  interface: string | null;
  metric: number | null;
  protocol: string | null;
  source: string | null;
}

export interface PingTarget {
  host: string;
  ok?: boolean;
  rtt_avg_ms?: number | null;
  packet_loss_percent?: number | null;
  error?: string;
}

export interface InternetStatus {
  online: boolean;
  public_ip: string | null;
  dns_ok: boolean;
  dns_servers: string[];
  dns_resolved: string[];
  ping_targets: PingTarget[];
  latency_ms: number | null;
  packet_loss_percent: number | null;
  gateway_reachable: boolean | null;
}

export interface TrafficSample {
  interface: string;
  rx_bps: number;
  tx_bps: number;
  rx_bytes: number;
  tx_bytes: number;
  rx_errors: number;
  tx_errors: number;
}

export interface TrafficPoint {
  ts: number;
  rx_bps: number;
  tx_bps: number;
  signal_dbm: number | null;
}

export interface SystemInfo {
  hostname: string | null;
  os: string | null;
  kernel: string | null;
  arch: string | null;
  model: string | null;
  uptime_s: number | null;
  load_avg: number[];
  cpu_percent: number | null;
  cpu_count: number | null;
  memory_total_mb: number | null;
  memory_used_mb: number | null;
  memory_percent: number | null;
  temperature_c: number | null;
  python: string | null;
  app_version: string | null;
}

export interface Snapshot {
  generated_at: string;
  demo: boolean;
  health_score: number;
  health_level: HealthLevel;
  summary: string;
  concerns: Concern[];
  link: WirelessLink;
  access_point: AccessPoint;
  nearby: NearbyNetwork[];
  devices: LanDevice[];
  interfaces: NetworkInterface[];
  routes: RouteInfo[];
  internet: InternetStatus;
  traffic: TrafficSample[];
  history: TrafficPoint[];
  system: SystemInfo;
  gateway_ip: string | null;
  local_ip: string | null;
  wireless_interface: string | null;
  subnet: string | null;
  capabilities: Record<string, boolean>;
}
