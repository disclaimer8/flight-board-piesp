// Compile-time configuration for the ESP32 flight board.
// (Pi uses a runtime config.yaml; on ESP32 v1 it's simpler to bake these in.)
// Wi-Fi credentials and observer location live in secrets.h (gitignored).
#pragma once

// ---- Panel geometry ----
#define PANEL_RES_X 128  // columns
#define PANEL_RES_Y 64   // rows
#define PANEL_CHAIN 1    // panels in the chain

// ---- HUB75 -> ESP32 pin map (mrfaptastic default for ESP-WROOM-32) ----
// See docs/hardware.md. Keep leads short (10-15 cm) since the ESP32 drives the
// panel at 3.3 V without a level shifter.
#define PIN_R1 25
#define PIN_G1 26
#define PIN_B1 27
#define PIN_R2 14
#define PIN_G2 12
#define PIN_B2 13
#define PIN_A 23
#define PIN_B 19
#define PIN_C 5
#define PIN_D 17
// E is only used by 1/32-scan panels. A 64-row panel is usually 1/32 scan and
// REQUIRES E — default 32. If yours is 1/16 scan (rare at 64 high), set to -1.
#define PIN_E 32
#define PIN_CLK 16
#define PIN_LAT 4
#define PIN_OE 15

// ---- Display ----
#define BRIGHTNESS 90  // 0-255

// ---- Data source ----
#define DISTANCE_KM 30.0
// Query radius in nautical miles = ceil(DISTANCE_KM / 1.852), same as the Pi.
#define RADIUS_NM ((int)((DISTANCE_KM) / 1.852 + 0.999))
#define TOP_N 8  // rank this many; the layout shows 4 per page

// ---- Timing ----
#define REFRESH_SEC 15  // poll airplanes.live every N seconds
#define ROTATE_SEC 8    // rotate pages when more than 4 aircraft are shown
#define FRAME_MS 50     // redraw cadence (~20 fps) for scrolling callsigns
#define STALE_SEC 45    // mark data stale if no successful poll within N seconds

// ---- Colors (R, G, B) — expanded into panel.color565(...) ----
#define CALLSIGN_RGB 255, 255, 255  // white
#define ALT_RGB 0, 180, 80          // muted green
#define DIST_RGB 255, 170, 0        // amber
#define ERROR_RGB 255, 0, 0         // stale-data dot
