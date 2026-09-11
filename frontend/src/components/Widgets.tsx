import type { ReactNode } from "react";
import { signalTone } from "../format";

export function SignalBars({ dbm }: { dbm: number | null | undefined }) {
  const tone = signalTone(dbm);
  let filled = 0;
  if (dbm != null) {
    if (dbm > -55) filled = 4;
    else if (dbm > -65) filled = 3;
    else if (dbm > -75) filled = 2;
    else filled = 1;
  }
  return (
    <span className="bars" title={dbm == null ? "No signal" : `${Math.round(dbm)} dBm`}>
      {[6, 10, 14, 18].map((h, i) => (
        <span key={h} className={i < filled ? `on ${tone}` : ""} style={{ height: h }} />
      ))}
    </span>
  );
}

export function HealthRing({ score, label }: { score: number; label: string }) {
  const r = 34;
  const c = 2 * Math.PI * r;
  const offset = c - (Math.max(0, Math.min(100, score)) / 100) * c;
  const color = score >= 75 ? "#3ee0a4" : score >= 55 ? "#f0b429" : "#ff6b7a";
  return (
    <div className="health">
      <svg width="92" height="92" viewBox="0 0 92 92">
        <circle cx="46" cy="46" r={r} stroke="rgba(255,255,255,0.08)" strokeWidth="8" fill="none" />
        <circle
          cx="46"
          cy="46"
          r={r}
          stroke={color}
          strokeWidth="8"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          transform="rotate(-90 46 46)"
        />
        <text x="46" y="50" textAnchor="middle" fill="#e8f1f6" fontSize="20" fontWeight="700">
          {score}
        </text>
      </svg>
      <div>
        <div className="k">Network health</div>
        <div className="v" style={{ fontSize: 22 }}>
          {label}
        </div>
      </div>
    </div>
  );
}

export function Badge({ children, tone = "muted" }: { children: ReactNode; tone?: string }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function KeyValue({ items }: { items: Array<[string, ReactNode]> }) {
  return (
    <dl className="kv">
      {items.map(([k, v]) => (
        <span key={k} style={{ display: "contents" }}>
          <dt>{k}</dt>
          <dd>{v ?? "—"}</dd>
        </span>
      ))}
    </dl>
  );
}
