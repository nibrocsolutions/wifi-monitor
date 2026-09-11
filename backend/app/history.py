from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any

from .models import LanDevice, TrafficPoint


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class HistoryStore:
    def __init__(self, maxlen: int = 180) -> None:
        self.maxlen = maxlen
        self._points: list[TrafficPoint] = []
        self._lock = threading.Lock()

    def add(self, point: TrafficPoint) -> None:
        with self._lock:
            self._points.append(point)
            if len(self._points) > self.maxlen:
                self._points = self._points[-self.maxlen :]

    def snapshot(self) -> list[TrafficPoint]:
        with self._lock:
            return list(self._points)


class DeviceRegistry:
    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._seen: dict[str, dict[str, Any]] = {}
        self._loaded = False
        self._boot = time.time()

    def _key(self, device: LanDevice) -> str:
        return (device.mac or device.ip or "").lower()

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                self._seen = payload
        except OSError:
            self._seen = {}
        except json.JSONDecodeError:
            self._seen = {}

    def _save(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(self._seen, handle, indent=2, sort_keys=True)
        os.replace(tmp, self.path)

    def observe(self, devices: list[LanDevice]) -> list[LanDevice]:
        with self._lock:
            self._load()
            now = _now_iso()
            updated: list[LanDevice] = []
            changed = False
            for device in devices:
                key = self._key(device)
                if not key:
                    updated.append(device)
                    continue
                record = self._seen.get(key)
                if record is None:
                    record = {"first_seen": now, "last_seen": now}
                    self._seen[key] = record
                    changed = True
                    is_new = True
                else:
                    record["last_seen"] = now
                    changed = True
                    first = record.get("first_seen")
                    is_new = False
                    if first:
                        try:
                            first_ts = datetime.fromisoformat(first).timestamp()
                            is_new = (time.time() - first_ts) < 600 and (
                                time.time() - self._boot
                            ) < 600
                        except ValueError:
                            is_new = False
                updated.append(
                    device.model_copy(
                        update={
                            "first_seen": record.get("first_seen"),
                            "last_seen": record.get("last_seen"),
                            "new": is_new and not device.is_self and not device.is_gateway,
                        }
                    )
                )
            if changed:
                try:
                    self._save()
                except OSError:
                    pass
            return updated
