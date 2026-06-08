// airplanes.live data source over HTTPS. Mirrors pi/src/flight_board/source.py:
// GET /v2/point/{lat}/{lon}/{radius_nm}, parsing the "ac" array.
#pragma once

#include <vector>

#include "aircraft.h"

// Fetch aircraft within radiusNm of (lat, lon) into `out`. Returns true on a
// successful 200 + parse; leaves `out` untouched and returns false otherwise
// (caller keeps showing the previous frame). Uses streamed ArduinoJson with a
// field filter to stay within the WROOM-32's heap.
bool fetchNearby(double lat, double lon, int radiusNm, std::vector<Aircraft>& out);
