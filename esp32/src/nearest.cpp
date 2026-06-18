#include "nearest.h"

#include <algorithm>
#include <cmath>

static const double kEarthRadiusKm = 6371.0088;

double haversineKm(double lat1, double lon1, double lat2, double lon2) {
    double rlat1 = lat1 * M_PI / 180.0;
    double rlat2 = lat2 * M_PI / 180.0;
    double dlat = rlat2 - rlat1;
    double dlon = (lon2 - lon1) * M_PI / 180.0;
    double a = std::sin(dlat / 2) * std::sin(dlat / 2) +
               std::cos(rlat1) * std::cos(rlat2) * std::sin(dlon / 2) * std::sin(dlon / 2);
    return 2 * kEarthRadiusKm * std::asin(std::sqrt(a));
}

int radiusKmToNm(double km) {
    return (int)std::ceil(km / 1.852);
}

double bearingDegrees(double lat1, double lon1, double lat2, double lon2) {
    double rlat1 = lat1 * M_PI / 180.0;
    double rlat2 = lat2 * M_PI / 180.0;
    double dlon = (lon2 - lon1) * M_PI / 180.0;
    double y = std::sin(dlon) * std::cos(rlat2);
    double x = std::cos(rlat1) * std::sin(rlat2) -
               std::sin(rlat1) * std::cos(rlat2) * std::cos(dlon);
    return std::fmod(std::atan2(y, x) * 180.0 / M_PI + 360.0, 360.0);
}

void rankNearest(std::vector<Aircraft>& aircraft, double lat, double lon, int topN) {
    aircraft.erase(
        std::remove_if(aircraft.begin(), aircraft.end(),
                       [](const Aircraft& ac) { return ac.onGround; }),
        aircraft.end());
    for (Aircraft& ac : aircraft) {
        ac.distKm = haversineKm(lat, lon, ac.lat, ac.lon);
        ac.bearingDeg = bearingDegrees(lat, lon, ac.lat, ac.lon);
        ac.hasBearing = true;
    }
    std::sort(aircraft.begin(), aircraft.end(),
              [](const Aircraft& a, const Aircraft& b) { return a.distKm < b.distKm; });
    if (topN >= 0 && (int)aircraft.size() > topN) {
        aircraft.resize(topN);
    }
}
