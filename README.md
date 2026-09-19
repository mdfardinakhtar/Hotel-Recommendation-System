# Indian Hotel Recommendation System

An intelligent Indian hotel recommendation platform powered by Natural Language Processing (NLP), aspect matching, customer review analytics, and machine learning sentiment classification.

---

## 🚀 How to Run Locally

1. Open your terminal in this project folder.
2. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the application:
   ```bash
   python app.py
   ```
5. Open your browser:
   [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🧪 Running Automated Tests

Run the automated test suites to validate recommendation quality, exact address integrity, city autocomplete, and booking lifecycle:
```bash
# 1. Test complete hotel booking flow (17 scenarios)
python test_booking.py

# 2. Test hotel address accuracy & duplicate city removal
python test_hotel_address.py

# 3. Test recommendation quality & NLP scoring
python test_recommendations.py

# 4. Test searchable destination city autocomplete
python test_city_autocomplete.py
```

---

## 🏨 Hotel Discovery & Booking Architecture

1. **Intelligent Discovery:** Users search by city, budget, minimum rating, and text preferences (e.g. *"quiet room near metro"*).
2. **Authoritative Address Hierarchy:**
   - **Hotel Name:** Name only
   - **Hotel Address:** Exact street, locality, landmark, state, and PIN code from dataset (with duplicate city safely removed)
   - **City / Location:** Independent destination city indicator
3. **One-Click Reservation Workflow:**
   - `[Book Now]` buttons on each recommendation card and hotel profile
   - Responsive 2-column reservation page with real-time night & price recalculation
   - Server-side authoritative price verification ($Total = Price \times Nights \times Rooms$)
   - Collision-resistant sequential Booking IDs (`BK` + YYYYMMDD + 4-digit sequence)
   - Persistent SQLite database storage in `booking.db`
   - Complete booking confirmation voucher with print/PDF support
   - "My Bookings" lookup dashboard with easy cancellation support

---

## 🧠 Recommendation Flow & Scoring Formula

User Preferences $\rightarrow$ TF-IDF Similarity + Aspect Match + Smoothed Sentiment + Smoothed Rating $\rightarrow$ Ranking

$$\text{Recommendation Score} = 0.35 \times \text{Similarity} + 0.25 \times \text{Aspect Match} + 0.20 \times \text{Smoothed Sentiment} + 0.20 \times \text{Rating Score}$$

### Key Features:
- **Aspect-Based Sentiment Extraction:** 9 hospitality aspects (Cleanliness, Room, Staff, Service, Food, Location, Price, Facilities, Comfort).
- **Graceful Fallback Mode:** Relaxes one constraint at a time if exact search criteria yield zero results, with full transparency to the user.
- **Location Normalization:** Smart location handling (e.g. "Delhi" seamlessly matches "Delhi_Transit").
- **Client-Side Sorting:** Sort recommendations dynamically by Best Match, Highest Rated, Lowest Price, or Highest Sentiment without re-querying backend.

---

## 📡 API Endpoints

### 1. `POST /recommend`
Generates personalized hotel recommendations based on constraints and free-form preference text.

**Example Request:**
```json
{
  "location": "Bangalore",
  "budget": 3000,
  "min_rating": 4.0,
  "preference": "clean room, friendly staff, good food"
}
```

### 2. `GET /hotel/<int:hotel_id>`
Detailed hotel profile page showing exact dataset address, aspect-wise feedback bars, ML sentiment breakdown, verified "Why Recommended" reasons, and paginated customer reviews.

### 3. `GET /book/<int:hotel_id>` & `POST /book/<int:hotel_id>`
Hotel booking form and submission endpoint. Supports both standard HTML form POST (with redirect) and JSON API requests (returns 201 with booking reference).

### 4. `GET /booking/confirmation/<booking_id>`
Displays the official booking voucher and reservation summary.

### 5. `GET /my-bookings`
Booking lookup portal allowing guests to enter their Booking Reference ID to check itinerary details, download vouchers, or cancel reservations.

### 6. `POST /booking/cancel/<booking_id>`
Cancels a reservation in the database without deleting historical records.

### 7. `GET /api/hotel/<int:hotel_id>/pricing`
Authoritative per-night pricing lookup for dynamic client calculation.

### 8. `GET /api/hotel/<int:hotel_id>/reviews`
REST endpoint returning paginated customer reviews with sentiment filtering (`?page=1&per_page=10&sentiment=positive`).

### 9. `GET /health`
System health check returning indexed review count, hotel count, and covered Indian locations.

