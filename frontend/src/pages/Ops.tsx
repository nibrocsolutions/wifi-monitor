import { Area, AreaChart, CartesianGrid, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useSnapshot } from "../api";
import { dash, formatBps, formatBytes } from "../format";
import { Badge, KeyValue } from "../components/Widgets";

export function TrafficPage() {
  const { snapshot } = useSnapshot();
  if (!snapshot) return <div className="card empty">Collecting the first sample…</div>;
  const chart = snapshot.history.map((p) => ({
    t: new Date(p.ts * 1000).toLocaleTimeString([], { minute: "2-digit", second: "2-digit" }),
    down: Math.round(p.rx_bps),
    up: Math.round(p.tx_bps),
    signal: p.signal_dbm,
  }));

  return (
    <>
      <div className="card">
        <h3>Throughput history</h3>
        <div className="chart">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chart}>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis dataKey="t" stroke="#617487" tick={{ fill: "#8ea3b5", fontSize: 11 }} />
              <YAxis stroke="#617487" tick={{ fill: "#8ea3b5", fontSize: 11 }} tickFormatter={(v) => formatBps(v)} />
              <Tooltip
                contentStyle={{ background: "#101824", border: "1px solid rgba(168,197,218,0.16)", borderRadius: 12 }}
                formatter={(value, name) =>
                  name === "signal" ? `${value} dBm` : formatBps(Number(value))
                }
              />
              <Area type="monotone" dataKey="down" name="Down" stroke="#3ee0a4" fill="#3ee0a4" fillOpacity={0.18} />
              <Area type="monotone" dataKey="up" name="Up" stroke="#6ea8ff" fill="#6ea8ff" fillOpacity={0.08} />
              <Line type="monotone" dataKey="signal" name="signal" stroke="#f0b429" dot={false} hide />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="card">
        <h3>Per-interface counters</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Interface</th>
                <th>Down</th>
                <th>Up</th>
                <th>RX bytes</th>
                <th>TX bytes</th>
                <th>Errors</th>
              </tr>
            </thead>
            <tbody>
              {snapshot.traffic.map((t) => (
                <tr key={t.interface}>
                  <td>{t.interface}</td>
                  <td>{formatBps(t.rx_bps)}</td>
                  <td>{formatBps(t.tx_bps)}</td>
                  <td className="mono">{formatBytes(t.rx_bytes)}</td>
                  <td className="mono">{formatBytes(t.tx_bytes)}</td>
                  <td>{t.rx_errors + t.tx_errors}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

export function InternetPage() {
  const { snapshot } = useSnapshot();
  if (!snapshot) return <div className="card empty">Collecting the first sample…</div>;
  const net = snapshot.internet;
  return (
    <div className="grid two">
      <div className="card">
        <h3>Reachability</h3>
        <KeyValue
          items={[
            ["Internet", net.online ? <Badge tone="ok">Online</Badge> : <Badge tone="bad">Offline</Badge>],
            ["Public IP", dash(net.public_ip)],
            ["DNS", net.dns_ok ? <Badge tone="ok">Resolving</Badge> : <Badge tone="bad">Failed</Badge>],
            ["DNS servers", net.dns_servers.join(", ") || "—"],
            ["Resolved example.com", net.dns_resolved.join(", ") || "—"],
            ["Average latency", net.latency_ms != null ? `${net.latency_ms.toFixed(1)} ms` : "—"],
            ["Probe loss", net.packet_loss_percent != null ? `${net.packet_loss_percent.toFixed(0)}%` : "—"],
            ["Gateway ping", net.gateway_reachable == null ? "—" : net.gateway_reachable ? "Reachable" : "No reply"],
          ]}
        />
      </div>
      <div className="card">
        <h3>Probe targets</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Host</th>
                <th>Status</th>
                <th>RTT</th>
                <th>Loss</th>
              </tr>
            </thead>
            <tbody>
              {net.ping_targets.map((t) => (
                <tr key={t.host}>
                  <td className="mono">{t.host}</td>
                  <td>{t.ok ? <Badge tone="ok">Up</Badge> : <Badge tone="bad">Down</Badge>}</td>
                  <td>{t.rtt_avg_ms != null ? `${t.rtt_avg_ms.toFixed(1)} ms` : "—"}</td>
                  <td>{t.packet_loss_percent != null ? `${t.packet_loss_percent}%` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export function InterfacesPage() {
  const { snapshot } = useSnapshot();
  if (!snapshot) return <div className="card empty">Collecting the first sample…</div>;
  return (
    <>
      {snapshot.interfaces.map((iface) => (
        <div className="card" key={iface.name}>
          <div className="toolbar">
            <h3 style={{ margin: 0 }}>{iface.name}</h3>
            <div className="row-tags">
              <Badge tone={iface.state === "up" ? "ok" : "muted"}>{iface.state ?? "unknown"}</Badge>
              {iface.is_wireless ? <Badge tone="info">Wireless</Badge> : null}
              {iface.is_default ? <Badge tone="ok">Default route</Badge> : null}
            </div>
          </div>
          <KeyValue
            items={[
              ["MAC", dash(iface.mac)],
              ["MTU", dash(iface.mtu)],
              ["IPv4", iface.ipv4.join(", ") || "—"],
              ["IPv6", iface.ipv6.join(", ") || "—"],
              ["RX / TX", `${formatBytes(iface.rx_bytes)} / ${formatBytes(iface.tx_bytes)}`],
              ["Packets", `${iface.rx_packets} / ${iface.tx_packets}`],
              ["Errors", `${iface.rx_errors} / ${iface.tx_errors}`],
              ["Dropped", `${iface.rx_dropped} / ${iface.tx_dropped}`],
            ]}
          />
        </div>
      ))}
      <div className="card">
        <h3>Routes</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Destination</th>
                <th>Gateway</th>
                <th>Interface</th>
                <th>Source</th>
                <th>Metric</th>
                <th>Protocol</th>
              </tr>
            </thead>
            <tbody>
              {snapshot.routes.map((r, idx) => (
                <tr key={`${r.destination}-${idx}`}>
                  <td className="mono">{r.destination}</td>
                  <td className="mono">{dash(r.gateway)}</td>
                  <td>{dash(r.interface)}</td>
                  <td className="mono">{dash(r.source)}</td>
                  <td>{dash(r.metric)}</td>
                  <td>{dash(r.protocol)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

export function SystemPage() {
  const { snapshot } = useSnapshot();
  if (!snapshot) return <div className="card empty">Collecting the first sample…</div>;
  const sys = snapshot.system;
  return (
    <div className="grid two">
      <div className="card">
        <h3>Host</h3>
        <KeyValue
          items={[
            ["Hostname", dash(sys.hostname)],
            ["Model", dash(sys.model)],
            ["OS", dash(sys.os)],
            ["Kernel", dash(sys.kernel)],
            ["Architecture", dash(sys.arch)],
            ["Uptime", sys.uptime_s != null ? `${Math.floor(sys.uptime_s / 3600)}h ${Math.floor((sys.uptime_s % 3600) / 60)}m` : "—"],
            ["App", dash(sys.app_version)],
            ["Python", dash(sys.python)],
          ]}
        />
      </div>
      <div className="card stack">
        <h3>Resources</h3>
        <div>
          <div className="k">CPU {sys.cpu_percent != null ? `${sys.cpu_percent}%` : "—"} · {sys.cpu_count ?? "?"} cores · load {sys.load_avg.join(" ") || "—"}</div>
          <div className="progress" style={{ marginTop: 8 }}>
            <span style={{ width: `${sys.cpu_percent ?? 0}%` }} />
          </div>
        </div>
        <div>
          <div className="k">
            Memory {sys.memory_percent != null ? `${sys.memory_percent}%` : "—"}
            {sys.memory_used_mb != null && sys.memory_total_mb != null
              ? ` · ${Math.round(sys.memory_used_mb)} / ${Math.round(sys.memory_total_mb)} MB`
              : ""}
          </div>
          <div className="progress" style={{ marginTop: 8 }}>
            <span style={{ width: `${sys.memory_percent ?? 0}%` }} />
          </div>
        </div>
        <KeyValue items={[["Temperature", sys.temperature_c != null ? `${sys.temperature_c.toFixed(1)} °C` : "—"]]} />
        <h3>Collector capabilities</h3>
        <div className="row-tags">
          {Object.entries(snapshot.capabilities).map(([k, v]) => (
            <Badge key={k} tone={v ? "ok" : "muted"}>
              {k}
            </Badge>
          ))}
        </div>
      </div>
    </div>
  );
}
