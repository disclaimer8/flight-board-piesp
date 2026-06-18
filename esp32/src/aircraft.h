// Shared aircraft model — Arduino-free so it compiles in the native test env.
// Mirrors the Pi `Aircraft` dataclass.
#pragma once

#include <string>

struct Aircraft {
    std::string hex;
    std::string callsign;
    std::string type;
    std::string registration;

    float altFt = 0.0f;
    bool hasAlt = false;
    float gsKt = 0.0f;
    bool hasGs = false;
    float track = 0.0f;
    bool hasTrack = false;
    bool onGround = false;

    double lat = 0.0;
    double lon = 0.0;
    double distKm = 0.0;      // filled by rankNearest()
    double bearingDeg = 0.0;  // filled by rankNearest() — bearing from observer to aircraft
    bool hasBearing = false;
};
