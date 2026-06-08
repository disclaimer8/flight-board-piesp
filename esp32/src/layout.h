// Frame composition for the 64x128 panel — mirrors pi/src/flight_board/layout.py.
// Four 16 px rows: callsign (white, scrolls if long) left; FLnnn/GND (green) +
// distance (amber) right; an 8-direction heading arrow at the far right.
#pragma once

#include <ESP32-HUB75-MatrixPanel-I2S-DMA.h>

#include <vector>

#include "aircraft.h"

namespace layout {

// Aircraft per page (rows that fit on one screen).
int rows();

// Startup screen shown until the first poll returns.
void drawSplash(MatrixPanel_I2S_DMA& panel, double lat, double lon);

// Draw one page (<= rows() aircraft). scrollOffset advances long callsigns;
// stale draws the red corner dot.
void drawPage(MatrixPanel_I2S_DMA& panel, const std::vector<Aircraft>& page,
              int scrollOffset, bool stale);

}  // namespace layout
