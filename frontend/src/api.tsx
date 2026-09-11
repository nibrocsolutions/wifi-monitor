import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Snapshot } from "./types";

interface SnapshotState {
  snapshot: Snapshot | null;
  error: string | null;
  connected: boolean;
  refresh: () => Promise<void>;
}

const SnapshotContext = createContext<SnapshotState | null>(null);

async function fetchSnapshot(): Promise<Snapshot> {
  const response = await fetch("/api/snapshot");
  if (!response.ok) {
    throw new Error(`Snapshot request failed (${response.status})`);
  }
  return response.json();
}

export function SnapshotProvider({ children }: { children: ReactNode }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);

  const refresh = async () => {
    try {
      const data = await fetchSnapshot();
      setSnapshot(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load snapshot");
    }
  };

  useEffect(() => {
    void refresh();
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/api/ws`);
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (event) => {
      try {
        setSnapshot(JSON.parse(event.data) as Snapshot);
        setError(null);
      } catch {
        /* ignore malformed frames */
      }
    };
    const poll = window.setInterval(() => {
      if (ws.readyState !== WebSocket.OPEN) {
        void refresh();
      }
    }, 5000);
    return () => {
      ws.close();
      window.clearInterval(poll);
    };
  }, []);

  const value = useMemo(
    () => ({ snapshot, error, connected, refresh }),
    [snapshot, error, connected],
  );

  return <SnapshotContext.Provider value={value}>{children}</SnapshotContext.Provider>;
}

export function useSnapshot() {
  const value = useContext(SnapshotContext);
  if (!value) {
    throw new Error("useSnapshot must be used within SnapshotProvider");
  }
  return value;
}
