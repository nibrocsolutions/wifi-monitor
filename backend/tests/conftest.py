import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("WIFI_MONITOR_DATA_DIR", str(ROOT / "data-test"))
os.environ.setdefault("WIFI_MONITOR_DEMO", "1")
os.environ.setdefault("WIFI_MONITOR_POLL", "30")
