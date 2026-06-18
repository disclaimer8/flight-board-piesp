#include "source.h"

#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>

static std::string trimSpaces(const char* s) {
    if (!s) return "";
    std::string r(s);
    size_t a = r.find_first_not_of(' ');
    if (a == std::string::npos) return "";
    size_t b = r.find_last_not_of(' ');
    return r.substr(a, b - a + 1);
}

bool fetchNearby(double lat, double lon, int radiusNm, std::vector<Aircraft>& out) {
    // airplanes.live forces HTTPS; it's a public read-only endpoint, so we skip
    // cert validation (no pinning for v1), matching the Pi/ESP32-S3 siblings.
    WiFiClientSecure client;
    client.setInsecure();

    char url[128];
    snprintf(url, sizeof(url), "https://api.airplanes.live/v2/point/%.4f/%.4f/%d",
             lat, lon, radiusNm);

    HTTPClient https;
    if (!https.begin(client, url)) {
        Serial.println("[source] https.begin failed");
        return false;
    }
    https.setUserAgent("flight-board-esp32/0.1");
    https.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);  // a 301 must not silently kill polling
    https.setConnectTimeout(8000);
    https.setTimeout(8000);

    int code = https.GET();
    if (code != 200) {
        Serial.printf("[source] GET %s -> %d\n", url, code);
        https.end();
        return false;
    }

    // Filter: keep only the fields we render, so a big response doesn't exhaust
    // the heap. Same shape as the ESP32-S3 sibling's parser.
    JsonDocument filter;
    JsonObject ff = filter["ac"].add<JsonObject>();
    ff["hex"] = true;
    ff["flight"] = true;
    ff["t"] = true;
    ff["r"] = true;
    ff["alt_baro"] = true;
    ff["gs"] = true;
    ff["track"] = true;
    ff["lat"] = true;
    ff["lon"] = true;

    JsonDocument doc;
    DeserializationError err =
        deserializeJson(doc, https.getStream(), DeserializationOption::Filter(filter));
    https.end();
    if (err) {
        Serial.printf("[source] json: %s\n", err.c_str());
        return false;
    }

    std::vector<Aircraft> parsed;
    for (JsonObject o : doc["ac"].as<JsonArray>()) {
        Aircraft a;
        a.hex = trimSpaces(o["hex"] | "");
        a.callsign = trimSpaces(o["flight"] | "");
        a.type = trimSpaces(o["t"] | "");
        a.registration = trimSpaces(o["r"] | "");

        JsonVariant alt = o["alt_baro"];
        if (alt.is<const char*>()) {
            a.onGround = (strcmp(alt.as<const char*>(), "ground") == 0);
        } else if (alt.is<float>()) {
            a.altFt = alt.as<float>();
            a.hasAlt = true;
        }
        if (o["gs"].is<float>()) {
            a.gsKt = o["gs"].as<float>();
            a.hasGs = true;
        }
        if (o["track"].is<float>()) {
            a.track = o["track"].as<float>();
            a.hasTrack = true;
        }
        a.lat = o["lat"] | 0.0;
        a.lon = o["lon"] | 0.0;
        parsed.push_back(a);
    }

    out = std::move(parsed);
    return true;
}
