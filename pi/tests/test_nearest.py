"""Tests for haversine distance and top-N ranking (pure math)."""

from __future__ import annotations

import math

from flight_board.nearest import bearing_degrees, haversine_km, nearest
from flight_board.source import Aircraft


def test_haversine_zero_distance():
    assert haversine_km(50.0, 8.0, 50.0, 8.0) == 0.0


def test_haversine_known_distance():
    # ~111 km per degree of latitude near the equator.
    d = haversine_km(0.0, 0.0, 1.0, 0.0)
    assert math.isclose(d, 111.19, abs_tol=0.5)


def test_haversine_symmetric():
    a = haversine_km(48.0, 2.0, 51.0, -0.1)
    b = haversine_km(51.0, -0.1, 48.0, 2.0)
    assert math.isclose(a, b, rel_tol=1e-9)


def test_bearing_degrees_cardinal_directions():
    assert math.isclose(bearing_degrees(0.0, 0.0, 1.0, 0.0), 0.0, abs_tol=0.1)
    assert math.isclose(bearing_degrees(0.0, 0.0, 0.0, 1.0), 90.0, abs_tol=0.1)
    assert math.isclose(bearing_degrees(0.0, 0.0, -1.0, 0.0), 180.0, abs_tol=0.1)
    assert math.isclose(bearing_degrees(0.0, 0.0, 0.0, -1.0), 270.0, abs_tol=0.1)


def _ac(lat: float, lon: float, hex_: str) -> Aircraft:
    return Aircraft(hex=hex_, lat=lat, lon=lon)


def test_nearest_sorts_and_caps():
    obs_lat, obs_lon = 50.0, 8.0
    fleet = [
        _ac(52.0, 8.0, "far"),
        _ac(50.1, 8.0, "near"),
        _ac(51.0, 8.0, "mid"),
    ]
    ranked = nearest(fleet, obs_lat, obs_lon, top_n=2)
    assert [a.hex for a in ranked] == ["near", "mid"]
    # Distance is filled in, single source of truth for the sort.
    assert ranked[0].dist_km < ranked[1].dist_km
    assert ranked[0].dist_km > 0
    assert ranked[0].bearing_deg is not None
    assert math.isclose(ranked[0].bearing_deg, 0.0, abs_tol=0.1)


def test_nearest_excludes_aircraft_on_ground():
    obs_lat, obs_lon = 50.0, 8.0
    fleet = [
        Aircraft(hex="ground", lat=50.0, lon=8.0, on_ground=True),
        _ac(50.1, 8.0, "airborne"),
    ]

    ranked = nearest(fleet, obs_lat, obs_lon, top_n=5)

    assert [a.hex for a in ranked] == ["airborne"]


def test_nearest_negative_top_n_returns_all():
    fleet = [_ac(50.1, 8.0, "a"), _ac(52.0, 8.0, "b")]
    ranked = nearest(fleet, 50.0, 8.0, top_n=-1)
    assert len(ranked) == 2


def test_nearest_empty():
    assert nearest([], 50.0, 8.0, top_n=5) == []
