from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
from typing import Sequence


def which(binary: str) -> str | None:
    return shutil.which(binary)


def run_cmd(
    args: Sequence[str],
    timeout: float = 8.0,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    try:
        proc = subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=merged,
            check=False,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except FileNotFoundError:
        return 127, "", f"not found: {args[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


def read_text(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def first_existing(*paths: str) -> str | None:
    for path in paths:
        if os.path.exists(path):
            return path
    return None


def normalize_mac(value: str | None) -> str | None:
    if not value:
        return None
    hex_only = re.sub(r"[^0-9A-Fa-f]", "", value)
    if len(hex_only) != 12:
        return None
    pairs = [hex_only[i : i + 2] for i in range(0, 12, 2)]
    return ":".join(pairs).lower()


def freq_to_channel(freq_mhz: float | None) -> int | None:
    if freq_mhz is None:
        return None
    freq = int(round(freq_mhz))
    if 2412 <= freq <= 2484:
        if freq == 2484:
            return 14
        return (freq - 2407) // 5
    if 5000 <= freq <= 5895:
        return (freq - 5000) // 5
    if 5955 <= freq <= 7115:
        return (freq - 5950) // 5
    return None


def freq_to_band(freq_mhz: float | None) -> str | None:
    if freq_mhz is None:
        return None
    if freq_mhz < 3000:
        return "2.4 GHz"
    if freq_mhz < 5900:
        return "5 GHz"
    return "6 GHz"


def signal_quality_percent(signal_dbm: float | None) -> float | None:
    if signal_dbm is None:
        return None
    # Map typical Wi-Fi RSSI (-100..-40) onto 0..100.
    clamped = max(-100.0, min(-40.0, signal_dbm))
    return round(((clamped + 100.0) / 60.0) * 100.0, 1)


def parse_bitrate(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"([\d.]+)\s*(MBit/s|Mb/s|Mbit/s|Mbps)", text, re.I)
    if match:
        return float(match.group(1))
    match = re.search(r"([\d.]+)\s*(GBit/s|Gb/s|Gbps)", text, re.I)
    if match:
        return float(match.group(1)) * 1000.0
    return None


def local_ipv4s() -> list[str]:
    addresses: list[str] = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip not in addresses and not ip.startswith("127."):
                addresses.append(ip)
    except OSError:
        pass
    return addresses


def is_private_ip(ip: str) -> bool:
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return False
    return (
        nums[0] == 10
        or (nums[0] == 192 and nums[1] == 168)
        or (nums[0] == 172 and 16 <= nums[1] <= 31)
        or nums[0] == 169
    )
