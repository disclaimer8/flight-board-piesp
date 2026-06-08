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

// Screen-space tip direction per octant (y grows downward, N is up).
static const int kVX[8] = {0, 1, 1, 1, 0, -1, -1, -1};
static const int kVY[8] = {-1, -1, 0, 1, 1, 1, 0, -1};

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
    int dx = kVX[oct], dy = kVY[oct], r = 3;
    p.drawLine(cx - dx * r, cy - dy * r, cx + dx * r, cy + dy * r, color);
    // Small arrowhead: two pixels flanking the tip.
    p.drawPixel(cx + dx * r - dx, cy + dy * r, color);
    p.drawPixel(cx + dx * r, cy + dy * r - dy, color);
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
        int arrowW = a.hasTrack ? 9 : 0;
        int rightW = altW + gap + distW + arrowW;
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

        // Altitude + distance (right), then heading arrow.
        int x = dataX;
        p.setTextColor(cAlt);
        p.setCursor(x, yText);
        p.print(alt.c_str());
        x += altW + gap;
        p.setTextColor(cDist);
        p.setCursor(x, yText);
        p.print(dist);
        x += distW;
        if (a.hasTrack) {
            drawArrow(p, x + arrowW / 2, top + kCell / 2, octant(a.track), cCall);
        }
    }

    if (stale) {
        p.drawPixel(PANEL_RES_X - 1, 0, cErr);
    }
}

}  // namespace layout
