"""
Automated Validation & Recommendation Quality Test Suite
Validates API endpoints, response schemas, filtering constraints,
graceful fallback mechanics, and scoring integrity.
"""

import sys
import requests

BASE_URL = "http://127.0.0.1:5000"

TEST_CASES = [
    {
        "id": "Bangalore query",
        "params": {
            "location": "Bangalore",
            "budget": 3000,
            "min_rating": 4.0,
            "preference": "Good food comfortable room near metro"
        },
        "expected_location": "Bangalore",
        "strict_rating": True
    },
    {
        "id": "Jaipur query",
        "params": {
            "location": "Jaipur",
            "budget": 2500,
            "min_rating": 4.0,
            "preference": "Excellent service clean room family friendly"
        },
        "expected_location": "Jaipur",
        "strict_rating": True
    },
    {
        "id": "Delhi query",
        "params": {
            "location": "Delhi",
            "budget": 2000,
            "min_rating": 4.0,
            "preference": "Clean rooms friendly staff affordable price"
        },
        "expected_location": "Delhi_Transit",
        "strict_rating": True
    },
    {
        "id": "Mumbai query",
        "params": {
            "location": "Mumbai",
            "budget": 3000,
            "min_rating": 4.0,
            "preference": "Clean comfortable room good service"
        },
        "expected_location": "Mumbai",
        # Maximum rating in Mumbai is 3.92, so fallback must relax rating to 3.5
        "strict_rating": False,
        "expect_fallback": True,
        "relaxed_min_rating": 3.5
    },
    {
        "id": "Hyderabad query",
        "params": {
            "location": "Hyderabad",
            "budget": 2500,
            "min_rating": 3.5,
            "preference": "Affordable hotel with good staff and clean rooms"
        },
        "expected_location": "Hyderabad",
        "strict_rating": True
    }
]


def run_tests():
    print("=" * 60)
    print("Recommendation Quality Test")
    print("=" * 60)

    all_passed = True
    test_results_summary = []

    for test in TEST_CASES:
        test_id = test["id"]
        params = test["params"]
        expected_loc = test["expected_location"]
        strict_rating = test.get("strict_rating", True)
        expect_fallback = test.get("expect_fallback", False)
        relaxed_min_rating = test.get("relaxed_min_rating", 3.5)

        try:
            resp = requests.post(f"{BASE_URL}/recommend", json=params, timeout=15)
            if resp.status_code != 200:
                print(f"[FAIL] {test_id}: HTTP status {resp.status_code}")
                all_passed = False
                continue

            data = resp.json()
            if not data.get("success"):
                print(f"[FAIL] {test_id}: API returned success=False")
                all_passed = False
                continue

            hotels = data.get("hotels", [])
            if len(hotels) == 0:
                print(f"[FAIL] {test_id}: Zero hotels returned")
                all_passed = False
                continue

            # Check graceful fallback behavior if expected
            if expect_fallback:
                if not data.get("is_relaxed"):
                    print(f"[FAIL] {test_id}: Expected graceful fallback for rating but is_relaxed was False")
                    all_passed = False
                    continue
                if data.get("relaxed_filter") != "rating":
                    print(f"[FAIL] {test_id}: Expected relaxed_filter='rating', got '{data.get('relaxed_filter')}'")
                    all_passed = False
                    continue

            # Validate each returned hotel
            validation_error = None
            for h in hotels:
                # 1. Location match
                h_loc = h.get("location")
                if h_loc != expected_loc:
                    validation_error = f"Location mismatch: expected {expected_loc}, got {h_loc}"
                    break

                # 2. Budget constraint
                price = h.get("price")
                if price is not None and price > params["budget"]:
                    validation_error = f"Budget exceeded: price ₹{price} > budget ₹{params['budget']}"
                    break

                # 3. Rating constraint
                rating = h.get("rating")
                min_req = params["min_rating"] if strict_rating else relaxed_min_rating
                if rating is not None and rating < min_req:
                    validation_error = f"Rating below minimum requirement: {rating} < {min_req}"
                    break

                # 4. Valid numeric ranges
                score = h.get("score")
                if score is None or not (0 <= score <= 100):
                    validation_error = f"Invalid recommendation score: {score}"
                    break

                sentiment = h.get("sentiment")
                if sentiment is not None and not (0 <= sentiment <= 100):
                    validation_error = f"Invalid sentiment percentage: {sentiment}"
                    break

                aspect_match = h.get("aspect_match")
                if aspect_match is not None and not (0 <= aspect_match <= 100):
                    validation_error = f"Invalid aspect match percentage: {aspect_match}"
                    break

            if validation_error:
                print(f"[FAIL] {test_id}: {validation_error}")
                all_passed = False
                continue

            # Test passes!
            print(f"[PASS] {test_id}")
            test_results_summary.append({
                "name": test_id,
                "params": params,
                "count": len(hotels),
                "is_relaxed": data.get("is_relaxed", False),
                "relaxed_filter": data.get("relaxed_filter"),
                "top_hotels": hotels[:3]
            })

        except Exception as e:
            print(f"[FAIL] {test_id}: Exception {str(e)}")
            all_passed = False

    # Also validate new Hotel Details & Reviews endpoints using top hotel from Test 1
    if test_results_summary:
        sample_hotel_id = test_results_summary[0]["top_hotels"][0]["hotel_id"]
        print("-" * 60)
        print(f"Testing Hotel Details & Reviews API (Sample ID: {sample_hotel_id})...")

        # Details HTML endpoint
        det_resp = requests.get(f"{BASE_URL}/hotel/{sample_hotel_id}", timeout=10)
        if det_resp.status_code == 200 and "Aspect-wise Customer Feedback" in det_resp.text:
            print("[PASS] Hotel Details Route (/hotel/<id>)")
        else:
            print(f"[FAIL] Hotel Details Route returned status {det_resp.status_code}")
            all_passed = False

        # Reviews JSON endpoint
        rev_resp = requests.get(f"{BASE_URL}/api/hotel/{sample_hotel_id}/reviews?page=1&per_page=5", timeout=10)
        if rev_resp.status_code == 200 and rev_resp.json().get("success"):
            rev_data = rev_resp.json()
            print(f"[PASS] Hotel Reviews API (/api/hotel/<id>/reviews) - returned {len(rev_data.get('reviews', []))} reviews")
        else:
            print(f"[FAIL] Hotel Reviews API returned status {rev_resp.status_code}")
            all_passed = False

    print("=" * 60)
    print("\nDETAILED TEST RESULTS SUMMARY TABLE:")
    for summary in test_results_summary:
        p = summary["params"]
        print(f"\nScenario: {summary['name']}")
        print(f"  Location: {p['location']}, Budget: Rs.{p['budget']}, Min Rating: {p['min_rating']}")
        print(f"  Preference: '{p['preference']}'")
        print(f"  Results Count: {summary['count']}, Relaxed: {summary['is_relaxed']} ({summary['relaxed_filter']})")
        print("  Top Recommendations:")
        for idx, h in enumerate(summary["top_hotels"], 1):
            print(f"    {idx}. {h['name']}")
            print(f"       Price: Rs.{h['price']} | Rating: {h['rating']}* | Sentiment: {h['sentiment']}% | Aspect Match: {h['aspect_match']}% | Score: {h['score']}%")

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
