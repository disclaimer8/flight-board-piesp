// Distance ranking — haversine + top-N. Arduino-free (host-testable), mirrors
// pi/src/flight_board/nearest.py.
#pragma once

#include <vector>

#include "aircraft.h"

// Great-circle distance in km between two lat/lon points.
double haversineKm(double lat1, double lon1, double lat2, double lon2);

// Query radius in whole nautical miles, rounded up (1 NM = 1.852 km).
int radiusKmToNm(double km);

// Initial bearing in degrees (0-360) from (lat1, lon1) to (lat2, lon2).
double bearingDegrees(double lat1, double lon1, double lat2, double lon2);

// Drop on-ground aircraft, fill distKm + bearingDeg for the rest (single pass),
// sort nearest-first, and cap to topN (topN < 0 keeps all).
void rankNearest(std::vector<Aircraft>& aircraft, double lat, double lon, int topN);
