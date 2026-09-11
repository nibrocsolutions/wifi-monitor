import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useSnapshot } from "../api";
import { dash, formatBps, formatBytes } from "../format";
import { Badge } from "../components/Widgets";
import { ConcernRow } from "../components/ConcernRow";
import type { SocketFlow } from "../types";

const PLAYBOOK = [
  {
    title: "1. Inventory first",
    body: "Start on LAN devices and Nearby networks. You cannot judge a flow until you know which radios and hosts belong to you. Mesh APs often share one SSID with many BSSIDs — that is expected if every MAC is yours.",
  },
  {
    title: "2. Follow concern links",
    body: "Each concern now points at the offending BSSID, host, or socket. Click through, confirm vendor and signal, and decide whether the row is yours. Unknown BSSIDs on your SSID are the classic impersonation case; known mesh nodes are not.",
  },
  {
    title: "3. Read the live socket table like an incident responder",
    body: "Treat this host as a sensor sitting on your LAN. For every established flow ask: who opened it, which service port, LAN or WAN, and is that destination on your allow list? Unusual flags are investigation hints, not proof of compromise.",
  },
  {
    title: "4. Watch for the quiet tells",
    body: "New WAN peers, DNS that bypasses your resolver, unfinished SYN-SENT bursts, listeners you did not install, and cleartext admin ports (telnet, SMB to the internet) are the same places an attacker would look — you are using them defensively.",
  },
  {
    title: "5. Correlate, then act on the owner",
    body: "Match a remote IP to the LAN device that opened it, then check that device’s firmware, cloud account, or whether it should even be on Wi‑Fi. This dashboard does not intercept payloads; it shows where to look next on equipment you already administer.",
  },
];

function flowKey(flow: SocketFlow) {
  return `${flow.protocol}-${flow.local_ip}:${flow.local_port}-${flow.remote_ip}:${flow.remote_port}`;
}

export function TrafficPage() {
  const { snapshot } = useSnapshot();
  const [params] = useSearchParams();
  const focus = (params.get("focus") || "").toLowerCase();
  const [query, setQuery] = useState("");
  const [onlyUnusual, setOnlyUnusual] = useState(false);

  const live = snapshot?.live_traffic;
  const trafficConcerns = useMemo(
    () => (snapshot?.concerns ?? []).filter((c) => c.section === "traffic").sort((a, b) => {
      const rank = (s: string) => (s === "critical" ? 0 : s === "warning" ? 1 : 2);
      return rank(a.severity) - rank(b.severity);
    }),
    [snapshot],
  );

  const flows = useMemo(() => {
    const list = live?.flows ?? [];
    const q = query.trim().toLowerCase();
    return list.filter((f) => {
      if (onlyUnusual && !f.unusual && !f.new) return false;
      if (!q) return true;
      return [f.remote_ip, f.local_ip, f.service, f.state, f.protocol, String(f.remote_port ?? ""), String(f.local_port ?? "")]
        .join(" ")
        .toLowerCase()
        .includes(q);
    });
  }, [live, query, onlyUnusual]);

  useEffect(() => {
    if (!focus) return;
    document.getElementById(`row-${focus}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [focus, flows]);

  if (!snapshot) return <div className="card empty">Collecting the first sample…</div>;
  const chart = snapshot.history.map((p) => ({
    t: new Date(p.ts * 1000).toLocaleTimeString([], { minute: "2-digit", second: "2-digit" }),
    down: Math.round(p.rx_bps),
    up: Math.round(p.tx_bps),
    signal: p.signal_dbm,
  }));

  return (
    <>
      <div className="grid metrics">
        <div className="card metric">
          <div className="k">Established</div>
          <div className="v">{live?.established ?? 0}</div>
          <div className="s">TCP sessions right now · source {live?.source ?? "—"}</div>
        </div>
        <div className="card metric">
          <div className="k">Listeners</div>
          <div className="v">{live?.listen ?? 0}</div>
          <div className="s">Services this host is advertising</div>
        </div>
        <div className="card metric">
          <div className="k">WAN / LAN peers</div>
          <div className="v">
            {live?.wan_remotes ?? 0} / {live?.lan_remotes ?? 0}
          </div>
          <div className="s">{live?.unique_remotes ?? 0} unique remotes · {live?.syn_sent ?? 0} SYN-SENT</div>
        </div>
        <div className="card metric">
          <div className="k">Interface rate</div>
          <div className="v">{formatBps(snapshot.traffic.find((t) => t.interface !== "lo")?.rx_bps ?? 0)}</div>
          <div className="s">Down on the default path</div>
        </div>
      </div>

      <div className="card">
        <h3>Traffic concerns</h3>
        {trafficConcerns.length === 0 ? (
          <div className="empty">No unusual socket patterns on this sample. Keep using the live table below as a watch list.</div>
        ) : (
          trafficConcerns.map((c) => <ConcernRow key={c.id} concern={c} />)
        )}
      </div>

      <div className="card">
        <div className="toolbar">
          <h3 style={{ margin: 0 }}>Live sockets</h3>
          <label className="toggle">
            <input type="checkbox" checked={onlyUnusual} onChange={(e) => setOnlyUnusual(e.target.checked)} />
            Unusual / new only
          </label>
          <input className="search" placeholder="Filter IP, port, service…" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <div className="table-wrap">
          {flows.length === 0 ? (
            <div className="empty">No matching sockets. Host networking is required to see the Pi’s table instead of the container’s.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Proto</th>
                  <th>State</th>
                  <th>Direction</th>
                  <th>Local</th>
                  <th>Remote</th>
                  <th>Service</th>
                  <th>Scope</th>
                  <th>Flags</th>
                </tr>
              </thead>
              <tbody>
                {flows.map((f) => {
                  const highlighted = Boolean(focus) && [f.remote_ip, f.local_ip].some((v) => (v || "").toLowerCase() === focus);
                  return (
                    <tr
                      key={flowKey(f)}
                      id={f.remote_ip ? `row-${f.remote_ip.toLowerCase()}` : undefined}
                      className={highlighted ? "highlight" : undefined}
                    >
                      <td className="mono">{f.protocol}</td>
                      <td>{dash(f.state)}</td>
                      <td>{f.direction}</td>
                      <td className="mono">
                        {dash(f.local_ip)}:{dash(f.local_port)}
                      </td>
                      <td className="mono">
                        {dash(f.remote_ip)}:{dash(f.remote_port)}
                      </td>
                      <td>{dash(f.service)}</td>
                      <td>{f.scope}</td>
                      <td className="row-tags">
                        {f.unusual ? <Badge tone="warn">Review</Badge> : null}
                        {f.new ? <Badge tone="info">New</Badge> : null}
                        {f.process ? <Badge tone="muted">{f.process}</Badge> : null}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="grid two">
        <div className="card">
          <h3>Listeners on this host</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Port</th>
                  <th>Service</th>
                  <th>Bind</th>
                  <th>Process</th>
                </tr>
              </thead>
              <tbody>
                {(live?.listeners ?? []).map((f) => (
                  <tr key={`${f.protocol}-${f.local_ip}-${f.local_port}`}>
                    <td className="mono">
                      {f.protocol}/{f.local_port}
                    </td>
                    <td>{dash(f.service)}</td>
                    <td className="mono">{dash(f.local_ip)}</td>
                    <td>{dash(f.process)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="card">
          <h3>Top remotes</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>IP</th>
                  <th>Sockets</th>
                  <th>Scope</th>
                  <th>Ports</th>
                </tr>
              </thead>
              <tbody>
                {(live?.top_remotes ?? []).map((t) => (
                  <tr key={t.ip} className={focus && t.ip.toLowerCase() === focus ? "highlight" : undefined}>
                    <td className="mono">{t.ip}</td>
                    <td>{t.count}</td>
                    <td>{t.scope}</td>
                    <td className="mono">{t.ports.join(", ") || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="card">
        <h3>How to use this section</h3>
        <div className="playbook">
          {PLAYBOOK.map((step) => (
            <div key={step.title} className="playbook-step">
              <h4>{step.title}</h4>
              <p>{step.body}</p>
            </div>
          ))}
        </div>
      </div>

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
                formatter={(value, name) => (name === "signal" ? `${value} dBm` : formatBps(Number(value)))}
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
