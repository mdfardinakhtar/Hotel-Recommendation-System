import unittest
import json
import re
import sqlite3
from datetime import date, timedelta
from app import app, get_db_connection, init_booking_db, hotel_data, HOTEL_DISPLAY_LOOKUP


class HotelBookingTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.client.testing = True
        init_booking_db()
        # Find a valid hotel ID with price
        cls.valid_hotel = hotel_data.dropna(subset=["Avg_Price"]).iloc[0]
        cls.valid_hotel_id = int(cls.valid_hotel["Hotel_ID"])
        cls.valid_hotel_price = round(float(cls.valid_hotel["Avg_Price"]))

    def test_01_get_booking_page_valid_hotel(self):
        """GET /book/<hotel_id> returns 200 and contains hotel details."""
        res = self.client.get(f"/book/{self.valid_hotel_id}")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        display_info = HOTEL_DISPLAY_LOOKUP.get(self.valid_hotel_id)
        self.assertIn(display_info["name"], html)
        self.assertIn("Complete Booking", html)
        self.assertIn("Primary Guest Details", html)

    def test_02_get_booking_page_invalid_hotel(self):
        """GET /book/<invalid_id> returns 404."""
        res = self.client.get("/book/9999999")
        self.assertEqual(res.status_code, 404)

    def test_03_successful_booking_creation_redirect(self):
        """POST /book/<hotel_id> with valid form data creates reservation and redirects."""
        today = date.today()
        cin = (today + timedelta(days=5)).strftime("%Y-%m-%d")
        cout = (today + timedelta(days=8)).strftime("%Y-%m-%d")  # 3 nights

        data = {
            "guest_name": "Arjun Sharma",
            "email": "arjun.sharma@example.com",
            "phone": "9876543210",
            "check_in": cin,
            "check_out": cout,
            "guests": "2",
            "rooms": "1",
            "special_request": "Quiet room on a high floor"
        }
        res = self.client.post(f"/book/{self.valid_hotel_id}", data=data)
        self.assertEqual(res.status_code, 302)
        location_header = res.headers.get("Location", "")
        self.assertIn("/booking/confirmation/", location_header)
        booking_id = location_header.split("/")[-1]
        self.assertTrue(re.match(r"^BK\d{8}\d{4}$", booking_id), f"Invalid ID format: {booking_id}")

    def test_04_successful_booking_creation_json(self):
        """POST /book/<hotel_id> with JSON payload returns 201 with booking_id."""
        today = date.today()
        cin = (today + timedelta(days=10)).strftime("%Y-%m-%d")
        cout = (today + timedelta(days=12)).strftime("%Y-%m-%d")  # 2 nights

        payload = {
            "guest_name": "Priya Patel",
            "email": "priya.p@testdomain.in",
            "phone": "+91 9123456789",
            "check_in": cin,
            "check_out": cout,
            "guests": 3,
            "rooms": 2,
            "special_request": "Late check-in requested"
        }
        res = self.client.post(
            f"/book/{self.valid_hotel_id}",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        resp_data = json.loads(res.data.decode("utf-8"))
        self.assertTrue(resp_data["success"])
        expected_total = round(self.valid_hotel_price * 2 * 2, 2)
        self.assertEqual(resp_data["total_amount"], expected_total)

    def test_05_authoritative_price_calculation_ignores_tampering(self):
        """Server ignores any client-supplied tampered total amount."""
        today = date.today()
        cin = (today + timedelta(days=3)).strftime("%Y-%m-%d")
        cout = (today + timedelta(days=5)).strftime("%Y-%m-%d")  # 2 nights

        payload = {
            "guest_name": "Hacker Attempt",
            "email": "tamper@security.org",
            "phone": "9998887776",
            "check_in": cin,
            "check_out": cout,
            "guests": 1,
            "rooms": 1,
            "total_amount": "1.00",  # Fraudulent price attempt
            "price_per_night": "1.00"
        }
        res = self.client.post(
            f"/book/{self.valid_hotel_id}",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        resp_data = json.loads(res.data.decode("utf-8"))
        booking_id = resp_data["booking_id"]

        # Verify in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT price_per_night, total_amount FROM bookings WHERE booking_id = ?", (booking_id,))
        row = cursor.fetchone()
        conn.close()

        expected_total = round(self.valid_hotel_price * 2 * 1, 2)
        self.assertEqual(row["price_per_night"], self.valid_hotel_price)
        self.assertEqual(row["total_amount"], expected_total)

    def test_06_database_record_persistence(self):
        """Verify saved record matches input data and schema in SQLite."""
        today = date.today()
        cin = (today + timedelta(days=20)).strftime("%Y-%m-%d")
        cout = (today + timedelta(days=22)).strftime("%Y-%m-%d")

        payload = {
            "guest_name": "Rohit Verma",
            "email": "rohit.verma@example.com",
            "phone": "9820098200",
            "check_in": cin,
            "check_out": cout,
            "guests": 2,
            "rooms": 1,
            "special_request": "Non-smoking room"
        }
        res = self.client.post(
            f"/book/{self.valid_hotel_id}",
            data=json.dumps(payload),
            content_type="application/json"
        )
        resp_data = json.loads(res.data.decode("utf-8"))
        booking_id = resp_data["booking_id"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,))
        row = dict(cursor.fetchone())
        conn.close()

        self.assertEqual(row["guest_name"], "Rohit Verma")
        self.assertEqual(row["email"], "rohit.verma@example.com")
        self.assertEqual(row["phone"], "9820098200")
        self.assertEqual(row["check_in"], cin)
        self.assertEqual(row["check_out"], cout)
        self.assertEqual(row["nights"], 2)
        self.assertEqual(row["guests"], 2)
        self.assertEqual(row["rooms"], 1)
        self.assertEqual(row["special_request"], "Non-smoking room")
        self.assertEqual(row["booking_status"], "Confirmed")

    def test_07_get_booking_confirmation_valid(self):
        """GET /booking/confirmation/<booking_id> renders confirmation page."""
        today = date.today()
        cin = (today + timedelta(days=4)).strftime("%Y-%m-%d")
        cout = (today + timedelta(days=6)).strftime("%Y-%m-%d")

        res_post = self.client.post(
            f"/book/{self.valid_hotel_id}",
            data=json.dumps({
                "guest_name": "Kavita Rao",
                "email": "kavita.rao@domain.com",
                "phone": "9711223344",
                "check_in": cin,
                "check_out": cout,
                "guests": 1,
                "rooms": 1
            }),
            content_type="application/json"
        )
        booking_id = json.loads(res_post.data.decode("utf-8"))["booking_id"]

        res_conf = self.client.get(f"/booking/confirmation/{booking_id}")
        self.assertEqual(res_conf.status_code, 200)
        html = res_conf.data.decode("utf-8")
        self.assertIn(booking_id, html)
        self.assertIn("Kavita Rao", html)
        self.assertIn("Reservation Confirmed!", html)

    def test_08_get_booking_confirmation_invalid(self):
        """GET /booking/confirmation/<invalid_id> returns 404."""
        res = self.client.get("/booking/confirmation/BK999999990000")
        self.assertEqual(res.status_code, 404)

    def test_09_validation_missing_name(self):
        """Missing or blank guest name returns 400."""
        today = date.today()
        payload = {
            "guest_name": "   ",
            "email": "test@test.com",
            "phone": "9876543210",
            "check_in": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
            "check_out": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
            "guests": 1,
            "rooms": 1
        }
        res = self.client.post(
            f"/book/{self.valid_hotel_id}",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data.decode("utf-8"))
        self.assertIn("valid full name", data["error"])

    def test_10_validation_invalid_email(self):
        """Invalid email returns 400."""
        today = date.today()
        payload = {
            "guest_name": "Ananya Sen",
            "email": "not-an-email",
            "phone": "9876543210",
            "check_in": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
            "check_out": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
            "guests": 1,
            "rooms": 1
        }
        res = self.client.post(
            f"/book/{self.valid_hotel_id}",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data.decode("utf-8"))
        self.assertIn("valid email address", data["error"])

    def test_11_validation_invalid_phone(self):
        """Invalid phone (< 7 digits or invalid characters) returns 400."""
        today = date.today()
        payload = {
            "guest_name": "Siddharth Roy",
            "email": "sid@test.com",
            "phone": "123",  # Too short
            "check_in": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
            "check_out": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
            "guests": 1,
            "rooms": 1
        }
        res = self.client.post(
            f"/book/{self.valid_hotel_id}",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data.decode("utf-8"))
        self.assertIn("valid mobile number", data["error"])

    def test_12_validation_past_check_in_date(self):
        """Check-in date in the past returns 400."""
        past_cin = (date.today() - timedelta(days=2)).strftime("%Y-%m-%d")
        cout = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        payload = {
            "guest_name": "Vikram Seth",
            "email": "vikram@test.com",
            "phone": "9876543210",
            "check_in": past_cin,
            "check_out": cout,
            "guests": 1,
            "rooms": 1
        }
        res = self.client.post(
            f"/book/{self.valid_hotel_id}",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data.decode("utf-8"))
        self.assertIn("cannot be in the past", data["error"])

    def test_13_validation_checkout_before_or_same_as_checkin(self):
        """Check-out date on or before check-in returns 400."""
        cin = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")
        payload = {
            "guest_name": "Vikram Seth",
            "email": "vikram@test.com",
            "phone": "9876543210",
            "check_in": cin,
            "check_out": cin,  # Same day
            "guests": 1,
            "rooms": 1
        }
        res = self.client.post(
            f"/book/{self.valid_hotel_id}",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data.decode("utf-8"))
        self.assertIn("Check-out date must be after check-in date", data["error"])

    def test_14_validation_invalid_guests_or_rooms(self):
        """Guests or rooms < 1 returns 400."""
        cin = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")
        cout = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")
        payload = {
            "guest_name": "Meera Joshi",
            "email": "meera@test.com",
            "phone": "9876543210",
            "check_in": cin,
            "check_out": cout,
            "guests": 0,
            "rooms": 1
        }
        res = self.client.post(
            f"/book/{self.valid_hotel_id}",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data.decode("utf-8"))
        self.assertIn("at least 1", data["error"])

    def test_15_cancel_booking_workflow(self):
        """POST /booking/cancel/<booking_id> marks status as 'Cancelled' without deleting record."""
        today = date.today()
        cin = (today + timedelta(days=7)).strftime("%Y-%m-%d")
        cout = (today + timedelta(days=9)).strftime("%Y-%m-%d")

        post_res = self.client.post(
            f"/book/{self.valid_hotel_id}",
            data=json.dumps({
                "guest_name": "Devansh Nair",
                "email": "devansh@domain.com",
                "phone": "9812345678",
                "check_in": cin,
                "check_out": cout,
                "guests": 1,
                "rooms": 1
            }),
            content_type="application/json"
        )
        booking_id = json.loads(post_res.data.decode("utf-8"))["booking_id"]

        cancel_res = self.client.post(
            f"/booking/cancel/{booking_id}",
            content_type="application/json"
        )
        self.assertEqual(cancel_res.status_code, 200)
        cancel_data = json.loads(cancel_res.data.decode("utf-8"))
        self.assertTrue(cancel_data["success"])
        self.assertEqual(cancel_data["status"], "Cancelled")

        # Verify in DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT booking_status FROM bookings WHERE booking_id = ?", (booking_id,))
        row = cursor.fetchone()
        conn.close()
        self.assertEqual(row["booking_status"], "Cancelled")

    def test_16_my_bookings_lookup(self):
        """GET /my-bookings with booking_id displays existing booking; unknown shows not found."""
        today = date.today()
        cin = (today + timedelta(days=8)).strftime("%Y-%m-%d")
        cout = (today + timedelta(days=10)).strftime("%Y-%m-%d")

        post_res = self.client.post(
            f"/book/{self.valid_hotel_id}",
            data=json.dumps({
                "guest_name": "Rohan Gupta",
                "email": "rohan.gupta@example.in",
                "phone": "9811122233",
                "check_in": cin,
                "check_out": cout,
                "guests": 2,
                "rooms": 1
            }),
            content_type="application/json"
        )
        booking_id = json.loads(post_res.data.decode("utf-8"))["booking_id"]

        # Lookup existing
        lookup_res = self.client.get(f"/my-bookings?booking_id={booking_id}")
        self.assertEqual(lookup_res.status_code, 200)
        html = lookup_res.data.decode("utf-8")
        self.assertIn(booking_id, html)
        self.assertIn("Rohan Gupta", html)

        # Lookup non-existent
        lookup_unknown = self.client.get("/my-bookings?booking_id=BK999900009999")
        self.assertEqual(lookup_unknown.status_code, 200)
        unknown_html = lookup_unknown.data.decode("utf-8")
        self.assertIn("No Reservation Found", unknown_html)

    def test_17_api_hotel_pricing(self):
        """GET /api/hotel/<hotel_id>/pricing returns 200 with matching price."""
        res = self.client.get(f"/api/hotel/{self.valid_hotel_id}/pricing")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode("utf-8"))
        self.assertTrue(data["success"])
        self.assertEqual(data["price_per_night"], self.valid_hotel_price)


if __name__ == "__main__":
    unittest.main()
