import {
  Activity,
  AlertTriangle,
  Globe,
  LayoutDashboard,
  Network,
  Radar,
  Radio,
  Router,
  Server,
  Smartphone,
  Wifi,
} from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useSnapshot } from "../api";
import { formatTime } from "../format";

const links = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/concerns", label: "Concerns", icon: AlertTriangle, countKey: "concerns" },
  { to: "/connection", label: "Connection", icon: Wifi },
  { to: "/access-point", label: "Access point", icon: Router },
  { to: "/nearby", label: "Nearby networks", icon: Radar },
  { to: "/devices", label: "LAN devices", icon: Smartphone },
  { to: "/traffic", label: "Live traffic", icon: Activity },
  { to: "/internet", label: "Internet", icon: Globe },
  { to: "/interfaces", label: "Interfaces", icon: Network },
  { to: "/system", label: "System", icon: Server },
];

const titles: Record<string, [string, string]> = {
  "/": ["Overview", "Live health of the Wi‑Fi network this host is joined to."],
  "/concerns": ["Concerns", "Issues worth reviewing, ordered by severity."],
  "/connection": ["Connection", "Association, signal, rates, and radio counters."],
  "/access-point": ["Access point", "The BSS this Pi is using as its gateway radio."],
  "/nearby": ["Nearby networks", "Everything the radio can currently hear."],
  "/devices": ["LAN devices", "Hosts discovered on the local subnet."],
  "/traffic": ["Live traffic", "Sockets, listeners, unusual flows, and how to investigate them."],
  "/internet": ["Internet", "DNS, latency, WAN reachability, and public identity."],
  "/interfaces": ["Interfaces", "Addresses, link state, and frame counters."],
  "/system": ["System", "Host resources for the Raspberry Pi running this monitor."],
};

export function Layout() {
  const { snapshot, connected, error } = useSnapshot();
  const location = useLocation();
  const [title, lede] = titles[location.pathname] ?? titles["/"];
  const concernCount = snapshot?.concerns.filter((c) => c.severity !== "info").length ?? 0;

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Radio size={18} />
          </div>
          <div>
            <h1>WiFi Monitor</h1>
            <p>Local network operations</p>
          </div>
        </div>
        <nav className="nav">
          {links.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink key={link.to} to={link.to} end={link.to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
                <Icon size={16} />
                {link.label}
                {link.countKey === "concerns" && concernCount > 0 ? <span className="count">{concernCount}</span> : null}
              </NavLink>
            );
          })}
        </nav>
        <div className="sidebar-foot">
          <div className="label">Host</div>
          <div className="value">{snapshot?.system.hostname ?? "waiting…"}</div>
          <div className="label" style={{ marginTop: 10 }}>
            Address
          </div>
          <div className="value">{snapshot?.local_ip ?? "—"}</div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div>
            <h2>{title}</h2>
            <p className="lede">{snapshot?.summary || lede}</p>
          </div>
          <div className="top-meta">
            {snapshot?.demo ? <span className="pill demo">Demo data</span> : null}
            <span className={`pill ${connected ? "live" : ""}`}>
              <span className="pulse" />
              {connected ? "Live" : "Polling"}
            </span>
            <span className="pill">{snapshot?.link.ssid ?? "No SSID"}</span>
            <span className="pill">{formatTime(snapshot?.generated_at)}</span>
          </div>
        </header>
        {error ? <div className="error-banner">{error}</div> : null}
        <div className="content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
