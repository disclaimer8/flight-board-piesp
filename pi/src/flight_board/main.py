"""Entry point: poll airplanes.live, rank nearest, render to the HUB75 panel.

On the Pi: ``sudo .venv/bin/python -m flight_board.main --config config.yaml``
(GPIO needs root). Locally, without any hardware:

    python -m flight_board.main --config config.example.yaml --mock

``--mock`` swaps in a MockRenderer fed by a canonical set of fake aircraft and
prints each composed frame to stdout, so the layout logic can be eyeballed on a
laptop. Data is refreshed every ``refresh_sec`` while the panel keeps redrawing
so long callsigns scroll and pages rotate between fetches. SIGTERM/SIGINT clear
the panel and exit 0.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

import requests
import yaml

from flight_board.layout import Layout, frame_to_ascii, paginate, select_page
from flight_board.nearest import nearest
from flight_board.renderer import MatrixRenderer, MockRenderer, Renderer
from flight_board.source import Aircraft, fetch_nearby

log = logging.getLogger("flight_board")

_running = True

# Canonical fake fleet for --mock: varied callsigns, altitudes, headings, and
# positions. The last field is a longitude offset from the observer (gives a
# spread of distances); the 5th has a long callsign so scrolling is visible.
# (hex, callsign, type, alt_ft, gs_kt, track, lon_offset)
_MOCK_ROWS = [
    ("400a1b", "BAW2901", "A320", 37000, 448, 90, 0.07),
    ("3c6dd2", "DLH9LH", "A21N", 12000, 290, 45, 0.17),
    ("4ca7b1", "RYR41KP", "B738", 35000, 460, 180, 0.34),
    ("a1b2c3", "UAL55", "B789", 40000, 510, 270, 0.50),
    ("48adef", "AFR1234XRAY", "A359", 8000, 240, 315, 0.70),
    ("ab1234", "EJU73Q", "A320", 26000, 400, 0, 1.00),
]


def _handle_signal(signum: int, _frame: Any) -> None:
    global _running
    log.info("received signal %d, shutting down", signum)
    _running = False


def load_config(path: str | Path) -> dict[str, Any]:
    """Parse the YAML config file."""
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _mock_fleet(lat: float, lon: float) -> list[Aircraft]:
    """Build the canonical fleet, anchored near (lat, lon) for realistic distances."""
    return [
        Aircraft(
            hex=hex_, callsign=cs, aircraft_type=typ, alt_ft=alt,
            ground_speed_kt=gs, track=trk, lat=lat, lon=lon + dlon,
        )
        for hex_, cs, typ, alt, gs, trk, dlon in _MOCK_ROWS
    ]


def run(
    config: dict[str, Any],
    renderer: Renderer,
    *,
    fetcher: Callable[[], list[Aircraft]] | None = None,
    print_frames: bool = False,
) -> None:
    """Main poll/rank/render loop. Returns when a signal clears ``_running``."""
    try:
        lat = float(config["lat"])
        lon = float(config["lon"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("config must set numeric 'lat' and 'lon'") from exc
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        raise ValueError(f"lat/lon out of range: {lat}, {lon}")
    distance_km = float(config.get("distance_km", 50))
    refresh_sec = float(config.get("refresh_sec", 15))
    rotate_sec = float(config.get("rotate_sec", 8))
    top_n = int(config.get("top_n", 8))
    if top_n < 0:
        raise ValueError(f"top_n must be >= 0, got {top_n}")
    source_url = str(config.get("source_url", "https://api.airplanes.live"))
    scroll_fps = float(config.get("scroll_fps", 20))

    layout = Layout(
        renderer.width,
        renderer.height,
        font_main=config.get("font_main"),
        font_compact=config.get("font_compact"),
        colors=config.get("colors"),
        error_indicator=bool(config.get("error_indicator", True)),
    )

    if fetcher is None:
        session = requests.Session()

        def fetcher() -> list[Aircraft]:
            return fetch_nearby(lat, lon, distance_km, source_url=source_url, session=session)

    frame_interval = 1.0 / scroll_fps if scroll_fps > 0 else 0.05

    # The blocking HTTP poll runs in a background thread; the render loop only
    # reads a snapshot, so the panel never freezes mid-fetch — this is the
    # CLAUDE.md "don't block the render path" contract (the poll used to be
    # inline, stalling scrolling for the whole round-trip every refresh_sec).
    state_lock = threading.Lock()
    shared: dict[str, Any] = {"aircraft": [], "have_data": False, "stale": False}

    def poll_worker() -> None:
        last_fetch = 0.0
        while _running:
            now = time.monotonic()
            if last_fetch == 0.0 or now - last_fetch >= refresh_sec:
                last_fetch = now
                try:
                    raw = fetcher()
                    ranked = nearest(raw, lat, lon, top_n)
                    with state_lock:
                        shared["aircraft"] = ranked
                        shared["have_data"] = True
                        shared["stale"] = False
                    log.info("fetched %d aircraft, showing %d", len(raw), len(ranked))
                except (requests.RequestException, ValueError) as exc:
                    with state_lock:
                        shared["stale"] = shared["have_data"]  # stale only after first data
                    print(f"poll failed: {exc}", file=sys.stderr)
            time.sleep(0.25)

    scroll_offset = 0
    start = time.monotonic()
    worker = threading.Thread(target=poll_worker, name="poll", daemon=True)
    worker.start()

    layout.render_splash(renderer, lat, lon, "loading...")
    try:
        while _running:
            now = time.monotonic()
            with state_lock:
                aircraft = shared["aircraft"]
                have_data = shared["have_data"]
                stale = shared["stale"]

            if not have_data:
                # First poll has no data yet: keep the splash up another cycle.
                layout.render_splash(renderer, lat, lon, "loading...")
            else:
                page_index = int((now - start) // rotate_sec)
                page = select_page(aircraft, page_index, per_page=layout.rows)
                layout.render(renderer, page, scroll_offset, stale=stale)
                if print_frames:
                    npages = len(paginate(aircraft, layout.rows))
                    print(f"--- frame: page {page_index % npages + 1}/{npages}, "
                          f"{len(aircraft)} aircraft, stale={stale} ---")
                    print(frame_to_ascii(renderer.images[-1]))

            scroll_offset += 1
            time.sleep(frame_interval)
    finally:
        worker.join(timeout=2.0)
        renderer.clear()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HUB75 flight board")
    parser.add_argument("--config", required=True, help="path to YAML config")
    parser.add_argument("--mock", action="store_true",
                        help="run without hardware: MockRenderer + fake fleet, print frames")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    config = load_config(args.config)

    if args.mock:
        lat = float(config["lat"])
        lon = float(config["lon"])
        renderer: Renderer = MockRenderer(128, 64)
        run(config, renderer, fetcher=lambda: _mock_fleet(lat, lon), print_frames=True)
    else:
        renderer = MatrixRenderer(config)
        run(config, renderer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
