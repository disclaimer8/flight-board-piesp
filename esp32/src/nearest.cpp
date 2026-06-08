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

void rankNearest(std::vector<Aircraft>& aircraft, double lat, double lon, int topN) {
    for (Aircraft& ac : aircraft) {
        ac.distKm = haversineKm(lat, lon, ac.lat, ac.lon);
    }
    std::sort(aircraft.begin(), aircraft.end(),
              [](const Aircraft& a, const Aircraft& b) { return a.distKm < b.distKm; });
    if (topN >= 0 && (int)aircraft.size() > topN) {
        aircraft.resize(topN);
    }
}
