"""airplanes.live data source.

Mirrors the URL/field shape used by the ESP32 sibling project
(``flight-radar-esp32``): ``GET /v2/point/{lat}/{lon}/{radius_nm}`` returning
``{"ac": [...]}``. Radius is expressed in nautical miles (1 NM = 1.852 km),
rounded up from the requested kilometre radius.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import requests

API_BASE = "https://api.airplanes.live"

# planespotters/airplanes.live reject generic or empty User-Agents; send a
# descriptive one (same lesson as the ESP32 firmware).
USER_AGENT = "flight-board-piesp/0.1 (+https://github.com/disclaimer8/flight-board-piesp)"

DEFAULT_TIMEOUT = 10.0


@dataclass
class Aircraft:
    """A single aircraft as reported by airplanes.live.

    ``dist_km`` is left at 0.0 by the source and filled in by
    :func:`flight_board.nearest.nearest`.
    """

    hex: str = ""
    callsign: str = ""
    aircraft_type: str = ""
    alt_ft: float | None = None
    ground_speed_kt: float | None = None
    track: float | None = None
    squawk: str = ""
    registration: str = ""
    lat: float = 0.0
    lon: float = 0.0
    on_ground: bool = False
    dist_km: float = field(default=0.0)


def radius_km_to_nm(radius_km: float) -> int:
    """Convert a kilometre radius to whole nautical miles, rounded up."""
    return int(math.ceil(radius_km / 1.852))


def _parse_aircraft(raw: dict[str, Any]) -> Aircraft:
    """Build an :class:`Aircraft` from one raw ``ac`` entry."""
    alt_ft: float | None = None
    on_ground = False
    alt_baro = raw.get("alt_baro")
    if isinstance(alt_baro, str):
        on_ground = alt_baro == "ground"
    elif isinstance(alt_baro, (int, float)):
        alt_ft = float(alt_baro)

    return Aircraft(
        hex=str(raw.get("hex", "")).strip(),
        callsign=str(raw.get("flight", "")).strip(),
        aircraft_type=str(raw.get("t", "")).strip(),
        alt_ft=alt_ft,
        ground_speed_kt=_as_float(raw.get("gs")),
        track=_as_float(raw.get("track")),
        squawk=str(raw.get("squawk", "")).strip(),
        registration=str(raw.get("r", "")).strip(),
        lat=_as_float(raw.get("lat")) or 0.0,
        lon=_as_float(raw.get("lon")) or 0.0,
        on_ground=on_ground,
    )


def _as_float(value: Any) -> float | None:
    """Best-effort float coercion; ``None`` if not numeric."""
    if isinstance(value, (int, float)):
        return float(value)
    return None


def fetch_nearby(
    lat: float,
    lon: float,
    radius_km: float,
    *,
    source_url: str = API_BASE,
    timeout: float = DEFAULT_TIMEOUT,
    session: requests.Session | None = None,
) -> list[Aircraft]:
    """Fetch aircraft within ``radius_km`` of ``(lat, lon)``.

    ``source_url`` lets a deployment point at a mirror; it defaults to the
    public airplanes.live endpoint. Raises ``requests.HTTPError`` on non-2xx.
    """
    radius_nm = radius_km_to_nm(radius_km)
    url = f"{source_url.rstrip('/')}/v2/point/{lat:.4f}/{lon:.4f}/{radius_nm}"
    getter = session.get if session is not None else requests.get
    resp = getter(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return [_parse_aircraft(a) for a in data.get("ac", [])]
