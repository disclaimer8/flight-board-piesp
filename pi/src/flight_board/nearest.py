"""Distance ranking: haversine + top-N nearest, single pass."""

from __future__ import annotations

import math

from flight_board.source import Aircraft

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres between two lat/lon points."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = rlat2 - rlat1
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing from ``(lat1, lon1)`` to ``(lat2, lon2)`` in degrees."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(rlat2)
    x = math.cos(rlat1) * math.sin(rlat2) - math.sin(rlat1) * math.cos(rlat2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def nearest(
    aircraft: list[Aircraft],
    lat: float,
    lon: float,
    top_n: int,
) -> list[Aircraft]:
    """Return the ``top_n`` aircraft closest to ``(lat, lon)``.

    Distance is computed exactly once per aircraft (single pass), stored on
    ``dist_km``, and the sort key reuses that value rather than recomputing.
    """
    airborne = [ac for ac in aircraft if not ac.on_ground]
    for ac in airborne:
        ac.dist_km = haversine_km(lat, lon, ac.lat, ac.lon)
        ac.bearing_deg = bearing_degrees(lat, lon, ac.lat, ac.lon)
    ranked = sorted(airborne, key=lambda ac: ac.dist_km)
    if top_n < 0:
        return ranked
    return ranked[:top_n]
