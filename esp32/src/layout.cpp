#include "layout.h"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>

#include "config.h"

namespace layout {

// Adafruit_GFX built-in font: 5x7 glyph in a 6x8 cell.
static const int kCell = 16;
static const int kPageRows = PANEL_RES_Y / kCell;  // 4 at 64 px
static const int kCharW = 6;
static const int kCharH = 8;

// Pixel-art heading arrow per octant (dx, dy from arrow centre; y grows down,
// N is up). Mirrors pi/src/flight_board/layout.py _ARROW_PIXELS.
struct ArrowPoint {
    int8_t dx;
    int8_t dy;
};
static const ArrowPoint kArrowN[] = {
    {0, -4}, {-1, -3}, {0, -3}, {1, -3}, {-2, -2}, {-1, -2}, {0, -2},
    {1, -2}, {2, -2}, {0, -1}, {0, 0}, {0, 1}, {0, 2}};
static const ArrowPoint kArrowNE[] = {
    {2, -4}, {1, -4}, {2, -3}, {3, -3}, {0, -3}, {1, -2},
    {2, -2}, {-1, -2}, {0, -1}, {1, -1}, {-1, 0}};
static const ArrowPoint kArrowE[] = {
    {4, 0}, {3, -1}, {3, 0}, {3, 1}, {2, -2}, {2, -1}, {2, 0},
    {2, 1}, {2, 2}, {1, 0}, {0, 0}, {-1, 0}, {-2, 0}};
static const ArrowPoint kArrowSE[] = {
    {2, 4}, {1, 4}, {2, 3}, {3, 3}, {0, 3}, {1, 2},
    {2, 2}, {-1, 2}, {0, 1}, {1, 1}, {-1, 0}};
static const ArrowPoint kArrowS[] = {
    {0, 4}, {-1, 3}, {0, 3}, {1, 3}, {-2, 2}, {-1, 2}, {0, 2},
    {1, 2}, {2, 2}, {0, 1}, {0, 0}, {0, -1}, {0, -2}};
static const ArrowPoint kArrowSW[] = {
    {-2, 4}, {-1, 4}, {-2, 3}, {-3, 3}, {0, 3}, {-1, 2},
    {-2, 2}, {1, 2}, {0, 1}, {-1, 1}, {1, 0}};
static const ArrowPoint kArrowW[] = {
    {-4, 0}, {-3, -1}, {-3, 0}, {-3, 1}, {-2, -2}, {-2, -1}, {-2, 0},
    {-2, 1}, {-2, 2}, {-1, 0}, {0, 0}, {1, 0}, {2, 0}};
static const ArrowPoint kArrowNW[] = {
    {-2, -4}, {-1, -4}, {-2, -3}, {-3, -3}, {0, -3}, {-1, -2},
    {-2, -2}, {1, -2}, {0, -1}, {-1, -1}, {1, 0}};
static const ArrowPoint* const kArrows[8] = {
    kArrowN, kArrowNE, kArrowE, kArrowSE, kArrowS, kArrowSW, kArrowW, kArrowNW};
static const int kArrowLen[8] = {13, 11, 13, 11, 13, 11, 13, 11};

int rows() { return kPageRows; }

static int octant(double track) {
    int o = (int)(std::fmod(track, 360.0) / 45.0 + 0.5);
    return ((o % 8) + 8) % 8;
}

static std::string altText(const Aircraft& a) {
    if (a.onGround) return "GND";
    if (!a.hasAlt) return "---";
    char b[8];
    snprintf(b, sizeof(b), "FL%03d", (int)std::lround(a.altFt / 100.0));
    return b;
}

static std::string callsignText(const Aircraft& a) {
    if (!a.callsign.empty()) return a.callsign;
    if (!a.registration.empty()) return a.registration;
    if (!a.hex.empty()) return a.hex;
    return "?";
}

static void drawArrow(MatrixPanel_I2S_DMA& p, int cx, int cy, int oct, uint16_t color) {
    for (int i = 0; i < kArrowLen[oct]; i++) {
        p.drawPixel(cx + kArrows[oct][i].dx, cy + kArrows[oct][i].dy, color);
    }
}

void drawSplash(MatrixPanel_I2S_DMA& p, double lat, double lon) {
    p.fillScreen(0);
    p.setTextSize(1);
    p.setTextWrap(false);

    char mid[24];
    snprintf(mid, sizeof(mid), "%.2f,%.2f", lat, lon);
    const char* lines[3] = {"FLIGHT BOARD", mid, "loading..."};
    uint16_t colors[3] = {p.color565(CALLSIGN_RGB), p.color565(ALT_RGB), p.color565(DIST_RGB)};

    const int lineH = 10;
    int top = (PANEL_RES_Y - 3 * lineH) / 2;
    for (int i = 0; i < 3; i++) {
        int w = (int)strlen(lines[i]) * kCharW;
        int x = (PANEL_RES_X - w) / 2;
        if (x < 0) x = 0;
        p.setTextColor(colors[i]);
        p.setCursor(x, top + i * lineH);
        p.print(lines[i]);
    }
}

void drawPage(MatrixPanel_I2S_DMA& p, const std::vector<Aircraft>& page,
              int scrollOffset, bool stale) {
    p.fillScreen(0);
    p.setTextSize(1);
    p.setTextWrap(false);

    uint16_t cCall = p.color565(CALLSIGN_RGB);
    uint16_t cAlt = p.color565(ALT_RGB);
    uint16_t cDist = p.color565(DIST_RGB);
    uint16_t cErr = p.color565(ERROR_RGB);

    int n = (int)page.size();
    if (n > kPageRows) n = kPageRows;
    for (int i = 0; i < n; i++) {
        const Aircraft& a = page[i];
        int top = i * kCell;
        int yText = top + (kCell - kCharH) / 2;

        std::string alt = altText(a);
        char dist[12];
        snprintf(dist, sizeof(dist), "%.0fkm", a.distKm);

        int altW = (int)alt.size() * kCharW;
        int distW = (int)strlen(dist) * kCharW;
        int gap = kCharW;
        bool hasArrow = a.hasBearing || a.hasTrack;
        int arrowW = hasArrow ? 8 : 0;
        int rightW = arrowW + altW + gap + distW;
        int dataX = PANEL_RES_X - rightW;
        int colW = dataX - 1;

        // Callsign (left), scrolling within its column if it overflows.
        std::string cs = callsignText(a);
        int csW = (int)cs.size() * kCharW;
        p.setTextColor(cCall);
        if (csW <= colW) {
            p.setCursor(0, yText);
            p.print(cs.c_str());
        } else {
            int cycle = csW + kCharW;
            int off = ((scrollOffset % cycle) + cycle) % cycle;
            p.setCursor(-off, yText);
            p.print(cs.c_str());
            p.setCursor(-off + cycle, yText);
            p.print(cs.c_str());
            // Erase anything that bled into the data column before drawing it.
            p.fillRect(colW, top, PANEL_RES_X - colW, kCell, 0);
        }

        // Heading arrow (points toward the aircraft), then altitude + distance.
        int x = dataX;
        if (hasArrow) {
            double bearing = a.hasBearing ? a.bearingDeg : a.track;
            drawArrow(p, x + arrowW / 2, top + kCell / 2, octant(bearing), cCall);
            x += arrowW;
        }
        p.setTextColor(cAlt);
        p.setCursor(x, yText);
        p.print(alt.c_str());
        x += altW + gap;
        p.setTextColor(cDist);
        p.setCursor(x, yText);
        p.print(dist);
    }

    if (stale) {
        p.drawPixel(PANEL_RES_X - 1, 0, cErr);
    }
}

}  // namespace layout
