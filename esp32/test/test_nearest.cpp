// Host-side unit tests for the Arduino-free ranking logic (env:native).
//   pio test -e native
#include <unity.h>

#include <cmath>
#include <vector>

#include "nearest.h"

void setUp() {}
void tearDown() {}

static Aircraft at(double lat, double lon, const char* hex) {
    Aircraft a;
    a.lat = lat;
    a.lon = lon;
    a.hex = hex;
    return a;
}

void test_radius_km_to_nm_rounds_up() {
    TEST_ASSERT_EQUAL_INT(27, radiusKmToNm(50));      // 26.99 -> 27
    TEST_ASSERT_EQUAL_INT(1, radiusKmToNm(1.852));
    TEST_ASSERT_EQUAL_INT(0, radiusKmToNm(0));
}

void test_haversine_zero_distance() {
    TEST_ASSERT_TRUE(haversineKm(50.0, 8.0, 50.0, 8.0) < 1e-9);
}

void test_haversine_known_distance() {
    // ~111 km per degree of latitude.
    double d = haversineKm(0.0, 0.0, 1.0, 0.0);
    TEST_ASSERT_TRUE(std::fabs(d - 111.19) < 0.5);
}

void test_haversine_symmetric() {
    double a = haversineKm(48.0, 2.0, 51.0, -0.1);
    double b = haversineKm(51.0, -0.1, 48.0, 2.0);
    TEST_ASSERT_TRUE(std::fabs(a - b) < 1e-9);
}

void test_rank_sorts_and_caps() {
    std::vector<Aircraft> fleet = {
        at(52.0, 8.0, "far"),
        at(50.1, 8.0, "near"),
        at(51.0, 8.0, "mid"),
    };
    rankNearest(fleet, 50.0, 8.0, 2);
    TEST_ASSERT_EQUAL_INT(2, (int)fleet.size());
    TEST_ASSERT_EQUAL_STRING("near", fleet[0].hex.c_str());
    TEST_ASSERT_EQUAL_STRING("mid", fleet[1].hex.c_str());
    TEST_ASSERT_TRUE(fleet[0].distKm < fleet[1].distKm);
    TEST_ASSERT_TRUE(fleet[0].distKm > 0.0);
}

void test_rank_negative_topn_keeps_all() {
    std::vector<Aircraft> fleet = {at(50.1, 8.0, "a"), at(52.0, 8.0, "b")};
    rankNearest(fleet, 50.0, 8.0, -1);
    TEST_ASSERT_EQUAL_INT(2, (int)fleet.size());
}

int main(int, char**) {
    UNITY_BEGIN();
    RUN_TEST(test_radius_km_to_nm_rounds_up);
    RUN_TEST(test_haversine_zero_distance);
    RUN_TEST(test_haversine_known_distance);
    RUN_TEST(test_haversine_symmetric);
    RUN_TEST(test_rank_sorts_and_caps);
    RUN_TEST(test_rank_negative_topn_keeps_all);
    return UNITY_END();
}
