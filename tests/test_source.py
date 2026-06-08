"""Tests for the airplanes.live source (HTTP mocked, no network)."""

from __future__ import annotations

import responses

from flight_board.source import API_BASE, Aircraft, fetch_nearby, radius_km_to_nm


def test_radius_km_to_nm_rounds_up():
    assert radius_km_to_nm(50) == 27  # 50 / 1.852 = 26.99 -> 27
    assert radius_km_to_nm(1.852) == 1
    assert radius_km_to_nm(0) == 0


@responses.activate
def test_fetch_nearby_parses_records():
    url = f"{API_BASE}/v2/point/50.0000/8.0000/27"
    responses.add(
        responses.GET,
        url,
        json={
            "ac": [
                {
                    "hex": "3c6dd2 ",
                    "flight": "DLH9LH  ",
                    "t": "A320",
                    "alt_baro": 35000,
                    "gs": 451.2,
                    "track": 89.7,
                    "squawk": "1000",
                    "r": "D-AIZZ",
                    "lat": 50.1,
                    "lon": 8.2,
                },
                {
                    "hex": "abc123",
                    "flight": "GND1",
                    "alt_baro": "ground",
                    "lat": 50.0,
                    "lon": 8.0,
                },
            ]
        },
        status=200,
    )

    result = fetch_nearby(50.0, 8.0, 50)

    assert len(result) == 2
    first = result[0]
    assert isinstance(first, Aircraft)
    assert first.hex == "3c6dd2"  # trimmed
    assert first.callsign == "DLH9LH"
    assert first.aircraft_type == "A320"
    assert first.alt_ft == 35000.0
    assert first.ground_speed_kt == 451.2
    assert first.track == 89.7
    assert first.registration == "D-AIZZ"
    assert first.on_ground is False

    grounded = result[1]
    assert grounded.on_ground is True
    assert grounded.alt_ft is None


@responses.activate
def test_fetch_nearby_empty_ac():
    responses.add(
        responses.GET,
        f"{API_BASE}/v2/point/0.0000/0.0000/6",
        json={"ac": []},
        status=200,
    )
    assert fetch_nearby(0.0, 0.0, 10) == []


@responses.activate
def test_fetch_nearby_custom_source_url():
    responses.add(
        responses.GET,
        "https://mirror.example/v2/point/10.0000/20.0000/6",
        json={"ac": []},
        status=200,
    )
    assert fetch_nearby(10.0, 20.0, 10, source_url="https://mirror.example/") == []
