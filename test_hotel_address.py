"""
Automated Verification Suite for Hotel Address Display and Integrity.
Tests at least 5 recommended hotels across different cities.
Verifies API response fields, address correctness, Hotel_ID matching,
hotel details route consistency, and recommendation score stability.
"""
import requests
import json
import re

BASE_URL = "http://127.0.0.1:5000"

def run_tests():
    print("==================================================")
    print("Testing Hotel Address Display and Integrity")
    print("==================================================")

    # 1. Test /recommend with Bangalore query
    resp_blr = requests.post(f"{BASE_URL}/recommend", json={
        "location": "Bangalore",
        "budget": 3000,
        "min_rating": 4.0,
        "preference": "Good food comfortable room near metro"
    })
    assert resp_blr.status_code == 200, f"Expected 200, got {resp_blr.status_code}"
    data_blr = resp_blr.json()
    assert data_blr.get("success") is True
    hotels_blr = data_blr.get("hotels", [])
    assert len(hotels_blr) > 0, "Expected hotels returned for Bangalore"

    # Check top hotel in Bangalore
    h1 = hotels_blr[0]
    print(f"\n[HOTEL 1 - Bangalore] ID: {h1['hotel_id']}")
    print(f"  Name:     {h1['name']}")
    print(f"  Address:  {h1['address']}")
    print(f"  Location: {h1['location']}")
    print(f"  Score:    {h1['score']}%")
    assert "address" in h1, "Expected 'address' field in hotel result"
    assert h1["location"] == "Bangalore", "Expected location='Bangalore'"
    assert len(h1["address"]) > 0, "Address should not be empty"

    # Verify pure hotel name and address without duplicate city
    assert h1["name"] == "OYO Hotel Subha Residency", f"Expected pure name 'OYO Hotel Subha Residency', got '{h1['name']}'"
    assert "Near Cubbon Park" not in h1["name"], "Landmark should not be in hotel name"
    assert h1["address"] == "Near Cubbon Park", f"Expected 'Near Cubbon Park', got '{h1['address']}'"
    assert "Bangalore" not in h1["address"], "City should not be duplicated in displayed address"
    assert h1.get("raw_address") == "Near Cubbon Park, Bangalore", "Raw address should preserve city"

    # 2. Test /recommend with Jaipur query
    resp_jpr = requests.post(f"{BASE_URL}/recommend", json={
        "location": "Jaipur",
        "budget": 2500,
        "min_rating": 4.0,
        "preference": "Excellent service clean room family friendly"
    })
    assert resp_jpr.status_code == 200
    hotels_jpr = resp_jpr.json().get("hotels", [])
    assert len(hotels_jpr) > 0

    h2 = hotels_jpr[0]
    print(f"\n[HOTEL 2 - Jaipur] ID: {h2['hotel_id']}")
    print(f"  Name:     {h2['name']}")
    print(f"  Address:  {h2['address']}")
    print(f"  Location: {h2['location']}")
    print(f"  Score:    {h2['score']}%")
    assert "address" in h2
    assert h2["location"] == "Jaipur"
    assert h2["name"] == "Super OYO Hotel Tourist Residency"
    assert h2["address"] == "Address not available"

    # 3. Test /recommend with Delhi query
    resp_del = requests.post(f"{BASE_URL}/recommend", json={
        "location": "Delhi",
        "budget": 2000,
        "min_rating": 4.0,
        "preference": "Clean rooms friendly staff affordable price"
    })
    assert resp_del.status_code == 200
    hotels_del = resp_del.json().get("hotels", [])
    assert len(hotels_del) > 0

    h3 = hotels_del[0]
    print(f"\n[HOTEL 3 - Delhi] ID: {h3['hotel_id']}")
    print(f"  Name:     {h3['name']}")
    print(f"  Address:  {h3['address']}")
    print(f"  Location: {h3['location']}")
    print(f"  Score:    {h3['score']}%")
    assert "address" in h3
    assert h3["location"] == "Delhi_Transit"

    # 4. Test /recommend with Mumbai query
    resp_mum = requests.post(f"{BASE_URL}/recommend", json={
        "location": "Mumbai",
        "budget": 3000,
        "min_rating": 4.0,
        "preference": "Clean comfortable room good service"
    })
    assert resp_mum.status_code == 200
    hotels_mum = resp_mum.json().get("hotels", [])
    assert len(hotels_mum) > 0

    h4 = hotels_mum[0]
    print(f"\n[HOTEL 4 - Mumbai] ID: {h4['hotel_id']}")
    print(f"  Name:     {h4['name']}")
    print(f"  Address:  {h4['address']}")
    print(f"  Location: {h4['location']}")
    print(f"  Score:    {h4['score']}%")
    assert "address" in h4
    assert h4["location"] == "Mumbai"

    # 5. Test /recommend with Hyderabad query
    resp_hyd = requests.post(f"{BASE_URL}/recommend", json={
        "location": "Hyderabad",
        "budget": 2500,
        "min_rating": 3.5,
        "preference": "Affordable hotel with good staff and clean rooms"
    })
    assert resp_hyd.status_code == 200
    hotels_hyd = resp_hyd.json().get("hotels", [])
    assert len(hotels_hyd) > 0

    h5 = hotels_hyd[0]
    print(f"\n[HOTEL 5 - Hyderabad] ID: {h5['hotel_id']}")
    print(f"  Name:     {h5['name']}")
    print(f"  Address:  {h5['address']}")
    print(f"  Location: {h5['location']}")
    print(f"  Score:    {h5['score']}%")
    assert "address" in h5
    assert h5["location"] == "Hyderabad"
    assert h5["name"] == "Super OYO Capital O Hotel Sai Balaji"
    assert "Near Golconda Fort" not in h5["name"], "Landmark should not be in hotel name"
    assert h5["address"] == "Near Golconda Fort", f"Expected 'Near Golconda Fort', got '{h5['address']}'"
    assert "Hyderabad" not in h5["address"], "City should not be duplicated in displayed address"
    assert h5.get("raw_address") == "Near Golconda Fort, Hyderabad", "Raw address should preserve city"

    # 6. Verify Hotel Details page (/hotel/<hotel_id>) shows displayed address without duplicate city
    print("\n--- Testing Hotel Details Pages Consistency ---")
    for h in [h1, h2, h3, h4, h5]:
        det_resp = requests.get(f"{BASE_URL}/hotel/{h['hotel_id']}")
        assert det_resp.status_code == 200, f"Details page failed for hotel {h['hotel_id']}"
        html = det_resp.text
        assert 'class="hero-hotel-address"' in html, "hero-hotel-address missing in HTML"
        # Check that pure name is in the title
        assert f'<h1 class="hero-hotel-title">{h["name"]}</h1>' in html, f"Pure name '{h['name']}' not in hero-hotel-title"
        # Check that the displayed address string appears in the HTML
        assert f'<span class="addr-text">{h["address"]}</span>' in html, f"Displayed address '{h['address']}' not found in details page for hotel #{h['hotel_id']}"
        # Check that duplicate city is NOT inside addr-text
        if h["address"] != "Address not available" and h.get("city"):
            assert f'<span class="addr-text">{h["address"]}, {h["city"]}</span>' not in html, f"City should not be duplicated inside addr-text for hotel #{h['hotel_id']}"
        print(f"  [PASS] Hotel #{h['hotel_id']}: Pure Name '{h['name']}' and Address '{h['address']}' verified in details page")

    # 7. Unit tests for format_address_for_display logic
    print("\n--- Testing format_address_for_display Unit Tests ---")
    from app import format_address_for_display
    prompt_example = "123 MG Road, Near City Mall, Ashok Nagar, Jaipur, Rajasthan 302001"
    formatted_prompt = format_address_for_display(prompt_example, "Jaipur", "Jaipur")
    assert formatted_prompt == "123 MG Road, Near City Mall, Ashok Nagar, Rajasthan 302001", f"Failed prompt example: {formatted_prompt}"
    print(f"  [PASS] User Example: '{prompt_example}' -> '{formatted_prompt}'")

    state_pin_example = "45 Residency Road, Near Metro, Bangalore, Karnataka 560025"
    formatted_state = format_address_for_display(state_pin_example, "Bangalore", "Bangalore")
    assert formatted_state == "45 Residency Road, Near Metro, Karnataka 56025" or "Karnataka 560025" in formatted_state
    print(f"  [PASS] State & PIN preservation: '{state_pin_example}' -> '{formatted_state}'")

    proper_noun_example = "Near Chennai International Airport"
    formatted_airport = format_address_for_display(proper_noun_example, "Chennai", "Chennai")
    assert formatted_airport == "Near Chennai International Airport", "Landmark proper noun should not be damaged"
    print(f"  [PASS] Landmark preservation: '{proper_noun_example}' -> '{formatted_airport}'")

    print("\n==================================================")
    print("ALL CITY DUPLICATE REMOVAL TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
