# Hardware (shared)

Both implementations drive the **same** display: a single **HUB75 64×128 RGB
LED matrix**. What differs is the controller and how it wires to the panel —
those details live in each subproject's hardware doc:

- **Raspberry Pi (Python):** [`pi/docs/hardware.md`](../pi/docs/hardware.md) —
  Pi Zero W + Electrodragon adapter / Adafruit HAT, GPIO mapping, root/DMA.
- **ESP32 (Arduino):** [`esp32/docs/hardware.md`](../esp32/docs/hardware.md) —
  ESP-WROOM-32 DevKit, HUB75 IDC pin map, color-depth limits without PSRAM.

## The panel

- **64×128 HUB75** RGB matrix. In software this is 64 rows × 128 columns
  (`PANEL_RES_Y=64`, `PANEL_RES_X=128`, one panel in the chain).
- If your specific module is physically two 64×64 tiles chained, configure it as
  two 64×64 panels (`chain = 2`) instead — same pixel count, different
  addressing.

## Power (applies to both)

- The panel can draw **up to ~4 A @ 5 V** at full white. Use a dedicated
  **5 V / 4 A** supply into the panel's 5 V input (screw terminal / power
  injector). **Do not** power the panel from the Pi's or ESP32's 5 V rail — the
  onboard regulator can't supply that current.
- Power the controller (Pi / ESP32) from its own supply.
- **Common ground is mandatory:** the panel PSU, the controller, and any adapter
  board must share a ground reference, or the data lines float and the display
  glitches.
- Cap brightness in config to keep current (and heat) reasonable; raise it only
  as your PSU allows.

## Signal levels

HUB75 expects 5 V logic but tolerates 3.3 V drive on **short** wires. The Pi
adapter board level-shifts for you; the ESP32 direct-wires at 3.3 V — keep those
leads short (10–15 cm) or add a 74HCT245 buffer for long ribbons. See each
subproject doc for specifics.
