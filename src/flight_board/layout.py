"""Frame composition: aircraft rows -> PIL image -> renderer.

One text row per aircraft, stacked top to bottom. Rows wider than the panel
scroll horizontally by ``scroll_offset`` pixels (the main loop advances the
offset each frame). All drawing happens off the UI/render path's critical
section: build the image, push it once, swap once.
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from flight_board.renderer import Renderer
from flight_board.source import Aircraft

# Gap (px) between the end of a scrolling row and its wrapped-around repeat.
SCROLL_GAP = 8
TEXT_COLOR = (0, 200, 255)


def _load_font(font_path: str | None) -> ImageFont.ImageFont:
    """Load a BDF/TTF font, falling back to PIL's built-in bitmap font."""
    if font_path:
        try:
            return ImageFont.truetype(font_path)
        except OSError:
            return ImageFont.load(font_path)
    return ImageFont.load_default()


def format_row(ac: Aircraft) -> str:
    """One-line summary for an aircraft: callsign, alt, speed, dist, track."""
    callsign = ac.callsign or ac.registration or ac.hex or "?"
    alt = "GND" if ac.on_ground else (f"FL{round(ac.alt_ft / 100):03d}" if ac.alt_ft else "---")
    speed = f"{round(ac.ground_speed_kt)}kt" if ac.ground_speed_kt else "---"
    dist = f"{ac.dist_km:.0f}km"
    track = f"{round(ac.track):03d}" if ac.track is not None else "---"
    return f"{callsign}  {alt}  {speed}  {dist}  {track}"


class Layout:
    """Renders ranked aircraft onto a :class:`Renderer`."""

    def __init__(self, width: int, height: int, font_path: str | None = None) -> None:
        self.width = width
        self.height = height
        self.font = _load_font(font_path)
        ascent, descent = self.font.getmetrics()
        self.row_height = ascent + descent + 1

    def _text_width(self, draw: ImageDraw.ImageDraw, text: str) -> int:
        return int(draw.textlength(text, font=self.font))

    def compose(self, aircraft: list[Aircraft], scroll_offset: int = 0) -> Image.Image:
        """Build the full frame image for the current aircraft + scroll state."""
        image = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        max_rows = max(1, self.height // self.row_height)
        for i, ac in enumerate(aircraft[:max_rows]):
            text = format_row(ac)
            y = i * self.row_height
            text_w = self._text_width(draw, text)
            if text_w <= self.width:
                draw.text((0, y), text, font=self.font, fill=TEXT_COLOR)
            else:
                # Scroll: shift left by offset modulo one full cycle, drawing a
                # second copy so the row wraps seamlessly.
                cycle = text_w + SCROLL_GAP
                x = -(scroll_offset % cycle)
                draw.text((x, y), text, font=self.font, fill=TEXT_COLOR)
                draw.text((x + cycle, y), text, font=self.font, fill=TEXT_COLOR)
        return image

    def render(
        self,
        renderer: Renderer,
        aircraft: list[Aircraft],
        scroll_offset: int = 0,
    ) -> None:
        """Compose a frame and push+swap it onto ``renderer``."""
        image = self.compose(aircraft, scroll_offset)
        renderer.set_image(image)
        renderer.swap()
