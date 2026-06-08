# Hardware — ESP32

A classic **ESP-WROOM-32 DevKit** (NodeMCU-style, USB-micro) driving a **HUB75
64×128 RGB LED matrix** via
[mrfaptastic ESP32-HUB75-MatrixPanel-DMA](https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA).

See [`../../docs/hardware.md`](../../docs/hardware.md) for the shared panel +
power notes. This doc covers the ESP32-specific wiring.

## Pin map: HUB75 IDC ↔ ESP-WROOM-32

Default mrfaptastic pinout (matches `include/config.h`):

```
HUB75    ESP32 (GPIO)
R1       25
G1       26
B1       27
R2       14
G2       12
B2       13
A        23
B        19
C         5
D        17
E        32   <-- see note
CLK      16
LAT (STB) 4
OE       15
GND      common ground (ESP32 + PSU + panel)
+5V      external 5 V / 4 A PSU — NOT from the ESP32
```

### The E line (scan rate)

A **64-row** panel is almost always **1/32 scan**, which needs the **E** address
line — `config.h` defaults `PIN_E` to **GPIO32**. If your specific panel is
1/16 scan (uncommon at 64 px tall), set `PIN_E` to `-1`. Symptoms of a wrong E
pin: only half the panel lights, or the image is split/doubled. Verify against
your panel's datasheet and adjust `PIN_E` — don't rewire.

## Power & ground (critical)

- The panel gets **5 V / 4 A from an external PSU** through its power injector /
  screw terminals. **Never** power the panel from the ESP32's 5 V/VIN pin.
- The ESP32 is powered separately (USB or its own 5 V).
- **Common ground is mandatory:** ESP32 GND ↔ PSU GND ↔ panel GND must be tied
  together, or the 3.3 V data lines have no reference and the panel glitches.

## Signal levels & wire length

The ESP32 drives HUB75 at **3.3 V** with **no level shifter**. This works on
**short** jumpers (10–15 cm) — keep them short for v1. For longer ribbons add a
**74HCT245** buffer to shift 3.3 V → 5 V logic, or you'll get flicker/ghosting.

## No PSRAM → limited color depth

The classic ESP-WROOM-32 has **no PSRAM**, so the full 24-bit (8-bit-per-channel
binary-coded-modulation, ~24bpp) DMA buffer won't fit alongside Wi-Fi + TLS.
This firmware builds with **`-DPIXEL_COLOR_DEPTH_BITS=6`** (`platformio.ini`),
which is plenty for the few solid UI colors and leaves heap for the HTTPS poll.

- Raise to `8` if you want finer color *and* `panel.begin()` still succeeds.
- If `begin()` logs a failure (out of DMA memory), drop back to `6`, or disable
  `mxconfig.double_buff` in `main.cpp` to halve the buffer.
- A higher color depth also lowers the achievable refresh rate; ~80 Hz minimum
  is comfortable for this static-ish board.
