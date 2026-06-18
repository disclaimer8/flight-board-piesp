"""Frame composition for a 64x128 HUB75 panel.

Layout: four 16 px rows, one aircraft per row. Per row — callsign on the left
(scrolls horizontally if it overflows its column), altitude + distance on the
right, and a small heading arrow at the far right. More than four aircraft are
split into pages that the main loop rotates between; fewer than four leaves the
trailing rows blank. A 1 px red corner dot marks stale data.

All drawing builds one PIL image off the live canvas, then pushes it once and
swaps once — the panel never sees a half-drawn frame.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from flight_board.renderer import Renderer
from flight_board.source import Aircraft

FONT_DIR = Path(__file__).parent / "fonts"

# Gap (px) between a scrolling row and its wrapped-around repeat.
SCROLL_GAP = 6
CELL_HEIGHT = 16
ROW_GAP = 1  # px of top padding inside each cell

DEFAULT_COLORS = {
    "callsign": (255, 255, 255),
    "alt": (0, 180, 80),       # muted green
    "dist": (255, 170, 0),     # amber
    "error": (255, 0, 0),
}

_OCTANTS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
# Screen-space tip direction per octant (y grows downward, N is up).
_OCTANT_VEC = [
    (0, -1), (1, -1), (1, 0), (1, 1),
    (0, 1), (-1, 1), (-1, 0), (-1, -1),
]
_ARROW_PIXELS = [
    [
        (0, -4), (-1, -3), (0, -3), (1, -3),
        (-2, -2), (-1, -2), (0, -2), (1, -2), (2, -2),
        (0, -1), (0, 0), (0, 1), (0, 2),
    ],
    [
        (2, -4), (1, -4), (2, -3), (3, -3), (0, -3),
        (1, -2), (2, -2), (-1, -2), (0, -1), (1, -1), (-1, 0),
    ],
    [
        (4, 0), (3, -1), (3, 0), (3, 1),
        (2, -2), (2, -1), (2, 0), (2, 1), (2, 2),
        (1, 0), (0, 0), (-1, 0), (-2, 0),
    ],
    [(2, 4), (1, 4), (2, 3), (3, 3), (0, 3), (1, 2), (2, 2), (-1, 2), (0, 1), (1, 1), (-1, 0)],
    [
        (0, 4), (-1, 3), (0, 3), (1, 3),
        (-2, 2), (-1, 2), (0, 2), (1, 2), (2, 2),
        (0, 1), (0, 0), (0, -1), (0, -2),
    ],
    [(-2, 4), (-1, 4), (-2, 3), (-3, 3), (0, 3), (-1, 2), (-2, 2), (1, 2), (0, 1), (-1, 1), (1, 0)],
    [
        (-4, 0), (-3, -1), (-3, 0), (-3, 1),
        (-2, -2), (-2, -1), (-2, 0), (-2, 1), (-2, 2),
        (-1, 0), (0, 0), (1, 0), (2, 0),
    ],
    [
        (-2, -4), (-1, -4), (-2, -3), (-3, -3), (0, -3),
        (-1, -2), (-2, -2), (1, -2), (0, -1), (-1, -1), (1, 0),
    ],
]


def heading_octant(track: float) -> int:
    """Map a track in degrees to one of 8 compass octants (0=N, 1=NE, ...)."""
    return int((track % 360) / 45.0 + 0.5) % 8


def octant_label(track: float) -> str:
    """Two-letter compass label (N/NE/E/...) for a track in degrees."""
    return _OCTANTS[heading_octant(track)]


def paginate(aircraft: list[Aircraft], per_page: int = 4) -> list[list[Aircraft]]:
    """Split aircraft into pages of ``per_page``. Empty input -> one empty page."""
    if not aircraft:
        return [[]]
    return [aircraft[i : i + per_page] for i in range(0, len(aircraft), per_page)]


def select_page(
    aircraft: list[Aircraft],
    page_index: int,
    per_page: int = 4,
) -> list[Aircraft]:
    """Return the page at ``page_index`` (wraps around the available pages)."""
    pages = paginate(aircraft, per_page)
    return pages[page_index % len(pages)]


def _parse_color(value: object, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    """Accept ``[r, g, b]`` or ``"#rrggbb"``; fall back on anything unexpected."""
    if isinstance(value, str) and value.startswith("#") and len(value) == 7:
        return (int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16))
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return (int(value[0]), int(value[1]), int(value[2]))
    return fallback


def _read_pixel_size(path: str) -> int | None:
    """Read PIXEL_SIZE from a BDF header (FreeType needs the exact strike size)."""
    with open(path, encoding="latin-1") as fh:
        for line in fh:
            if line.startswith("PIXEL_SIZE"):
                return int(line.split()[1])
    return None


def load_font(name: str | None) -> ImageFont.ImageFont:
    """Load a font by bundled name or filesystem path.

    Bundled fonts under ``fonts/`` win over an external path. BDF strikes are
    loaded at their native PIXEL_SIZE. Anything that fails falls back to
    Pillow's built-in bitmap font so the board still renders.
    """
    if not name:
        return ImageFont.load_default()

    bundled = FONT_DIR / name
    path = str(bundled) if bundled.is_file() else (name if Path(name).is_file() else None)
    if path is None:
        return ImageFont.load_default()

    size = _read_pixel_size(path) if path.endswith(".bdf") else None
    for candidate in (size, 8, 6, 10):
        if candidate is None:
            continue
        try:
            return ImageFont.truetype(path, candidate)
        except OSError:
            continue
    return ImageFont.load_default()


def alt_str(ac: Aircraft) -> str:
    """Altitude as flight level (``FLnnn``), ``GND``, or ``---`` when unknown."""
    if ac.on_ground:
        return "GND"
    if ac.alt_ft is None:
        return "---"
    return f"FL{round(ac.alt_ft / 100):03d}"


def format_row(ac: Aircraft) -> str:
    """Flat one-line summary (callsign, alt, speed, dist, track) — used by tests/CLI."""
    callsign = ac.callsign or ac.registration or ac.hex or "?"
    speed = f"{round(ac.ground_speed_kt)}kt" if ac.ground_speed_kt else "---"
    track = octant_label(ac.track) if ac.track is not None else "--"
    return f"{callsign}  {alt_str(ac)}  {speed}  {ac.dist_km:.0f}km  {track}"


def frame_to_ascii(image: Image.Image) -> str:
    """Render a frame as ASCII (lit pixel -> '#') for --mock terminal preview."""
    px = image.convert("L").load()
    w, h = image.size
    border = "+" + "-" * w + "+"
    lines = [border]
    for y in range(h):
        row = "".join("#" if px[x, y] else " " for x in range(w))
        lines.append("|" + row + "|")
    lines.append(border)
    return "\n".join(lines)


class Layout:
    """Renders ranked aircraft (one page) onto a :class:`Renderer`."""

    def __init__(
        self,
        width: int,
        height: int,
        *,
        font_main: str | None = None,
        font_compact: str | None = None,
        colors: dict | None = None,
        error_indicator: bool = True,
    ) -> None:
        self.width = width
        self.height = height
        self.font_main = load_font(font_main)
        self.font_compact = load_font(font_compact)
        merged = dict(DEFAULT_COLORS)
        for key in DEFAULT_COLORS:
            if colors and key in colors:
                merged[key] = _parse_color(colors[key], DEFAULT_COLORS[key])
        self.colors = merged
        self.error_indicator = error_indicator
        self.rows = max(1, height // CELL_HEIGHT)

    def _text_width(self, draw: ImageDraw.ImageDraw, text: str, font) -> int:
        return int(draw.textlength(text, font=font))

    def _baseline(self, font, cell_top: int) -> int:
        ascent, descent = font.getmetrics()
        line_h = ascent + descent
        return cell_top + ROW_GAP + max(0, (CELL_HEIGHT - ROW_GAP - line_h) // 2)

    def _draw_arrow(
        self,
        draw: ImageDraw.ImageDraw,
        cx: int,
        cy: int,
        octant: int,
        color: tuple[int, int, int],
        r: int = 3,
    ) -> None:
        del r
        points = [(cx + dx, cy + dy) for dx, dy in _ARROW_PIXELS[octant]]
        draw.point(points, fill=color)

    def _draw_callsign(
        self,
        image: Image.Image,
        text: str,
        cell_top: int,
        col_w: int,
        scroll_offset: int,
    ) -> None:
        col_w = max(1, col_w)
        measure = ImageDraw.Draw(image)
        text_w = self._text_width(measure, text, self.font_main)
        y = self._baseline(self.font_main, cell_top)
        color = self.colors["callsign"]
        if text_w <= col_w:
            measure.text((1, y), text, font=self.font_main, fill=color)
            return
        # Overflowing: render into a clipped column image so the scroll stays put.
        sub = Image.new("RGB", (col_w, CELL_HEIGHT), (0, 0, 0))
        sd = ImageDraw.Draw(sub)
        cycle = text_w + SCROLL_GAP
        sx = -(scroll_offset % cycle)
        sub_y = self._baseline(self.font_main, 0)
        sd.text((sx, sub_y), text, font=self.font_main, fill=color)
        sd.text((sx + cycle, sub_y), text, font=self.font_main, fill=color)
        image.paste(sub, (0, cell_top))

    def compose(
        self,
        page: list[Aircraft],
        scroll_offset: int = 0,
        *,
        stale: bool = False,
    ) -> Image.Image:
        """Build the frame image for one page of (up to ``rows``) aircraft."""
        image = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(image)

        for i, ac in enumerate(page[: self.rows]):
            cell_top = i * CELL_HEIGHT
            y = self._baseline(self.font_compact, cell_top)

            data_alt = alt_str(ac)
            data_dist = f"{ac.dist_km:.0f}km"
            alt_w = self._text_width(draw, data_alt, self.font_compact)
            dist_w = self._text_width(draw, data_dist, self.font_compact)
            arrow_w = 8 if (ac.bearing_deg is not None or ac.track is not None) else 0
            gap = 3
            right_block = arrow_w + alt_w + gap + dist_w
            data_x = self.width - right_block

            callsign = ac.callsign or ac.registration or ac.hex or "?"
            self._draw_callsign(image, callsign, cell_top, data_x - 2, scroll_offset)

            x = data_x
            bearing = ac.bearing_deg if ac.bearing_deg is not None else ac.track
            if bearing is not None:
                self._draw_arrow(
                    draw,
                    cx=x + arrow_w // 2,
                    cy=cell_top + CELL_HEIGHT // 2,
                    octant=heading_octant(bearing),
                    color=self.colors["callsign"],
                )
                x += arrow_w
            draw.text((x, y), data_alt, font=self.font_compact, fill=self.colors["alt"])
            x += alt_w + gap
            draw.text((x, y), data_dist, font=self.font_compact, fill=self.colors["dist"])

        if stale and self.error_indicator:
            draw.point((self.width - 1, 0), fill=self.colors["error"])
        return image

    def compose_splash(self, lat: float, lon: float, message: str = "loading...") -> Image.Image:
        """Startup screen shown until the first data arrives."""
        image = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        lines = ["FLIGHT BOARD", f"{lat:.3f},{lon:.3f}", message]
        colors = [self.colors["callsign"], self.colors["alt"], self.colors["dist"]]
        ascent, descent = self.font_main.getmetrics()
        line_h = ascent + descent + 2
        total = line_h * len(lines)
        top = max(0, (self.height - total) // 2)
        for i, (text, color) in enumerate(zip(lines, colors)):
            w = self._text_width(draw, text, self.font_main)
            x = max(0, (self.width - w) // 2)
            draw.text((x, top + i * line_h), text, font=self.font_main, fill=color)
        return image

    def render(
        self,
        renderer: Renderer,
        page: list[Aircraft],
        scroll_offset: int = 0,
        *,
        stale: bool = False,
    ) -> None:
        """Compose a page and push+swap it onto ``renderer``."""
        renderer.set_image(self.compose(page, scroll_offset, stale=stale))
        renderer.swap()

    def render_splash(self, renderer: Renderer, lat: float, lon: float, message: str) -> None:
        renderer.set_image(self.compose_splash(lat, lon, message))
        renderer.swap()
