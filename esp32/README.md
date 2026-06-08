# flight-board-piesp — ESP32 (Arduino)

The **ESP-WROOM-32** implementation. Polls
[airplanes.live](https://airplanes.live) for aircraft near a fixed observer,
ranks them by distance, and renders the nearest few on a **HUB75 64×128 RGB LED
matrix** via [mrfaptastic ESP32-HUB75-MatrixPanel-DMA](https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA).
A behavioural mirror of the Pi (Python) version in [`../pi`](../pi).

> Part of a two-implementation repo — see the [root README](../README.md) for
> the Pi-vs-ESP32 overview and shared [panel/power notes](../docs/hardware.md).

## How it works

```
airplanes.live ──fetch──▶ source.cpp ──rank──▶ nearest.cpp ──draw──▶ layout.cpp ──▶ HUB75
  /v2/point        Aircraft[]        top-N haversine        MatrixPanel_I2S_DMA
```

- `src/source.cpp` — HTTPS GET `/v2/point/{lat}/{lon}/{radius_nm}`, streamed
  ArduinoJson parse (field-filtered to fit the no-PSRAM heap).
- `src/nearest.cpp` — haversine + top-N (Arduino-free, host-tested).
- `src/layout.cpp` — 4×16 px rows: callsign (white, scrolls) / `FLnnn`·`GND`
  (green) + distance (amber) / heading arrow. Page rotation + stale-data dot.
- `src/main.cpp` — Wi-Fi connect, panel init, splash, poll/render timers.
- `include/config.h` — compile-time settings (panel, pins, timing, colors).
- `src/secrets.h` — Wi-Fi creds + observer lat/lon (gitignored; copy from
  `secrets.h.example`).

## Build & flash

[PlatformIO](https://platformio.org/) (`brew install platformio` or the VS Code
extension):

```bash
cd esp32
cp src/secrets.h.example src/secrets.h   # then edit Wi-Fi + HOME_LAT/HOME_LON
pio run -e esp32dev                       # compile
pio run -e esp32dev -t upload             # flash (see port note below)
pio device monitor                        # serial @ 115200
```

Flash to a specific port (find it with `pio device list` / `ls /dev/cu.*`):

```bash
pio run -e esp32dev -t upload --upload-port /dev/cu.usbserial-XXXX
```

## Test

Host-side unit tests for the Arduino-free logic (no board needed):

```bash
pio test -e native
```

## Configuration

Edit `include/config.h` (compile-time): `PANEL_RES_X/Y`, `PANEL_CHAIN`, HUB75
`PIN_*`, `BRIGHTNESS`, `DISTANCE_KM` (→ `RADIUS_NM`), `TOP_N`, `REFRESH_SEC`,
`ROTATE_SEC`, `STALE_SEC`, and the `*_RGB` colors. Wi-Fi + location go in
`src/secrets.h`.

## Hardware

ESP-WROOM-32 DevKit + HUB75 64×128 panel + external **5 V / 4 A** PSU, common
ground. Full pin map, the E-line/scan-rate note, and the no-PSRAM color-depth
trade-off: [`docs/hardware.md`](docs/hardware.md).
