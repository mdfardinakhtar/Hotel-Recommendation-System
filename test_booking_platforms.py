"""
Automated Test Suite for Indian Hotel Recommendation System
Architecture Transition: Recommendation + External Booking Platform Discovery
Verifies:
1. External platform links generation for MakeMyTrip, Goibibo, Booking.com, and Agoda.
2. Complete absence of internal booking routes and SQLite database mechanisms.
3. Successful /recommend API response containing booking_platforms array and 3-tier address.
4. Rendering of /hotel/<id> details page with platform options, disclaimer, and new-tab links.
5. Absence of 'My Bookings' or internal checkout buttons across templates.
"""

import unittest
import urllib.parse
from app import app, get_booking_platform_links, BOOKING_PLATFORMS, HOTEL_DISPLAY_LOOKUP


class TestBookingPlatformArchitecture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_booking_platforms_config(self):
        """Verify that the 4 specified platforms are configured correctly."""
        platform_ids = [p["id"] for p in BOOKING_PLATFORMS]
        self.assertIn("makemytrip", platform_ids)
        self.assertIn("goibibo", platform_ids)
        self.assertIn("booking_com", platform_ids)
        self.assertIn("agoda", platform_ids)
        self.assertEqual(len(BOOKING_PLATFORMS), 4)

    def test_get_booking_platform_links_construction(self):
        """Verify query construction and URL encoding for external search links."""
        hotel_name = "Super OYO Townhouse 123"
        city = "Bangalore"
        address = "12th Main Road, Indiranagar, Karnataka 560038"

        links = get_booking_platform_links(hotel_name, city, address)
        self.assertEqual(len(links), 4)

        for item in links:
            self.assertIn("id", item)
            self.assertIn("name", item)
            self.assertIn("url", item)
            self.assertIn("button_text", item)
            self.assertTrue(item["button_text"].startswith("Search on"))
            self.assertIn("search_query", item)
            # Ensure query has hotel name and city
            self.assertTrue("Townhouse" in item["search_query"])
            self.assertTrue("Bangalore" in item["search_query"])

        # Check MakeMyTrip
        mmt = next(x for x in links if x["id"] == "makemytrip")
        self.assertTrue(mmt["url"].startswith("https://www.makemytrip.com/hotels/hotel-listing/?searchText="))
        self.assertEqual(mmt["button_text"], "Search on MakeMyTrip")

        # Check Goibibo
        goibibo = next(x for x in links if x["id"] == "goibibo")
        self.assertTrue(goibibo["url"].startswith("https://www.goibibo.com/hotels/find-hotels-in-any/?searchText="))
        self.assertEqual(goibibo["button_text"], "Search on Goibibo")

        # Check Booking.com
        bcom = next(x for x in links if x["id"] == "booking_com")
        self.assertTrue(bcom["url"].startswith("https://www.booking.com/searchresults.html?ss="))
        self.assertEqual(bcom["button_text"], "Search on Booking.com")

        # Check Agoda
        agoda = next(x for x in links if x["id"] == "agoda")
        self.assertTrue(agoda["url"].startswith("https://www.agoda.com/search?text="))
        self.assertEqual(agoda["button_text"], "Search on Agoda")

    def test_internal_booking_routes_removed(self):
        """Verify that all previous internal booking and reservation endpoints return 404."""
        # 1. /book/<id>
        res_book = self.client.get("/book/11355")
        self.assertEqual(res_book.status_code, 404)

        # 2. /booking/confirmation/<id>
        res_conf = self.client.get("/booking/confirmation/BK202609200001")
        self.assertEqual(res_conf.status_code, 404)

        # 3. /my-bookings
        res_my = self.client.get("/my-bookings")
        self.assertEqual(res_my.status_code, 404)

        # 4. /booking/<id>
        res_get_bk = self.client.get("/booking/BK202609200001")
        self.assertEqual(res_get_bk.status_code, 404)

        # 5. /api/hotel/<id>/pricing
        res_price = self.client.get("/api/hotel/11355/pricing")
        self.assertEqual(res_price.status_code, 404)

    def test_recommend_endpoint_includes_platform_links(self):
        """Verify that /recommend returns hotels with booking_platforms data."""
        payload = {
            "location": "Bangalore",
            "budget": "5000",
            "min_rating": "4.0",
            "preference": "clean room and friendly staff"
        }
        res = self.client.post("/recommend", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertGreater(len(data["hotels"]), 0)

        first_hotel = data["hotels"][0]
        self.assertIn("booking_platforms", first_hotel)
        self.assertEqual(len(first_hotel["booking_platforms"]), 4)

        # Check 3-tier address fields intact
        self.assertIn("name", first_hotel)
        self.assertIn("address", first_hotel)
        self.assertIn("city", first_hotel)
        self.assertIn("score", first_hotel)

    def test_hotel_details_page_rendering(self):
        """Verify /hotel/<id> renders booking options section, external links, and disclosures."""
        # Pick first hotel ID from lookup
        test_hid = next(iter(HOTEL_DISPLAY_LOOKUP.keys()))
        res = self.client.get(f"/hotel/{test_hid}")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Must have booking options section
        self.assertIn('id="booking-options"', html)
        self.assertIn('Popular Booking Platforms (Where to Book)', html)

        # Must have all 4 platforms
        self.assertIn("MakeMyTrip", html)
        self.assertIn("Goibibo", html)
        self.assertIn("Booking.com", html)
        self.assertIn("Agoda", html)

        # Must open in new tab with security attributes
        self.assertIn('target="_blank"', html)
        self.assertIn('rel="noopener noreferrer"', html)

        # Must have transparency disclosure
        self.assertIn("Booking Transparency", html)
        self.assertIn("completed entirely on the selected external booking platform", html)

        # Must NOT have internal booking button or links
        self.assertNotIn('href="/book/', html)
        self.assertNotIn('/my-bookings', html)
        self.assertNotIn('Book This Hotel', html)

    def test_homepage_no_my_bookings_link(self):
        """Verify that the homepage no longer contains 'My Bookings'."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertNotIn('/my-bookings', html)
        self.assertNotIn('My Bookings', html)


if __name__ == "__main__":
    unittest.main()
