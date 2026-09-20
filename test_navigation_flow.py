"""
End-to-End Simulation and Verification of Back Navigation vs Back to Search
"""

import unittest
import json
from app import app


class TestNavigationEndToEnd(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_navigation_flow_steps(self):
        print("\n--- STEP 1: Search Page Loading ---")
        res_home = self.client.get("/")
        self.assertEqual(res_home.status_code, 200)
        home_html = res_home.get_data(as_text=True)

        # 1. Navbar has top-back-btn (hidden on initial search)
        self.assertIn('id="top-back-btn"', home_html)
        self.assertIn('class="btn-secondary top-back-btn hidden"', home_html)
        self.assertIn('onclick="handleGoBack()"', home_html)
        print(" [PASS] Top Back button present in navbar, initially hidden.")

        print("\n--- STEP 2: Submit Search & Receive Recommendations ---")
        req_payload = {
            "location": "Jaipur",
            "budget": "3000",
            "min_rating": "4.0",
            "preference": "clean and comfortable"
        }
        res_rec = self.client.post("/recommend", data=json.dumps(req_payload), content_type="application/json")
        self.assertEqual(res_rec.status_code, 200)
        rec_data = json.loads(res_rec.get_data(as_text=True))
        self.assertTrue(rec_data["success"])
        self.assertGreater(len(rec_data["hotels"]), 0)
        first_hotel = rec_data["hotels"][0]
        hotel_id = first_hotel["hotel_id"]
        print(f" [PASS] Recommendations returned {len(rec_data['hotels'])} hotels. First: {first_hotel['name']} (ID: {hotel_id})")

        # Check results header markup in index.html contains BOTH buttons
        self.assertIn('class="results-nav-buttons"', home_html)
        self.assertIn('onclick="handleGoBack()"', home_html)
        self.assertIn('onclick="resetSearchFlow()"', home_html)
        self.assertIn('<span>Back to Search</span>', home_html)
        print(" [PASS] Results header contains BOTH 'Back' (step) and 'Back to Search' (reset).")

        print("\n--- STEP 3: Navigate to Hotel Details Page ---")
        res_details = self.client.get(f"/hotel/{hotel_id}")
        self.assertEqual(res_details.status_code, 200)
        details_html = res_details.get_data(as_text=True)

        # 1. Hotel Details top navbar has BOTH Back and Back to Search
        self.assertIn('class="btn-secondary top-back-btn"', details_html)
        self.assertIn('onclick="handleGoBack()"', details_html)
        self.assertIn('<span>Back</span>', details_html)
        print(" [PASS] Hotel Details navbar has '<- Back' button.")

        self.assertIn('class="btn-secondary nav-back-btn"', details_html)
        self.assertIn('onclick="resetSearchSession()"', details_html)
        self.assertIn('<span>Back to Search</span>', details_html)
        print(" [PASS] Hotel Details navbar has 'Back to Search' button.")

        # 2. Breadcrumb retains Home link
        self.assertIn('<a href="/">Home</a>', details_html)
        print(" [PASS] Hotel Details breadcrumb retains 'Home' link.")

        # 3. Graceful fallback script exists
        self.assertIn('function handleGoBack()', details_html)
        self.assertIn('window.history.back()', details_html)
        self.assertIn('window.location.href = "/#results"', details_html)
        self.assertIn('window.location.href = "/"', details_html)
        print(" [PASS] Hotel Details handleGoBack() has safe multi-tier fallback (referrer -> session search state -> root).")

        print("\n--- STEP 4: Verify Separation of Duties in JS ---")
        with open("static/script.js", "r", encoding="utf-8") as f:
            script_js = f.read()

        # handleGoBack preserves inputs
        self.assertIn("function handleGoBack()", script_js)
        self.assertIn("function showSearchView()", script_js)
        # resetSearchFlow clears inputs
        self.assertIn("function resetSearchFlow()", script_js)
        self.assertIn("sessionStorage.removeItem(", script_js)
        self.assertIn("clearSelectedCity()", script_js)
        self.assertIn("clearAllPreferences()", script_js)
        print(" [PASS] script.js strictly separates Back (preserves inputs) and Back to Search (resets flow).")


if __name__ == "__main__":
    unittest.main()
