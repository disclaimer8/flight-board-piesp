# Hardware

A single **HUB75 64×128 RGB LED matrix** driven by a **Raspberry Pi Zero W
1.1** (armv6l) via [hzeller/rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix).

## Power

- The panel draws **up to ~4 A @ 5 V** at full white. Use a dedicated
  **5 V / 4 A** supply into the panel's screw terminals — **do not** power the
  panel from the Pi's 5V rail.
- Power the Pi separately (its own 5 V supply / USB). Share a common **ground**
  between the panel PSU and the Pi.
- Brightness in `config.yaml` caps current; start at 60 and raise as your PSU
  allows.

## Wiring: Adafruit Bonnet/HAT vs direct

Two ways to connect HUB75 to the Pi:

| Option | Pros | Notes |
| --- | --- | --- |
| **Adafruit RGB Matrix Bonnet/HAT** (recommended) | Clean, level-shifted, one HUB75 connector, optional PWM-quality mod | Set `hardware_mapping: "adafruit-hat"` (or `"adafruit-hat-pwm"` if you do the GPIO4↔GPIO18 solder bridge for flicker-free output) |
| **Direct GPIO wiring** | No extra board | Fiddly; 3.3 V logic into a 5 V panel works in practice but is out of spec; use `hardware_mapping: "regular"` |

### Direct HUB75 → Pi GPIO (`regular` mapping)

Pin numbers are **physical BCM header** positions for the default `regular`
mapping (single chain, one parallel). This matches the library's wiring guide —
when in doubt, follow
[hzeller's wiring doc](https://github.com/hzeller/rpi-rgb-led-matrix/blob/master/wiring.md).

| HUB75 | Pi GPIO (BCM) | HUB75 | Pi GPIO (BCM) |
| --- | --- | --- | --- |
| R1 | GPIO17 | R2 | GPIO5 |
| G1 | GPIO18 | G2 | GPIO13 |
| B1 | GPIO22 | B2 | GPIO6 |
| A  | GPIO23 | B  | GPIO24 |
| C  | GPIO25 | D  | GPIO15 |
| CLK| GPIO11 | LAT (STB) | GPIO4 |
| OE | GPIO18*| GND | any GND |

\* OE/GPIO18 overlaps with the PWM line used by the `-pwm` mappings; on a
Bonnet this is handled for you.

> **64×128 geometry:** in the config this panel is `rows: 64`, `cols: 128`,
> `chain: 1`. If your specific module is physically two 64×64 tiles chained,
> use `rows: 64`, `cols: 64`, `chain: 2` instead — same pixel count, different
> addressing.

## GPIO needs root

The matrix library programs the Pi's GPIO/DMA directly, which requires
**root** (or `CAP_SYS_NICE`/hardware access). Run via `sudo`, or via the
provided systemd unit which starts at boot. To reduce flicker, the library also
benefits from disabling the on-board sound (`dtparam=audio=off`) and isolating
a CPU core — see the upstream README's "Improving flicker" section.

## Tuning on a Pi Zero W 1.1

- The Zero is slow; keep `gpio_slowdown: 1` or `2`.
- Expect a real ceiling on refresh from the single-core armv6l CPU — keep
  `top_n` modest and `scroll_fps` around 20.
