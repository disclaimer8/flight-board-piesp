"""Tests for frame composition against the MockRenderer."""

from __future__ import annotations

from PIL import Image

from flight_board.layout import Layout, format_row
from flight_board.renderer import MockRenderer
from flight_board.source import Aircraft


def test_format_row_uses_fallbacks():
    ac = Aircraft(hex="abc123")
    row = format_row(ac)
    assert "abc123" in row  # no callsign/reg -> hex fallback
    assert "---" in row  # missing alt/speed/track


def test_format_row_ground():
    ac = Aircraft(callsign="GND1", on_ground=True)
    assert "GND" in format_row(ac)


def test_format_row_airborne():
    ac = Aircraft(callsign="DLH9LH", alt_ft=35000, ground_speed_kt=450, track=90, dist_km=12)
    row = format_row(ac)
    assert "DLH9LH" in row
    assert "FL350" in row
    assert "450kt" in row
    assert "12km" in row
    assert "090" in row


def test_compose_returns_panel_sized_image():
    layout = Layout(128, 64)
    img = layout.compose([Aircraft(callsign="TEST1", dist_km=5)])
    assert isinstance(img, Image.Image)
    assert img.size == (128, 64)


def test_render_pushes_and_swaps():
    layout = Layout(128, 64)
    renderer = MockRenderer(128, 64)
    layout.render(renderer, [Aircraft(callsign="AAA1", dist_km=3)], scroll_offset=0)
    kinds = [c[0] for c in renderer.calls]
    assert kinds == ["set_image", "swap"]
    assert renderer.calls[0][1] == (128, 64)


def test_long_row_scrolls_without_error():
    # A narrow panel forces the row wider than the width -> scroll branch.
    layout = Layout(32, 16)
    renderer = MockRenderer(32, 16)
    long_ac = Aircraft(callsign="VERYLONGCALLSIGN", alt_ft=35000, ground_speed_kt=450, track=90)
    layout.render(renderer, [long_ac], scroll_offset=10)
    assert renderer.calls[0][1] == (32, 16)


def test_compose_caps_rows_to_panel_height():
    layout = Layout(128, 64)
    fleet = [Aircraft(callsign=f"AC{i:03d}", dist_km=i) for i in range(50)]
    # Should not raise even though there are far more aircraft than rows.
    img = layout.compose(fleet)
    assert img.size == (128, 64)
