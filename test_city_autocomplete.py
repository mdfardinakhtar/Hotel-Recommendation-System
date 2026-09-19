"""
Validation script for Destination City Autocomplete component and backend integration.
"""
import requests
import json
import re

BASE_URL = "http://127.0.0.1:5000"

def test_homepage_html():
    print("--- 1. Testing Homepage HTML Structure ---")
    resp = requests.get(f"{BASE_URL}/")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    html = resp.text
    
    # Verify required elements exist
    assert 'id="city-search-input"' in html, "city-search-input not found"
    assert 'id="clear-city-btn"' in html, "clear-city-btn not found"
    assert 'id="location"' in html, "hidden location input not found"
    assert 'id="city-dropdown-menu"' in html, "city-dropdown-menu not found"
    assert 'id="city-dropdown-list"' in html, "city-dropdown-list not found"
    assert 'window.SERVER_LOCATIONS = [' in html, "window.SERVER_LOCATIONS not found"
    
    # Extract window.SERVER_LOCATIONS from HTML
    match = re.search(r'window\.SERVER_LOCATIONS\s*=\s*(\[.*?\]);', html, re.DOTALL)
    assert match is not None, "Could not extract SERVER_LOCATIONS from script tag"
    
    locations_json = match.group(1)
    locations = json.loads(locations_json)
    print(f"Total locations loaded in frontend: {len(locations)}")
    assert len(locations) > 200, f"Expected > 200 locations, got {len(locations)}"
    
    # Verify first option is All India
    assert locations[0]["value"] == "", "First option should be empty value (All India)"
    assert "All India" in locations[0]["label"], "First option should have All India label"
    
    # Verify key cities exist
    delhi_loc = next((loc for loc in locations if loc["value"] == "Delhi_Transit"), None)
    assert delhi_loc is not None, "Delhi_Transit not found in SERVER_LOCATIONS"
    assert delhi_loc["label"] == "Delhi (Transit)", f"Delhi label is {delhi_loc['label']}"
    
    bangalore_loc = next((loc for loc in locations if loc["value"] == "Bangalore"), None)
    assert bangalore_loc is not None, "Bangalore not found in SERVER_LOCATIONS"
    
    mumbai_loc = next((loc for loc in locations if loc["value"] == "Mumbai"), None)
    assert mumbai_loc is not None, "Mumbai not found in SERVER_LOCATIONS"
    
    print("Homepage HTML and SERVER_LOCATIONS passed!")


def test_recommendation_endpoints():
    print("\n--- 2. Testing /recommend API with various city queries ---")
    
    test_cases = [
        {"desc": "Delhi_Transit (from autocomplete select)", "location": "Delhi_Transit", "expected_loc": "Delhi_Transit"},
        {"desc": "Delhi (from typed normalized query)", "location": "Delhi", "expected_loc": "Delhi_Transit"},
        {"desc": "delhi (lowercase normalized)", "location": "delhi", "expected_loc": "Delhi_Transit"},
        {"desc": "Bangalore", "location": "Bangalore", "expected_loc": "Bangalore"},
        {"desc": "Mumbai", "location": "Mumbai", "expected_loc": "Mumbai"},
        {"desc": "All India (empty location)", "location": "", "expected_loc": None},
    ]
    
    for tc in test_cases:
        payload = {
            "location": tc["location"],
            "budget": "3500",
            "min_rating": "3.5",
            "preference": "clean room good service"
        }
        resp = requests.post(f"{BASE_URL}/recommend", json=payload)
        assert resp.status_code == 200, f"Failed for {tc['desc']}: status {resp.status_code}"
        data = resp.json()
        assert data.get("success") is True, f"Failed for {tc['desc']}: success is not True"
        hotels = data.get("hotels", [])
        assert len(hotels) > 0, f"No hotels returned for {tc['desc']}"
        
        if tc["expected_loc"]:
            for h in hotels:
                assert h["location"] == tc["expected_loc"], f"Expected location {tc['expected_loc']}, got {h['location']}"
        
        print(f"PASS: {tc['desc']} -> returned {len(hotels)} hotels (top: '{hotels[0]['name']}' in {hotels[0]['location']})")

if __name__ == "__main__":
    test_homepage_html()
    test_recommendation_endpoints()
    print("\nALL CITY AUTOCOMPLETE AND BACKEND TESTS PASSED SUCCESSFULLY!")
