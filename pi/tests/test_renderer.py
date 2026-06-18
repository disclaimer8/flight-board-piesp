"""Tests for rgbmatrix option construction."""

from __future__ import annotations

import sys
import types

fake_pil = types.SimpleNamespace(Image=object)
sys.modules.setdefault("PIL", fake_pil)

from flight_board.renderer import build_matrix_options  # noqa: E402


class FakeRGBMatrixOptions:
    pass


def install_fake_rgbmatrix(monkeypatch) -> None:
    fake = types.SimpleNamespace(RGBMatrixOptions=FakeRGBMatrixOptions)
    monkeypatch.setitem(sys.modules, "rgbmatrix", fake)


def test_matrix_options_default_to_direct_gpio_mapping(monkeypatch):
    install_fake_rgbmatrix(monkeypatch)

    options = build_matrix_options({})

    assert options.rows == 64
    assert options.cols == 128
    assert options.chain_length == 1
    assert options.parallel == 1
    assert options.hardware_mapping == "regular"
    assert options.led_rgb_sequence == "RGB"


def test_matrix_options_allow_explicit_panel_overrides(monkeypatch):
    install_fake_rgbmatrix(monkeypatch)

    options = build_matrix_options({
        "brightness": 42,
        "gpio_slowdown": 1,
        "pwm_bits": 7,
        "limit_refresh_rate_hz": 120,
        "panel": {
            "rows": 32,
            "cols": 64,
            "chain": 2,
            "parallel": 1,
            "hardware_mapping": "regular",
            "led_rgb_sequence": "RBG",
        },
    })

    assert options.rows == 32
    assert options.cols == 64
    assert options.chain_length == 2
    assert options.brightness == 42
    assert options.gpio_slowdown == 1
    assert options.hardware_mapping == "regular"
    assert options.led_rgb_sequence == "RBG"
    assert options.pwm_bits == 7
    assert options.limit_refresh_rate_hz == 120
