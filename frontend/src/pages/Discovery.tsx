import { useMemo, useState } from "react";
import { useSnapshot } from "../api";
import { dash, formatDbm } from "../format";
import { Badge, SignalBars } from "../components/Widgets";

export function NearbyPage() {
  const { snapshot } = useSnapshot();
  const [query, setQuery] = useState("");
  const rows = useMemo(() => {
    const list = snapshot?.nearby ?? [];
    const q = query.trim().toLowerCase();
    if (!q) return list;
    return list.filter((n) =>
      [n.ssid, n.bssid, n.vendor, n.security, n.band, String(n.channel ?? "")]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(q),
    );
  }, [snapshot, query]);

  if (!snapshot) return <div className="card empty">Collecting the first sample…</div>;

  return (
    <div className="card">
      <div className="toolbar">
        <h3 style={{ margin: 0 }}>
          {rows.length} network{rows.length === 1 ? "" : "s"} in range
        </h3>
        <input className="search" placeholder="Filter SSID, BSSID, vendor…" value={query} onChange={(e) => setQuery(e.target.value)} />
      </div>
      <div className="table-wrap">
        {rows.length === 0 ? (
          <div className="empty">No nearby BSS records. On a Pi, run with host networking so `iw scan` can see the air.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>SSID</th>
                <th>Signal</th>
                <th>Band</th>
                <th>Ch</th>
                <th>Security</th>
                <th>BSSID</th>
                <th>Vendor</th>
                <th>Width</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((n) => (
                <tr key={n.bssid ?? `${n.ssid}-${n.channel}`} className={n.is_associated ? "assoc" : undefined}>
                  <td>{n.ssid ?? <span className="badge muted">hidden</span>}</td>
                  <td>
                    <span style={{ display: "inline-flex", gap: 8, alignItems: "center" }}>
                      <SignalBars dbm={n.signal_dbm} /> {formatDbm(n.signal_dbm)}
                    </span>
                  </td>
                  <td>{dash(n.band)}</td>
                  <td>{dash(n.channel)}</td>
                  <td>
                    <Badge tone={n.security === "Open" || n.security === "WEP" ? "bad" : "ok"}>{n.security ?? "—"}</Badge>
                  </td>
                  <td className="mono">{dash(n.bssid)}</td>
                  <td>{dash(n.vendor)}</td>
                  <td>{n.width_mhz ? `${n.width_mhz} MHz` : "—"}</td>
                  <td className="row-tags">
                    {n.is_associated ? <Badge tone="ok">Associated</Badge> : null}
                    {n.is_duplicate_ssid ? <Badge tone="warn">Duplicate SSID</Badge> : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export function DevicesPage() {
  const { snapshot } = useSnapshot();
  const [query, setQuery] = useState("");
  const rows = useMemo(() => {
    const list = snapshot?.devices ?? [];
    const q = query.trim().toLowerCase();
    if (!q) return list;
    return list.filter((d) =>
      [d.hostname, d.ip, d.mac, d.vendor, d.state].filter(Boolean).join(" ").toLowerCase().includes(q),
    );
  }, [snapshot, query]);

  if (!snapshot) return <div className="card empty">Collecting the first sample…</div>;

  return (
    <div className="card">
      <div className="toolbar">
        <h3 style={{ margin: 0 }}>
          {rows.length} device{rows.length === 1 ? "" : "s"} on {snapshot.subnet ?? "the LAN"}
        </h3>
        <input className="search" placeholder="Filter host, IP, MAC…" value={query} onChange={(e) => setQuery(e.target.value)} />
      </div>
      <div className="table-wrap">
        {rows.length === 0 ? (
          <div className="empty">No neighbors yet. ARP, arp-scan, or nmap host discovery will fill this table on a Pi.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Host</th>
                <th>IP</th>
                <th>MAC</th>
                <th>Vendor</th>
                <th>State</th>
                <th>Role</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => (
                <tr key={`${d.mac}-${d.ip}`}>
                  <td>{d.hostname ?? "—"}</td>
                  <td className="mono">{dash(d.ip)}</td>
                  <td className="mono">{dash(d.mac)}</td>
                  <td>{dash(d.vendor)}</td>
                  <td>{dash(d.state)}</td>
                  <td className="row-tags">
                    {d.is_gateway ? <Badge tone="info">Gateway</Badge> : null}
                    {d.is_self ? <Badge tone="ok">This host</Badge> : null}
                    {d.new ? <Badge tone="warn">New</Badge> : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
