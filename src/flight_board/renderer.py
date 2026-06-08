"""Display abstraction over hzeller/rpi-rgb-led-matrix.

The ``rgbmatrix`` binding only exists on the Pi (built via
``scripts/install.sh``), so it is imported lazily inside
:class:`MatrixRenderer`. Tests run on a host with no panel and use
:class:`MockRenderer`, which records every draw call instead of touching
hardware.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from PIL import Image


class Renderer(ABC):
    """Minimal double-buffered display surface.

    Callers draw into a PIL image, push it with :meth:`set_image`, then make
    it visible with :meth:`swap` (paired with the panel's vsync).
    """

    width: int
    height: int

    @abstractmethod
    def set_image(self, image: Image.Image) -> None:
        """Stage ``image`` onto the off-screen canvas."""

    @abstractmethod
    def swap(self) -> None:
        """Make the staged canvas visible."""

    @abstractmethod
    def clear(self) -> None:
        """Blank the off-screen canvas."""


def build_matrix_options(config: dict[str, Any]) -> Any:
    """Build ``RGBMatrixOptions`` from a parsed config ``panel`` block.

    Imported lazily so this module stays importable without the binding.
    """
    from rgbmatrix import RGBMatrixOptions  # noqa: PLC0415 (hardware-only dep)

    panel = config.get("panel", {})
    options = RGBMatrixOptions()
    options.rows = int(panel.get("rows", 64))
    options.cols = int(panel.get("cols", 128))
    options.chain_length = int(panel.get("chain", 1))
    options.parallel = int(panel.get("parallel", 1))
    options.brightness = int(config.get("brightness", 60))
    options.gpio_slowdown = int(config.get("gpio_slowdown", 2))
    options.hardware_mapping = str(panel.get("hardware_mapping", "regular"))
    options.drop_privileges = False
    return options


class MatrixRenderer(Renderer):
    """Real HUB75 renderer backed by ``rgbmatrix.RGBMatrix``."""

    def __init__(self, config: dict[str, Any]) -> None:
        from rgbmatrix import RGBMatrix  # noqa: PLC0415 (hardware-only dep)

        options = build_matrix_options(config)
        self._matrix = RGBMatrix(options=options)
        self._canvas = self._matrix.CreateFrameCanvas()
        self.width = self._matrix.width
        self.height = self._matrix.height

    def set_image(self, image: Image.Image) -> None:
        self._canvas.SetImage(image.convert("RGB"))

    def swap(self) -> None:
        self._canvas = self._matrix.SwapOnVSync(self._canvas)

    def clear(self) -> None:
        self._canvas.Clear()


class MockRenderer(Renderer):
    """Host-side renderer that records draw calls for assertions in tests."""

    def __init__(self, width: int = 128, height: int = 64) -> None:
        self.width = width
        self.height = height
        self.calls: list[tuple[str, Any]] = []

    def set_image(self, image: Image.Image) -> None:
        self.calls.append(("set_image", image.size))

    def swap(self) -> None:
        self.calls.append(("swap", None))

    def clear(self) -> None:
        self.calls.append(("clear", None))
