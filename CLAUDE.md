# flight-board-piesp — conventions

Live flight board: Raspberry Pi Zero W 1.1 (armv6l) + one HUB75 64×128 LED
matrix. Polls airplanes.live, ranks nearest aircraft by distance, scrolls them
on the panel. See [README.md](README.md) and [docs/hardware.md](docs/hardware.md).

## Architecture

Pure, host-testable logic + a thin hardware layer (mirrors the `flight-radar-esp32`
sibling's "pure core + thin Arduino" split):

- `src/flight_board/source.py` — airplanes.live HTTP + `Aircraft` dataclass.
  URL is `/v2/point/{lat}/{lon}/{radius_nm}` (radius nautical miles, ceil of km).
- `src/flight_board/nearest.py` — haversine + top-N. **Single pass**: distance
  is computed once per aircraft, stored on `dist_km`, and reused as the sort key.
- `src/flight_board/renderer.py` — abstract `Renderer`; `MatrixRenderer` (real,
  wraps `rgbmatrix`) and `MockRenderer` (records draw calls). **`rgbmatrix` is
  imported lazily** inside `MatrixRenderer`/`build_matrix_options` so every other
  module imports cleanly on a host with no panel.
- `src/flight_board/layout.py` — PIL composition, one row per aircraft, scroll
  for over-wide rows, double-buffered (`set_image` then `swap`).
- `src/flight_board/main.py` — argparse, YAML config, poll/render loop, SIGTERM.

## Code style

- Python **3.9+** floor (Pi Zero W 1.1 is armv6l — the binding wheels and the
  CPU are the bottleneck). Every module starts with
  `from __future__ import annotations` so `list[X]` / `X | None` annotations are
  free on 3.9.
- Lint with **ruff** (`E,F,I,UP`). `ruff check .` must be clean before commit.
- Keep modules small and single-purpose; no business logic in `main.py` beyond
  wiring.

## Tests

- **Host-runnable, no hardware.** Tests must never import `rgbmatrix`.
- Display tests use `MockRenderer` and assert on its recorded `calls`.
- `source.py` tests mock HTTP with `responses` — **no real network**.
- `nearest.py` tests are pure math.
- Run: `pytest -q` and `ruff check .` (this is exactly what CI runs).
- `rgbmatrix` is **never** a CI/pip dependency — it is built on the Pi via
  `scripts/install.sh` only.

## Don't block the render path

- The panel must keep refreshing. `main.py` separates the slow network poll
  (every `refresh_sec`) from the redraw loop (every frame, advancing scroll).
  Don't put blocking network calls in the per-frame path.
- Compose into a PIL image, then push once and `swap` once — don't draw
  pixel-by-pixel onto the live canvas.

## Gotchas

- GPIO/DMA needs **root** — run via `sudo` or the systemd unit.
- HUB75 panel needs its **own 5 V / 4 A supply**, common ground with the Pi.
- airplanes.live wants ≤ 1 request/sec and a **descriptive User-Agent**
  (generic/empty UA → HTTP 403); see `source.USER_AGENT`.
- North-up / distance-only board — no heading hardware involved.
- `config.yaml` is gitignored; edit a copy of `config.example.yaml`.
