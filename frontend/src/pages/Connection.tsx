import { useSnapshot } from "../api";
import { dash, formatDbm } from "../format";
import { Badge, KeyValue, SignalBars } from "../components/Widgets";

export function ConnectionPage() {
  const { snapshot } = useSnapshot();
  if (!snapshot) return <div className="card empty">Collecting the first sample…</div>;
  const link = snapshot.link;
  return (
    <div className="grid two">
      <div className="card">
        <h3>Association</h3>
        <KeyValue
          items={[
            ["State", link.connected ? <Badge tone="ok">Connected</Badge> : <Badge tone="bad">Disconnected</Badge>],
            ["Interface", dash(link.interface)],
            ["SSID", dash(link.ssid)],
            ["BSSID", dash(link.bssid)],
            ["Mode", dash(link.mode)],
            ["Security", dash(link.security ?? snapshot.access_point.security)],
            ["Power save", link.power_save == null ? "—" : link.power_save ? "On" : "Off"],
          ]}
        />
      </div>
      <div className="card">
        <h3>Radio quality</h3>
        <KeyValue
          items={[
            [
              "Signal",
              <span style={{ display: "inline-flex", gap: 8, alignItems: "center" }}>
                {formatDbm(link.signal_dbm)} <SignalBars dbm={link.signal_dbm} />
              </span>,
            ],
            ["Noise", formatDbm(link.noise_dbm)],
            ["Quality", dash(link.link_quality ?? (link.link_quality_percent != null ? `${link.link_quality_percent}%` : null))],
            ["Band / channel", `${dash(link.band)} · ${dash(link.channel)}`],
            ["Frequency", link.frequency_mhz ? `${link.frequency_mhz} MHz` : "—"],
            ["TX rate", link.tx_bitrate_mbps != null ? `${link.tx_bitrate_mbps} Mbps` : "—"],
            ["RX rate", link.rx_bitrate_mbps != null ? `${link.rx_bitrate_mbps} Mbps` : "—"],
            ["TX power", link.tx_power_dbm != null ? `${link.tx_power_dbm} dBm` : "—"],
            ["Beacon interval", dash(link.beacon_interval)],
            ["DTIM", dash(link.dtim_period)],
            ["TX retries", dash(link.tx_retries)],
            ["Missed beacons", dash(link.missed_beacons)],
          ]}
        />
      </div>
    </div>
  );
}

export function AccessPointPage() {
  const { snapshot } = useSnapshot();
  if (!snapshot) return <div className="card empty">Collecting the first sample…</div>;
  const ap = snapshot.access_point;
  return (
    <div className="grid two">
      <div className="card">
        <h3>Serving BSS</h3>
        <KeyValue
          items={[
            ["SSID", dash(ap.ssid)],
            ["BSSID", dash(ap.bssid)],
            ["Vendor", dash(ap.vendor)],
            ["Band", dash(ap.band)],
            ["Channel", dash(ap.channel)],
            ["Frequency", ap.frequency_mhz ? `${ap.frequency_mhz} MHz` : "—"],
            ["Security", dash(ap.security)],
            ["Group cipher", dash(ap.group_cipher)],
            ["Pairwise", ap.pairwise_ciphers.join(", ") || "—"],
            ["Auth suites", ap.auth_suites.join(", ") || "—"],
            ["Hidden SSID", ap.hidden ? "Yes" : "No"],
          ]}
        />
      </div>
      <div className="card">
        <h3>Gateway & addressing</h3>
        <KeyValue
          items={[
            ["Gateway IP", dash(snapshot.gateway_ip)],
            ["This host", dash(snapshot.local_ip)],
            ["Subnet", dash(snapshot.subnet)],
            ["Default route", dash(snapshot.routes.find((r) => r.destination === "default")?.interface)],
            ["Gateway reachable", snapshot.internet.gateway_reachable == null ? "—" : snapshot.internet.gateway_reachable ? "Yes" : "No"],
          ]}
        />
      </div>
    </div>
  );
}
