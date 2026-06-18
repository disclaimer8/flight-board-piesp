#include <Arduino.h>
#include <ESP32-HUB75-MatrixPanel-I2S-DMA.h>
#include <WiFi.h>

#include <vector>
#include <cstring>

#include "config.h"
#include "layout.h"
#include "nearest.h"
#include "secrets.h"
#include "source.h"

static MatrixPanel_I2S_DMA* panel = nullptr;
static std::vector<Aircraft> g_aircraft;

static unsigned long g_lastPoll = 0;
static unsigned long g_lastFrame = 0;
static unsigned long g_lastRotate = 0;
static unsigned long g_lastSuccess = 0;
static int g_pageIndex = 0;
static int g_scrollOffset = 0;
static bool g_haveData = false;
static int g_consecutiveFails = 0;          // reboot after too many poll failures
static const int MAX_CONSECUTIVE_FAILS = 20;
static std::vector<Aircraft> g_pageCache;   // current page, rebuilt only on change
static bool g_pageDirty = true;             // E-H3: avoid copying a vector every frame

static void connectWifi() {
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);   // auto-recover after a router reboot / drop
    WiFi.persistent(true);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.printf("[wifi] connecting to %s", WIFI_SSID);
    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) {
        delay(1000);
        Serial.print(".");
    }
    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf(" ok, ip=%s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println(" FAILED (will keep retrying on poll)");
    }
}

void setup() {
    Serial.begin(115200);
    delay(200);
    Serial.println("\n[flight-board-esp32] boot");

    // Resolve color channel pin mapping based on COLOR_ORDER configuration
    int8_t r1 = PIN_R1, g1 = PIN_G1, b1 = PIN_B1;
    int8_t r2 = PIN_R2, g2 = PIN_G2, b2 = PIN_B2;

    if (strcmp(COLOR_ORDER, "RBG") == 0) {
        g1 = PIN_B1; b1 = PIN_G1;
        g2 = PIN_B2; b2 = PIN_G2;
    } else if (strcmp(COLOR_ORDER, "BGR") == 0) {
        r1 = PIN_B1; b1 = PIN_R1;
        r2 = PIN_B2; b2 = PIN_R2;
    } else if (strcmp(COLOR_ORDER, "GRB") == 0) {
        r1 = PIN_G1; g1 = PIN_R1;
        r2 = PIN_G2; g2 = PIN_R2;
    } else if (strcmp(COLOR_ORDER, "GBR") == 0) {
        r1 = PIN_B1; g1 = PIN_R1; b1 = PIN_G1;
        r2 = PIN_B2; g2 = PIN_R2; b2 = PIN_G2;
    } else if (strcmp(COLOR_ORDER, "BRG") == 0) {
        r1 = PIN_G1; g1 = PIN_B1; b1 = PIN_R1;
        r2 = PIN_G2; g2 = PIN_B2; b2 = PIN_R2;
    }

    HUB75_I2S_CFG::i2s_pins pins = {
        r1, g1, b1, r2, g2, b2,
        PIN_A,  PIN_B,  PIN_C,  PIN_D,  PIN_E,  PIN_LAT, PIN_OE, PIN_CLK};
    HUB75_I2S_CFG mxconfig(PANEL_RES_X, PANEL_RES_Y, PANEL_CHAIN, pins);
    mxconfig.double_buff = true;  // tear-free: draw to back buffer, then flip

    panel = new MatrixPanel_I2S_DMA(mxconfig);
    if (!panel->begin()) {
        // DMA buffers were not allocated; every subsequent panel-> draw would
        // write into null/garbage (crash). Don't drive a dead panel — reboot and
        // retry rather than loop forever on an uninitialized framebuffer.
        Serial.println("[panel] begin() FAILED — out of DMA memory? lower "
                       "PIXEL_COLOR_DEPTH_BITS or disable double_buff. Restarting.");
        delay(2000);
        ESP.restart();
    }
    panel->setBrightness8(BRIGHTNESS);
    panel->clearScreen();

    layout::drawSplash(*panel, HOME_LAT, HOME_LON);
    panel->flipDMABuffer();

    connectWifi();
}

static void pollNow() {
    std::vector<Aircraft> fresh;
    if (WiFi.status() == WL_CONNECTED &&
        fetchNearby(HOME_LAT, HOME_LON, radiusKmToNm(DISTANCE_KM), fresh)) {
        rankNearest(fresh, HOME_LAT, HOME_LON, TOP_N);
        g_aircraft = std::move(fresh);
        g_haveData = true;
        g_pageDirty = true;
        g_lastSuccess = millis();
        g_consecutiveFails = 0;
        Serial.printf("[poll] %d aircraft, heap=%u (min %u)\n", (int)g_aircraft.size(),
                      (unsigned)ESP.getFreeHeap(), (unsigned)ESP.getMinFreeHeap());
    } else {
        // Network error / no link: keep the previous frame, show stale dot.
        // After a long run of failures (wedged Wi-Fi/heap) reboot to recover.
        if (++g_consecutiveFails >= MAX_CONSECUTIVE_FAILS) {
            Serial.println("[poll] too many failures; restarting");
            delay(500);
            ESP.restart();
        }
        Serial.printf("[poll] failed (%d); keeping last frame\n", g_consecutiveFails);
    }
}

static std::vector<Aircraft> currentPage() {
    int per = layout::rows();
    int total = (int)g_aircraft.size();
    int npages = (total + per - 1) / per;
    if (npages < 1) npages = 1;
    int pi = ((g_pageIndex % npages) + npages) % npages;
    int begin = pi * per;
    int end = begin + per;
    if (end > total) end = total;
    std::vector<Aircraft> page;
    for (int i = begin; i < end; i++) page.push_back(g_aircraft[i]);
    return page;
}

void loop() {
    unsigned long now = millis();

    if (g_lastPoll == 0 || now - g_lastPoll >= (unsigned long)REFRESH_SEC * 1000UL) {
        g_lastPoll = now;
        pollNow();
    }

    if (now - g_lastRotate >= (unsigned long)ROTATE_SEC * 1000UL) {
        g_lastRotate = now;
        g_pageIndex++;
        g_pageDirty = true;
    }

    if (now - g_lastFrame >= (unsigned long)FRAME_MS) {
        g_lastFrame = now;
        if (!g_haveData) {
            layout::drawSplash(*panel, HOME_LAT, HOME_LON);
        } else {
            // Rebuild the page slice only when data or the page index changes —
            // not every frame (per-frame vector+string copy churns the heap).
            if (g_pageDirty) {
                g_pageCache = currentPage();
                g_pageDirty = false;
            }
            bool stale = (now - g_lastSuccess) > (unsigned long)STALE_SEC * 1000UL;
            layout::drawPage(*panel, g_pageCache, g_scrollOffset, stale);
            g_scrollOffset++;
        }
        panel->flipDMABuffer();
    }
}
