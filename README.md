# WiFi Monitor

Professional local Wi‑Fi operations dashboard for a Raspberry Pi. It watches the network the Pi is joined to, surfaces every useful radio and LAN signal in its own section, and flags security or quality concerns.

The UI is a live dark-console dashboard. The collector reads the Pi’s wireless interface, nearby BSS list, LAN neighbors, routes, DNS, and internet probes — then scores the result.

## Install on a Raspberry Pi

You need [Docker](https://docs.docker.com/engine/install/raspberry-pi-os/) with the Compose plugin, and a Pi that is already associated with the Wi‑Fi network you want to observe.

```bash
git clone https://github.com/nibrocsolutions/wifi-monitor.git
cd wifi-monitor
./install.sh
```

That is the whole install. `install.sh` runs:

```bash
docker compose up -d --build
```

Then open **http://\<pi-ip\>:8085** from a phone or laptop on the same LAN.

The container uses **host networking** and **privileged** mode so `iw` can talk to the Pi’s Wi‑Fi radio. Without those, the dashboard can still show host metrics, but nearby-network scans will be empty.

### Manual Docker commands

```bash
git clone https://github.com/nibrocsolutions/wifi-monitor.git
cd wifi-monitor
docker compose up -d --build
```

Equivalent `docker run` after a local build:

```bash
docker build -t wifi-monitor:local .
docker run -d --name wifi-monitor --network host --privileged \
  -v wifi-monitor-data:/data \
  -e WIFI_MONITOR_PORT=8085 \
  wifi-monitor:local
```

Stop / restart:

```bash
docker compose logs -f
docker compose restart
docker compose down
```

## What the app shows

Each area of the product is a first-class section in the sidebar:

| Section | Contents |
| --- | --- |
| **Overview** | Health score, SSID, signal, LAN/WAN snapshot, top concerns, live throughput |
| **Concerns** | Ranked issues: weak signal, open/WEP/WPA1, duplicate SSID, crowded channels, new devices, DNS/WAN failure, hot Pi, interface errors |
| **Connection** | Association, BSSID, band/channel, RSSI, bitrates, power save, retries, missed beacons |
| **Access point** | Serving BSS security/ciphers, gateway IP, subnet, gateway reachability |
| **Nearby networks** | Every BSS the radio can hear: signal, channel, encryption, vendor, hidden/duplicate flags |
| **LAN devices** | Neighbors from ARP / arp-scan / nmap host discovery, with gateway and “this host” tags |
| **Traffic** | Per-interface rates and a rolling throughput history |
| **Internet** | DNS, public IP, probe RTT/loss to 1.1.1.1 and 8.8.8.8 |
| **Interfaces** | Addresses, counters, errors/drops, routing table |
| **System** | Pi model, OS, CPU, memory, SoC temperature, collector capabilities |

New MAC addresses are remembered under `/data` so they stay marked as new across refreshes.

## Demo mode

On a machine without a Wi‑Fi radio (or before you deploy to the Pi), you can preview the full UI:

```bash
WIFI_MONITOR_DEMO=1 WIFI_MONITOR_DATA_DIR=./data \
  PYTHONPATH=backend python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8085
```

The banner **Demo data** is shown whenever sample wireless data is injected.

## Local development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
pytest

cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to port 8085. Run the API with demo mode in another terminal.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `WIFI_MONITOR_PORT` | `8085` | Listen port (host network) |
| `WIFI_MONITOR_DATA_DIR` | `/data` | Device history |
| `WIFI_MONITOR_POLL` | `5` | Snapshot interval, seconds |
| `WIFI_MONITOR_IFACE` | auto | Force a wireless interface name |
| `WIFI_MONITOR_DEMO` | unset | `1` to load demonstration radio/LAN data |
| `TZ` | `America/New_York` | Container timezone |

## Security notes

This monitor is for **your** LAN and the SSID the Pi is already joined to. It performs standard host discovery (`ip neigh`, optional `arp-scan`, optional `nmap -sn`) and a passive/privileged `iw scan`. It does not include exploit payloads or attack workflows.

Keep the dashboard on a trusted network. Host networking binds port 8085 on the Pi; put a reverse proxy or firewall in front of it if the Pi is reachable beyond your home LAN.
