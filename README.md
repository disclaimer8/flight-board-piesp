# flight-board-piesp

A live **flight board** for a **Raspberry Pi Zero W 1.1** driving one **HUB75
64×128 RGB LED matrix**. It polls [airplanes.live](https://airplanes.live) for
aircraft near a fixed observer location, ranks them by distance, and scrolls the
nearest few across the panel — callsign, altitude, ground speed, distance, and
track.

Sibling project: [`flight-radar-esp32`](https://github.com/disclaimer8) — the
same airplanes.live data source on an ESP32-S3 round LCD.

## How it works

```
airplanes.live  ──fetch──▶  source.py  ──rank──▶  nearest.py  ──compose──▶  layout.py  ──push──▶  renderer.py ──▶ HUB75
   /v2/point         Aircraft[]          top-N by haversine        PIL image            MatrixRenderer
```

- `source.py` — `fetch_nearby(lat, lon, radius_km)` → `list[Aircraft]` from
  `GET /v2/point/{lat}/{lon}/{radius_nm}` (radius in nautical miles).
- `nearest.py` — single-pass haversine, sort, top-N.
- `renderer.py` — abstract `Renderer`; `MatrixRenderer` wraps
  `rgbmatrix.RGBMatrix`, `MockRenderer` records draw calls for tests.
- `layout.py` — PIL composition of one row per aircraft, horizontal scroll for
  long rows, double-buffered push.
- `main.py` — argparse, YAML config, poll/render loop, graceful SIGTERM.

## Hardware

Raspberry Pi Zero W 1.1 + one HUB75 64×128 panel + a **5 V / 4 A** panel supply.
See [docs/hardware.md](docs/hardware.md) for pinout, the Adafruit Bonnet vs
direct-wiring trade-off, power, and the root/GPIO requirement.

## Install (on the Pi)

```bash
git clone https://github.com/disclaimer8/flight-board-piesp.git
cd flight-board-piesp
./scripts/install.sh          # builds rpi-rgb-led-matrix + bindings, sets up .venv
cp config.example.yaml config.yaml   # then edit lat/lon, panel, brightness
```

`rgbmatrix` is built from source by `install.sh` and is **not** a pip
dependency — it only exists on the Pi.

## Run

```bash
# GPIO needs root:
sudo .venv/bin/python -m flight_board.main --config config.yaml
```

Or install the service so it starts at boot:

```bash
sudo cp systemd/flight-board.service /etc/systemd/system/
sudo systemctl enable --now flight-board
```

## Develop / test (any host, no panel)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check .
pytest -q
```

Host tests use `MockRenderer`, so no LED matrix or Pi is needed — this is what
CI runs (`.github/workflows/ci.yml`).

## Configuration

All knobs live in `config.yaml` (copy of `config.example.yaml`): observer
`lat`/`lon`, `distance_km`, `refresh_sec`, `top_n`, `source_url`, panel
`rows`/`cols`/`chain`, `brightness`, and `gpio_slowdown`.

## License

Not yet chosen — add a `LICENSE` of your choice.
