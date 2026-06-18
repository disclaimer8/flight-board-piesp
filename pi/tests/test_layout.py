"""Tests for the 64x128 layout: rows, pagination/rotation, scroll, splash."""

from __future__ import annotations

from PIL import Image, ImageDraw

from flight_board.layout import (
    Layout,
    alt_str,
    format_row,
    heading_octant,
    octant_label,
    paginate,
    select_page,
)
from flight_board.renderer import MockRenderer
from flight_board.source import Aircraft

W, H = 128, 64


def mk_layout(**kw) -> Layout:
    kw.setdefault("font_main", "5x8.bdf")
    kw.setdefault("font_compact", "tom-thumb.bdf")
    return Layout(W, H, **kw)


def lit_rows(image: Image.Image) -> int:
    """Count 16px row-bands that contain at least one lit pixel."""
    gray = image.convert("L").load()
    count = 0
    for band in range(image.height // 16):
        y0 = band * 16
        if any(gray[x, y] for x in range(image.width) for y in range(y0, y0 + 16)):
            count += 1
    return count


# ---- pure heading helpers ----

def test_heading_octant_boundaries():
    assert heading_octant(0) == 0      # N
    assert heading_octant(90) == 2     # E
    assert heading_octant(180) == 4    # S
    assert heading_octant(270) == 6    # W
    assert heading_octant(360) == 0    # wraps
    assert heading_octant(44) == 1     # NE


def test_octant_label():
    assert octant_label(0) == "N"
    assert octant_label(45) == "NE"
    assert octant_label(315) == "NW"


def test_alt_str():
    assert alt_str(Aircraft(alt_ft=35000)) == "FL350"
    assert alt_str(Aircraft(on_ground=True)) == "GND"
    assert alt_str(Aircraft()) == "---"


def test_format_row_fallbacks_and_fields():
    assert "abc123" in format_row(Aircraft(hex="abc123"))  # hex fallback
    ac = Aircraft(callsign="DLH9LH", alt_ft=35000, ground_speed_kt=450, track=90, dist_km=12)
    row = format_row(ac)
    assert "DLH9LH" in row and "FL350" in row and "450kt" in row and "12km" in row and "E" in row


# ---- pagination / rotation ----

def test_paginate_counts():
    fleet = [Aircraft(hex=f"{i:06x}") for i in range(6)]
    pages = paginate(fleet, per_page=4)
    assert [len(p) for p in pages] == [4, 2]


def test_paginate_empty():
    assert paginate([]) == [[]]


def test_select_page_rotates_and_wraps():
    fleet = [Aircraft(hex=f"{i:06x}") for i in range(6)]
    assert len(select_page(fleet, 0, 4)) == 4
    assert len(select_page(fleet, 1, 4)) == 2
    # Page index 2 wraps back to page 0.
    assert [a.hex for a in select_page(fleet, 2, 4)] == [a.hex for a in select_page(fleet, 0, 4)]


# ---- composition: cell counts ----

def test_compose_zero_aircraft_is_empty():
    img = mk_layout().compose([])
    assert img.size == (W, H)
    assert lit_rows(img) == 0


def test_compose_one_aircraft_one_row():
    page = [Aircraft(callsign="BAW1", alt_ft=35000, track=90, dist_km=5)]
    assert lit_rows(mk_layout().compose(page)) == 1


def test_compact_list_draws_position_arrow_from_bearing(monkeypatch):
    layout = mk_layout()
    calls = []

    def record_arrow(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(layout, "_draw_arrow", record_arrow)

    layout.compose([Aircraft(callsign="BAW1", alt_ft=35000, track=270, bearing_deg=90, dist_km=5)])

    assert len(calls) == 1
    assert calls[0][1]["octant"] == 2


def test_north_arrow_has_wide_head():
    image = Image.new("RGB", (11, 11), (0, 0, 0))
    layout = mk_layout()
    layout._draw_arrow(ImageDraw.Draw(image), 5, 5, 0, (255, 255, 255))

    for x in range(3, 8):
        assert image.getpixel((x, 3)) == (255, 255, 255)
    for y in range(4, 8):
        assert image.getpixel((5, y)) == (255, 255, 255)


def test_compose_four_aircraft_four_rows():
    page = [Aircraft(callsign=f"AC{i}", alt_ft=10000 * (i + 1), track=i * 45, dist_km=i + 1)
            for i in range(4)]
    assert lit_rows(mk_layout().compose(page)) == 4


def test_six_aircraft_rotate_across_two_pages():
    fleet = [Aircraft(callsign=f"AC{i:02d}", alt_ft=10000, track=i * 30, dist_km=i + 1)
             for i in range(6)]
    layout = mk_layout()
    page0 = select_page(fleet, 0, layout.rows)
    page1 = select_page(fleet, 1, layout.rows)
    assert lit_rows(layout.compose(page0)) == 4
    assert lit_rows(layout.compose(page1)) == 2


# ---- scrolling ----

def test_long_callsign_scrolls_between_frames():
    layout = mk_layout()
    renderer = MockRenderer(W, H)
    long_ac = Aircraft(callsign="VERYLONGCALLSIGN123", alt_ft=35000, track=90, dist_km=5)
    layout.render(renderer, [long_ac], scroll_offset=0)
    layout.render(renderer, [long_ac], scroll_offset=40)
    # Both frames captured at panel size, but pixels differ because the
    # callsign column scrolled.
    assert [c[0] for c in renderer.calls] == ["set_image", "swap", "set_image", "swap"]
    assert renderer.images[0].size == (W, H)
    assert renderer.images[0].tobytes() != renderer.images[1].tobytes()


def test_short_callsign_does_not_scroll():
    layout = mk_layout()
    short = Aircraft(callsign="BA1", alt_ft=35000, track=90, dist_km=5)
    a = layout.compose([short], scroll_offset=0)
    b = layout.compose([short], scroll_offset=40)
    assert a.tobytes() == b.tobytes()


# ---- splash + stale indicator ----

def test_splash_renders_content():
    img = mk_layout().compose_splash(50.11, 8.68, "loading...")
    assert img.size == (W, H)
    assert lit_rows(img) > 0


def test_stale_indicator_dot():
    layout = mk_layout()
    page = [Aircraft(callsign="BAW1", alt_ft=35000, track=90, dist_km=5)]
    clean = layout.compose(page, stale=False)
    stale = layout.compose(page, stale=True)
    assert clean.getpixel((W - 1, 0)) == (0, 0, 0)
    assert stale.getpixel((W - 1, 0)) == (255, 0, 0)


def test_stale_indicator_can_be_disabled():
    layout = mk_layout(error_indicator=False)
    page = [Aircraft(callsign="BAW1", alt_ft=35000, track=90, dist_km=5)]
    assert layout.compose(page, stale=True).getpixel((W - 1, 0)) == (0, 0, 0)


def test_render_pushes_and_swaps():
    renderer = MockRenderer(W, H)
    mk_layout().render(renderer, [Aircraft(callsign="AAA1", track=90, dist_km=3)])
    assert [c[0] for c in renderer.calls] == ["set_image", "swap"]
    assert renderer.calls[0][1] == (W, H)
