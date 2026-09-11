export function formatBytes(value: number | null | undefined): string {
  if (value == null) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let amount = value;
  let idx = 0;
  while (amount >= 1024 && idx < units.length - 1) {
    amount /= 1024;
    idx += 1;
  }
  return `${amount.toFixed(amount >= 10 || idx === 0 ? 0 : 1)} ${units[idx]}`;
}

export function formatBps(value: number | null | undefined): string {
  if (value == null) return "—";
  const units = ["bps", "Kbps", "Mbps", "Gbps"];
  let amount = value;
  let idx = 0;
  while (amount >= 1000 && idx < units.length - 1) {
    amount /= 1000;
    idx += 1;
  }
  return `${amount.toFixed(amount >= 10 ? 0 : 1)} ${units[idx]}`;
}

export function formatDbm(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${Math.round(value)} dBm`;
}

export function formatUptime(seconds: number | null | undefined): string {
  if (seconds == null) return "—";
  const s = Math.floor(seconds);
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function signalTone(dbm: number | null | undefined): "ok" | "warn" | "bad" | "muted" {
  if (dbm == null) return "muted";
  if (dbm > -60) return "ok";
  if (dbm > -70) return "warn";
  return "bad";
}

export function dash(value: string | number | null | undefined): string {
  if (value == null || value === "") return "—";
  return String(value);
}
