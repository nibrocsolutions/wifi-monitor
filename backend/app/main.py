from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .collect import Collector
from .concerns import analyze, health_level, score_concerns, summarize
from .models import Snapshot

DATA_DIR = os.environ.get("WIFI_MONITOR_DATA_DIR", "/data")
PORT = int(os.environ.get("WIFI_MONITOR_PORT", "8085"))
DEMO = os.environ.get("WIFI_MONITOR_DEMO", "").lower() in {"1", "true", "yes"}
POLL_SECONDS = float(os.environ.get("WIFI_MONITOR_POLL", "5"))

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if not STATIC_DIR.exists():
    STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

collector = Collector(data_dir=DATA_DIR, demo=DEMO)
_latest: Snapshot | None = None
_clients: set[WebSocket] = set()
_lock = asyncio.Lock()


def enrich(snapshot: Snapshot) -> Snapshot:
    snapshot.concerns = analyze(snapshot)
    snapshot.health_score = score_concerns(snapshot.concerns)
    snapshot.health_level = health_level(snapshot.health_score)  # type: ignore[assignment]
    snapshot.summary = summarize(snapshot)
    return snapshot


async def _broadcast(payload: dict[str, Any]) -> None:
    stale: list[WebSocket] = []
    for ws in list(_clients):
        try:
            await ws.send_json(payload)
        except Exception:
            stale.append(ws)
    for ws in stale:
        _clients.discard(ws)


async def poll_loop() -> None:
    global _latest
    while True:
        try:
            snapshot = await asyncio.to_thread(collector.collect)
            snapshot = enrich(snapshot)
            async with _lock:
                _latest = snapshot
            await _broadcast(snapshot.model_dump())
        except Exception:
            pass
        await asyncio.sleep(POLL_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    os.makedirs(DATA_DIR, exist_ok=True)
    task = asyncio.create_task(poll_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="WiFi Monitor", version=__version__, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "version": __version__, "demo": DEMO}


@app.get("/api/snapshot")
async def snapshot() -> Snapshot:
    global _latest
    async with _lock:
        current = _latest
    if current is None:
        current = enrich(await asyncio.to_thread(collector.collect))
        async with _lock:
            _latest = current
    return current


@app.websocket("/api/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    _clients.add(ws)
    try:
        async with _lock:
            current = _latest
        if current is not None:
            await ws.send_json(current.model_dump())
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(ws)


if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str) -> FileResponse:
        candidate = STATIC_DIR / full_path
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
