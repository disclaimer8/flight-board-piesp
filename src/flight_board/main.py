"""Entry point: poll airplanes.live, rank nearest, render to the HUB75 panel.

Run on the Pi with ``python -m flight_board.main --config config.yaml`` (GPIO
needs root; see ``systemd/flight-board.service``). Data is refreshed every
``refresh_sec`` while the panel keeps redrawing at ``scroll_fps`` so long rows
scroll smoothly between fetches. SIGTERM/SIGINT exit cleanly.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Any

import requests
import yaml

from flight_board.layout import Layout
from flight_board.nearest import nearest
from flight_board.renderer import MatrixRenderer, Renderer
from flight_board.source import fetch_nearby

log = logging.getLogger("flight_board")

_running = True


def _handle_signal(signum: int, _frame: Any) -> None:
    global _running
    log.info("received signal %d, shutting down", signum)
    _running = False


def load_config(path: str | Path) -> dict[str, Any]:
    """Parse the YAML config file."""
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def run(config: dict[str, Any], renderer: Renderer) -> None:
    """Main poll/rank/render loop. Returns when a signal clears ``_running``."""
    lat = float(config["lat"])
    lon = float(config["lon"])
    distance_km = float(config.get("distance_km", 50))
    refresh_sec = float(config.get("refresh_sec", 15))
    top_n = int(config.get("top_n", 8))
    source_url = str(config.get("source_url", "https://api.airplanes.live"))
    scroll_fps = float(config.get("scroll_fps", 20))

    layout = Layout(renderer.width, renderer.height, font_path=config.get("font"))
    frame_interval = 1.0 / scroll_fps if scroll_fps > 0 else 0.05
    session = requests.Session()

    aircraft: list = []
    last_fetch = 0.0
    scroll_offset = 0

    while _running:
        now = time.monotonic()
        if now - last_fetch >= refresh_sec:
            try:
                raw = fetch_nearby(lat, lon, distance_km, source_url=source_url, session=session)
                aircraft = nearest(raw, lat, lon, top_n)
                log.info("fetched %d aircraft, showing %d", len(raw), len(aircraft))
            except (requests.RequestException, ValueError) as exc:
                log.warning("fetch failed: %s", exc)
            last_fetch = now

        layout.render(renderer, aircraft, scroll_offset)
        scroll_offset += 1
        time.sleep(frame_interval)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HUB75 flight board")
    parser.add_argument("--config", required=True, help="path to YAML config")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    config = load_config(args.config)
    renderer = MatrixRenderer(config)
    run(config, renderer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
