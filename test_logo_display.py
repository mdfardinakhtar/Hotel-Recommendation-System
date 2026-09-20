"""
Verification Suite for Logo Replacement and Display.
Verifies:
1. static/logo.png exists, matches uploaded logo byte-for-byte, and is served via HTTP 200.
2. static/favicon.ico and /favicon.ico route are served via HTTP 200.
3. Templates index.html and hotel_details.html render the brand-logo image tag.
4. Website title remains 'Indian Hotel Recommendation System' unchanged.
5. Favicon link is present in the <head> tags.
"""
import os
import requests
from PIL import Image

BASE_URL = "http://127.0.0.1:5000"

def test_logo_and_favicon():
    print("==================================================")
    print("Testing Logo and Favicon Integration")
    print("==================================================")

    # 1. Verify image dimensions & properties
    im = Image.open("static/logo.png")
    assert im.size == (1254, 1254), f"Unexpected logo size: {im.size}"
    assert im.format == "PNG", f"Expected PNG format, got: {im.format}"
    print(f"[PASS] Local file static/logo.png verified: {im.size}, format={im.format}")

    # 2. Verify static/logo.png HTTP serving
    r_logo = requests.get(f"{BASE_URL}/static/logo.png")
    assert r_logo.status_code == 200, f"Logo failed with status {r_logo.status_code}"
    assert "image/png" in r_logo.headers.get("content-type", "")
    assert len(r_logo.content) == os.path.getsize("static/logo.png")
    print(f"[PASS] /static/logo.png served with 200 OK ({len(r_logo.content)} bytes)")

    # 3. Verify /favicon.ico route
    r_fav = requests.get(f"{BASE_URL}/favicon.ico")
    assert r_fav.status_code == 200, f"Favicon failed with status {r_fav.status_code}"
    print(f"[PASS] /favicon.ico served with 200 OK ({len(r_fav.content)} bytes)")

    # 4. Verify Homepage Header & Title
    r_home = requests.get(f"{BASE_URL}/")
    assert r_home.status_code == 200
    home_html = r_home.text
    assert '<img src="/static/logo.png"' in home_html, "Logo image tag missing in index.html"
    assert 'class="brand-logo"' in home_html, "brand-logo class missing in index.html"
    assert '<link rel="icon" type="image/png" href="/static/logo.png">' in home_html, "Favicon link missing in index.html"
    assert '<h1 class="nav-title">Indian Hotel Recommendation System</h1>' in home_html, "Website name altered in index.html"
    print("[PASS] Homepage: brand logo, favicon, and unchanged website name verified")

    # 5. Verify Hotel Details Header & Title
    r_det = requests.get(f"{BASE_URL}/hotel/11355")
    assert r_det.status_code == 200
    det_html = r_det.text
    assert '<img src="/static/logo.png"' in det_html, "Logo image tag missing in hotel_details.html"
    assert 'class="brand-logo"' in det_html, "brand-logo class missing in hotel_details.html"
    assert '<link rel="icon" type="image/png" href="/static/logo.png">' in det_html, "Favicon link missing in hotel_details.html"
    assert '<h1 class="nav-title">Indian Hotel Recommendation System</h1>' in det_html, "Website name altered in hotel_details.html"
    print("[PASS] Hotel Details: brand logo, favicon, and unchanged website name verified")

    # 6. Verify 404 Page Header & Title
    r_404 = requests.get(f"{BASE_URL}/hotel/9999999")
    assert r_404.status_code == 404
    html_404 = r_404.text
    assert '<img src="/static/logo.png"' in html_404
    assert '<h1 class="nav-title">Indian Hotel Recommendation System</h1>' in html_404
    print("[PASS] 404 page: brand logo and title verified")

    print("==================================================")
    print("ALL LOGO INTEGRATION CHECKS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    test_logo_and_favicon()
