# flight-board-piesp

Two implementations of the **same flight board** — a live display of the nearest
aircraft on a **HUB75 64×128 RGB LED matrix**. Both poll
[airplanes.live](https://airplanes.live) for traffic near a fixed observer,
rank it by distance, and render the closest few (callsign, altitude, distance,
heading) in a 4-row layout with a scrolling callsign and page rotation.

The two share the data model and behaviour but target very different hardware:

| | **Pi** ([`pi/`](pi/)) | **ESP32** ([`esp32/`](esp32/)) |
| --- | --- | --- |
| Controller | Raspberry Pi Zero W 1.1 (armv6l) | ESP-WROOM-32 DevKit |
| OS | Raspberry Pi OS (Linux) | none (bare-metal / Arduino) |
| Language | Python 3.9+ | C++ (Arduino) |
| Build/deploy | `pip` + `scripts/install.sh` | PlatformIO (`pio run -t upload`) |
| Panel driver | [hzeller/rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix) | [mrfaptastic ESP32-HUB75-MatrixPanel-DMA](https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA) |
| JSON | stdlib + `requests` | ArduinoJson (streamed) |
| Wiring | via adapter board (level-shifted) | direct 3.3 V GPIO → HUB75 |
| Config | `config.yaml` (runtime) | `include/config.h` + `secrets.h` (compile-time) |
| Tests / CI | ruff + pytest (`MockRenderer`) | `pio run` compile (+ native unit test) |

Same airplanes.live URL on both: `GET /v2/point/{lat}/{lon}/{radius_nm}` where
`radius_nm = ceil(distance_km / 1.852)`.

## Layout

Four 16 px rows, one aircraft per row: callsign on the left (white, scrolls if
it overflows), altitude (`FLnnn`/`GND`, green) + distance (`Nkm`, amber) on the
right, and a small 8-direction heading arrow. More than four aircraft rotate
across pages; a 1 px red corner dot marks stale data.

## Subprojects

- **[`pi/`](pi/)** — Python implementation. See [`pi/README.md`](pi/README.md).
- **[`esp32/`](esp32/)** — Arduino/PlatformIO firmware. See
  [`esp32/README.md`](esp32/README.md).

## Hardware

Both drive the same 64×128 HUB75 panel from a dedicated **5 V / 4 A** supply
with a **common ground**. Shared panel/power notes:
[`docs/hardware.md`](docs/hardware.md). Controller-specific wiring:
[`pi/docs/hardware.md`](pi/docs/hardware.md),
[`esp32/docs/hardware.md`](esp32/docs/hardware.md).

## License

Not yet chosen — add a `LICENSE` of your choice.
