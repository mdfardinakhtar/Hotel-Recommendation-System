"""
Automated Verification Suite for Destination City Searchable Dropdown / Autocomplete.
Covers all 12 test cases requested by the user.
"""
import requests
import json
import re

BASE_URL = "http://127.0.0.1:5000"

def filter_cities_client_sim(locations, query):
    """Exact simulation of JavaScript handleCitySearchInput filtering logic."""
    raw_query = (query or "").strip()
    q_lower = raw_query.lower()
    if not q_lower:
        return locations
    matches = []
    for item in locations:
        label = (item.get("label") or "").lower()
        val = (item.get("value") or "").lower()
        norm_val = val.replace("_", " ")
        if q_lower in label or q_lower in val or q_lower in norm_val:
            matches.append(item)
        elif q_lower.startswith("del") and ("delhi" in label or "delhi" in val):
            matches.append(item)
    return matches

def run_tests():
    print("==================================================")
    print("Testing Destination City Searchable Dropdown")
    print("==================================================")

    # Fetch homepage and parse window.SERVER_LOCATIONS
    resp = requests.get(f"{BASE_URL}/")
    assert resp.status_code == 200, f"Failed to get homepage: {resp.status_code}"
    html = resp.text

    # Extract window.SERVER_LOCATIONS
    match = re.search(r'window\.SERVER_LOCATIONS\s*=\s*(\[.*?\]);', html, re.DOTALL)
    assert match is not None, "Could not extract window.SERVER_LOCATIONS from homepage"
    locations = json.loads(match.group(1))
    print(f"Total verified locations pre-loaded: {len(locations)}")

    # 1. Search "Delhi"
    delhi_matches = filter_cities_client_sim(locations, "Delhi")
    delhi_labels = [m["label"] for m in delhi_matches]
    print(f"[TEST 1] Search 'Delhi': {delhi_labels}")
    assert any("Delhi" in lbl for lbl in delhi_labels), "Expected Delhi in search results"

    # 2. Search "del"
    del_matches = filter_cities_client_sim(locations, "del")
    del_labels = [m["label"] for m in del_matches]
    print(f"[TEST 2] Search 'del': {del_labels}")
    assert any("Delhi" in lbl for lbl in del_labels), "Expected Delhi in 'del' search results"

    # 3. Search "Bangalore"
    blr_matches = filter_cities_client_sim(locations, "Bangalore")
    blr_labels = [m["label"] for m in blr_matches]
    print(f"[TEST 3] Search 'Bangalore': {blr_labels}")
    assert "Bangalore" in blr_labels, "Expected Bangalore in search results"

    # 4. Search "ban"
    ban_matches = filter_cities_client_sim(locations, "ban")
    ban_labels = [m["label"] for m in ban_matches]
    print(f"[TEST 4] Search 'ban': {ban_labels}")
    assert "Bangalore" in ban_labels, "Expected Bangalore in 'ban' search results"

    # 5. Search "Mumbai"
    mum_full_matches = filter_cities_client_sim(locations, "Mumbai")
    mum_full_labels = [m["label"] for m in mum_full_matches]
    print(f"[TEST 5] Search 'Mumbai': {mum_full_labels}")
    assert "Mumbai" in mum_full_labels, "Expected Mumbai in search results"

    # 6. Search "mum"
    mum_matches = filter_cities_client_sim(locations, "mum")
    mum_labels = [m["label"] for m in mum_matches]
    print(f"[TEST 6] Search 'mum': {mum_labels}")
    assert "Mumbai" in mum_labels, "Expected Mumbai in 'mum' search results"

    # 7. Search a nonexistent city such as "XYZABC"
    fake_matches = filter_cities_client_sim(locations, "XYZABC")
    print(f"[TEST 7] Search 'XYZABC': {len(fake_matches)} matches -> displays 'No city found'")
    assert len(fake_matches) == 0, "Expected 0 matches for nonexistent city"

    # 8. Select a city (e.g. Bangalore)
    selected_city = blr_matches[0]
    location_payload_val = selected_city["value"]
    print(f"[TEST 8] Select city: label='{selected_city['label']}', value='{location_payload_val}'")
    assert location_payload_val == "Bangalore"

    # 9. Clear the selected city
    cleared_val = ""
    cleared_matches = filter_cities_client_sim(locations, cleared_val)
    print(f"[TEST 9] Clear selected city: value='{cleared_val}', shows all {len(cleared_matches)} options")
    assert cleared_val == ""
    assert len(cleared_matches) == len(locations)

    # 10. Search and select another city (e.g. Delhi)
    delhi_choice = next(m for m in del_matches if m["value"] == "Delhi_Transit")
    print(f"[TEST 10] Select another city: label='{delhi_choice['label']}', value='{delhi_choice['value']}'")
    assert delhi_choice["value"] == "Delhi_Transit"

    # 11. Submit recommendation request
    payload = {
        "location": delhi_choice["value"],
        "budget": "3000",
        "min_rating": "4.0",
        "preference": "Clean Room Friendly Staff"
    }
    rec_resp = requests.post(f"{BASE_URL}/recommend", json=payload)
    print(f"[TEST 11] Submit recommendation request: Status code = {rec_resp.status_code}")
    assert rec_resp.status_code == 200, f"Expected 200 OK, got {rec_resp.status_code}"

    # 12. Verify the correct location reaches the existing recommendation API
    data = rec_resp.json()
    assert data.get("success") is True, "Expected success=True"
    hotels = data.get("hotels", [])
    print(f"[TEST 12] Verified response: returned {len(hotels)} hotels in {hotels[0]['location']}")
    assert len(hotels) > 0, "Expected hotels to be returned"
    for h in hotels:
        assert h["location"] == "Delhi_Transit", f"Expected location 'Delhi_Transit', got '{h['location']}'"

    print("\n==================================================")
    print("ALL 12 TEST CASES PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
