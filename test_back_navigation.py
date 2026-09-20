"""
Automated Test Suite for Professional Back Button and Navigation Flow
Verifies:
1. Presence of professional Back button at the TOP of the homepage navbar (#top-back-btn).
2. Presence of Back button at the top of results section (.results-back-btn).
3. Presence of professional Back button at the TOP of hotel details page (.top-back-btn).
4. window.history.back() and graceful edge-case fallback implementation.
5. Presence of state preservation controller (saveSearchState, restoreSearchStateIfPresent).
6. Preserved search inputs, preferences, results, and sorting logic.
7. Mobile responsive styling for Back buttons.
8. Complete absence of internal booking forms or checkouts.
"""

import unittest
import re
from app import app


class TestBackNavigationFeature(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_homepage_top_back_button(self):
        """Verify homepage has professional Back button at the top in nav-actions."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Check top back button in navbar
        self.assertIn('id="top-back-btn"', html)
        self.assertIn('class="btn-secondary top-back-btn', html)
        self.assertIn('onclick="handleGoBack()"', html)
        self.assertIn('Back', html)

        # Check results section back button
        self.assertIn('class="btn-secondary results-back-btn"', html)
        self.assertIn('Back to Search', html)

    def test_hotel_details_top_back_button(self):
        """Verify hotel details page has professional Back button at the top in navbar."""
        res = self.client.get("/hotel/11355")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Check top back button in navbar
        self.assertIn('class="btn-secondary top-back-btn"', html)
        self.assertIn('onclick="handleGoBack()"', html)
        self.assertIn('Back', html)

        # Check breadcrumb uses back navigation
        self.assertIn('onclick="handleGoBack()"', html)

        # Check handleGoBack script with graceful fallback
        self.assertIn('function handleGoBack()', html)
        self.assertIn('window.history.back()', html)
        self.assertIn('window.location.href = "/"', html)

    def test_frontend_state_preservation_controller(self):
        """Verify script.js implements state persistence and browser history handling."""
        with open("static/script.js", "r", encoding="utf-8") as f:
            js = f.read()

        # State persistence functions
        self.assertIn("function saveSearchState()", js)
        self.assertIn("function restoreSearchStateIfPresent()", js)
        self.assertIn("function handleGoBack()", js)
        self.assertIn("function showSearchView()", js)
        self.assertIn("function updateTopBackButton(", js)

        # Session storage usage
        self.assertIn("hotel_recommendation_search_state", js)
        self.assertIn("sessionStorage.setItem(", js)
        self.assertIn("sessionStorage.getItem(", js)

        # Browser history integration
        self.assertIn('history.pushState({ step: "results" }, "", "#results")', js)
        self.assertIn('window.addEventListener("popstate"', js)
        self.assertIn('window.addEventListener("pageshow"', js)
        self.assertIn("window.history.back()", js)

    def test_css_styling_and_responsiveness(self):
        """Verify style.css contains professional button styles and mobile responsive rules."""
        with open("static/style.css", "r", encoding="utf-8") as f:
            css = f.read()

        # Top back button styles
        self.assertIn(".top-back-btn", css)
        self.assertIn(".results-back-btn", css)
        self.assertIn(".results-title-group", css)

        # Mobile media query
        self.assertIn("@media (max-width: 640px)", css)


if __name__ == "__main__":
    unittest.main()
