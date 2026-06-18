# flight-board-piesp — Pi (Python)

The **Raspberry Pi Zero W 1.1** implementation. Polls
[airplanes.live](https://airplanes.live) for aircraft near a fixed observer
location, ranks them by distance, and renders the nearest few on a **HUB75
64×128 RGB LED matrix** via
[hzeller/rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix).

> Part of a two-implementation repo — see the [root README](../README.md) for
> the Pi-vs-ESP32 overview. Shared panel/power notes:
> [`../docs/hardware.md`](../docs/hardware.md).

## How it works

```
airplanes.live ──fetch──▶ source.py ──rank──▶ nearest.py ──compose──▶ layout.py ──push──▶ renderer.py ──▶ HUB75
  /v2/point        Aircraft[]        top-N haversine        PIL image           MatrixRenderer
```

- `source.py` — `fetch_nearby(lat, lon, radius_km)` → `list[Aircraft]` from
  `GET /v2/point/{lat}/{lon}/{radius_nm}` (radius in nautical miles).
- `nearest.py` — single-pass haversine, sort, top-N.
- `renderer.py` — abstract `Renderer`; `MatrixRenderer` wraps
  `rgbmatrix.RGBMatrix`, `MockRenderer` records draw calls for tests.
- `layout.py` — 4×16 px rows (callsign / FL / km / heading arrow), scrolling
  callsign, page rotation, double-buffered push.
- `main.py` — argparse, YAML config, poll/render loop, splash, graceful SIGTERM.

## Hardware

Pi Zero W 1.1 + one HUB75 64×128 panel + a **5 V / 4 A** panel supply. This
build uses an Electrodragon "RGB Matrix Adapter for RaspberryPi". See
[docs/hardware.md](docs/hardware.md) for the GPIO map, adapter notes, and the
root/GPIO requirement.

## Install (on the Pi)

```bash
git clone https://github.com/disclaimer8/flight-board-piesp.git
cd flight-board-piesp/pi
./scripts/install.sh          # builds rpi-rgb-led-matrix + bindings, sets up .venv
cp config.example.yaml config.yaml   # then edit lat/lon, panel, brightness
```

`rgbmatrix` is built from source by `install.sh` and is **not** a pip
dependency — it only exists on the Pi.

## Run

```bash
sudo .venv/bin/python -m flight_board.main --config config.yaml   # GPIO needs root
```

Try the layout on a laptop with no panel (prints ASCII frames to stdout):

```bash
pip install -e ".[dev]"
python -m flight_board.main --config config.example.yaml --mock
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
`.github/workflows/pi-ci.yml` runs.

## Configuration

All knobs live in `config.yaml` (copy of `config.example.yaml`): observer
`lat`/`lon`, `distance_km`, `refresh_sec`, `top_n`, `rotate_sec`, `source_url`,
`font_main`/`font_compact`, `colors`, `error_indicator`, panel
`rows`/`cols`/`chain`/`hardware_mapping`/`led_rgb_sequence`, `brightness`, and
`gpio_slowdown`. On Pi Zero W, `pwm_bits` and `limit_refresh_rate_hz` can cap
the matrix refresh load at the cost of some color depth or refresh headroom.

For the direct GPIO wiring used by this build, set:

```yaml
panel:
  hardware_mapping: "regular"
  led_rgb_sequence: "RGB"
pwm_bits: 7
limit_refresh_rate_hz: 120
```

## Fonts

Bundled bitmap fonts under `src/flight_board/fonts/` (via
[rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix)):

- **tom-thumb.bdf** (3×5) — © Brian Swetland / Robey Pointer, **MIT**.
- **5x8.bdf**, **4x6.bdf** — Markus Kuhn's misc-fixed, **public domain**.

A bare filename in `config.yaml`'s `font_main` / `font_compact` is resolved from
this bundled directory first, then as a filesystem path.
