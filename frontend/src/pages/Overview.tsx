import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useSnapshot } from "../api";
import { formatBps, formatDbm } from "../format";
import { Badge, HealthRing, SignalBars } from "../components/Widgets";
import type { Concern } from "../types";

function severityRank(value: string) {
  if (value === "critical") return 0;
  if (value === "warning") return 1;
  return 2;
}

export function OverviewPage() {
  const { snapshot } = useSnapshot();
  if (!snapshot) return <div className="card empty">Collecting the first sample…</div>;

  const concerns = [...snapshot.concerns].sort((a, b) => severityRank(a.severity) - severityRank(b.severity));
  const chart = snapshot.history.map((p) => ({
    t: new Date(p.ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    down: Math.round(p.rx_bps),
    up: Math.round(p.tx_bps),
  }));
  const topTraffic = snapshot.traffic.find((t) => t.interface !== "lo");

  return (
    <>
      <div className="grid metrics">
        <div className="card">
          <HealthRing score={snapshot.health_score} label={snapshot.health_level} />
        </div>
        <div className="card metric">
          <div className="k">SSID</div>
          <div className="v">{snapshot.link.ssid ?? "Not associated"}</div>
          <div className="s">
            {snapshot.link.band ?? "—"} · ch {snapshot.link.channel ?? "—"} · {snapshot.access_point.security ?? "unknown security"}
          </div>
        </div>
        <div className="card metric">
          <div className="k">Signal</div>
          <div className="v" style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {formatDbm(snapshot.link.signal_dbm)}
            <SignalBars dbm={snapshot.link.signal_dbm} />
          </div>
          <div className="s">
            {snapshot.link.tx_bitrate_mbps ? `${snapshot.link.tx_bitrate_mbps} Mbps link` : "Rate unavailable"}
          </div>
        </div>
        <div className="card metric">
          <div className="k">LAN / WAN</div>
          <div className="v">{snapshot.devices.length} hosts</div>
          <div className="s">
            {snapshot.internet.online ? `Online · ${snapshot.internet.latency_ms?.toFixed(0) ?? "—"} ms` : "Internet unreachable"}
            {topTraffic ? ` · ↓ ${formatBps(topTraffic.rx_bps)}` : ""}
          </div>
        </div>
      </div>

      <div className="grid split">
        <div className="card">
          <h3>Priority concerns</h3>
          {concerns.length === 0 ? (
            <div className="empty">No concerns. The local wireless environment looks clean.</div>
          ) : (
            concerns.slice(0, 5).map((c) => <ConcernRow key={c.id} concern={c} />)
          )}
        </div>
        <div className="card">
          <h3>Throughput</h3>
          <div className="chart">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chart}>
                <defs>
                  <linearGradient id="down" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3ee0a4" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#3ee0a4" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                <XAxis dataKey="t" hide />
                <YAxis hide />
                <Tooltip
                  contentStyle={{ background: "#101824", border: "1px solid rgba(168,197,218,0.16)", borderRadius: 12 }}
                  formatter={(value) => formatBps(Number(value))}
                />
                <Area type="monotone" dataKey="down" stroke="#3ee0a4" fill="url(#down)" />
                <Area type="monotone" dataKey="up" stroke="#6ea8ff" fill="transparent" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </>
  );
}

export function ConcernRow({ concern }: { concern: Concern }) {
  return (
    <div className="concern">
      <div>
        <Badge tone={concern.severity}>{concern.severity}</Badge>
      </div>
      <div>
        <h4>{concern.title}</h4>
        <p>{concern.detail}</p>
        <p className="rec">{concern.recommendation}</p>
      </div>
    </div>
  );
}

export function ConcernsPage() {
  const { snapshot } = useSnapshot();
  if (!snapshot) return <div className="card empty">Collecting the first sample…</div>;
  const concerns = [...snapshot.concerns].sort((a, b) => severityRank(a.severity) - severityRank(b.severity));
  return (
    <div className="card">
      <h3>{concerns.length} reported items</h3>
      {concerns.length === 0 ? (
        <div className="empty">Nothing to review. Health checks passed on this sample.</div>
      ) : (
        concerns.map((c) => <ConcernRow key={c.id} concern={c} />)
      )}
    </div>
  );
}
