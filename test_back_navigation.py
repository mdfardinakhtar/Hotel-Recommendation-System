"""
Automated Test Suite for Professional Back Button and Navigation Flow
Verifies:
1. Presence of professional Back button at the TOP of the homepage navbar (#top-back-btn).
2. Presence of BOTH "Back" (one step) and "Back to Search" (reset) in recommendation results header.
3. Presence of BOTH "Back" and "Back to Search" at the TOP of hotel details page navbar.
4. Preserved Home breadcrumb link on hotel details page.
5. window.history.back() and graceful edge-case fallback implementation.
6. Distinct actions: handleGoBack() preserves state vs resetSearchFlow() resets state.
7. Presence of state preservation controller (saveSearchState, restoreSearchStateIfPresent).
8. Mobile responsive styling for all Back navigation buttons.
"""

import unittest
from app import app


class TestBackNavigationFeature(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_homepage_top_back_button(self):
        """Verify homepage has professional Back button at the top and results header has both buttons."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Check top back button in navbar
        self.assertIn('id="top-back-btn"', html)
        self.assertIn('class="btn-secondary top-back-btn hidden"', html)
        self.assertIn('onclick="handleGoBack()"', html)
        self.assertIn('<span>Back</span>', html)

        # Check results section has both Back (one step) and Back to Search (reset)
        self.assertIn('class="results-nav-buttons"', html)
        self.assertIn('onclick="handleGoBack()"', html)
        self.assertIn('onclick="resetSearchFlow()"', html)
        self.assertIn('<span>Back to Search</span>', html)

    def test_hotel_details_top_back_button(self):
        """Verify hotel details page has BOTH Back and Back to Search buttons at the top in navbar."""
        res = self.client.get("/hotel/11355")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Check top back button in navbar (one step back)
        self.assertIn('class="btn-secondary top-back-btn"', html)
        self.assertIn('onclick="handleGoBack()"', html)
        self.assertIn('<span>Back</span>', html)

        # Check existing Back to Search button is retained in navbar
        self.assertIn('class="btn-secondary nav-back-btn"', html)
        self.assertIn('href="/"', html)
        self.assertIn('onclick="resetSearchSession()"', html)
        self.assertIn('<span>Back to Search</span>', html)

        # Check breadcrumb retains Home link
        self.assertIn('<a href="/">Home</a>', html)

        # Check handleGoBack script with graceful fallback
        self.assertIn('function handleGoBack()', html)
        self.assertIn('window.history.back()', html)
        self.assertIn('window.location.href = "/"', html)
        self.assertIn('function resetSearchSession()', html)

    def test_frontend_state_preservation_controller(self):
        """Verify script.js implements state persistence, separation of Back vs Reset, and history handling."""
        with open("static/script.js", "r", encoding="utf-8") as f:
            js = f.read()

        # State persistence and navigation functions
        self.assertIn("function saveSearchState()", js)
        self.assertIn("function restoreSearchStateIfPresent()", js)
        self.assertIn("function handleGoBack()", js)
        self.assertIn("function showSearchView()", js)
        self.assertIn("function resetSearchFlow()", js)
        self.assertIn("function updateTopBackButton(", js)

        # Session storage usage
        self.assertIn("hotel_recommendation_search_state", js)
        self.assertIn("sessionStorage.setItem(", js)
        self.assertIn("sessionStorage.getItem(", js)
        self.assertIn("sessionStorage.removeItem(", js)

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
        self.assertIn(".nav-back-btn", css)
        self.assertIn(".results-back-btn", css)
        self.assertIn(".results-nav-buttons", css)
        self.assertIn(".results-title-group", css)

        # Mobile media query
        self.assertIn("@media (max-width: 640px)", css)


if __name__ == "__main__":
    unittest.main()
