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

Run the automated test suites to validate recommendation quality, exact address integrity, city autocomplete, and external booking platform discovery:
```bash
# 1. Test external booking platform recommendations & search queries (6 tests)
python test_booking_platforms.py

# 2. Test hotel address accuracy & duplicate city removal
python test_hotel_address.py

# 3. Test recommendation quality & NLP scoring formula
python test_recommendations.py

# 4. Test searchable destination city autocomplete
python test_city_autocomplete.py
```

---

## 🏨 Recommendation & External Booking Platform Discovery Architecture

The application is strictly designed as an **intelligent recommendation and discovery platform**:

1. **Intelligent Discovery:** Users search by city, budget, minimum rating, and text preferences (e.g. *"quiet room near metro"*).
2. **Authoritative 3-Tier Address Hierarchy:**
   - **Hotel Name:** Name only
   - **Hotel Address:** Exact street, locality, landmark, state, and PIN code from dataset (with duplicate city safely removed)
   - **City / Location:** Independent destination city indicator
3. **External Booking Platform Integration:**
   - Instead of hosting an internal booking database or collecting user payment credentials, the system discovers and links to the 4 leading travel platforms:
     - **MakeMyTrip** (`https://www.makemytrip.com/hotels/hotel-listing/?searchText=...`)
     - **Goibibo** (`https://www.goibibo.com/hotels/find-hotels-in-any/?searchText=...`)
     - **Booking.com** (`https://www.booking.com/searchresults.html?ss=...`)
     - **Agoda** (`https://www.agoda.com/search?text=...`)
   - Each platform link is prefilled with a query combining the hotel name, destination city, and landmark.
   - All links open safely in a new browser tab (`target="_blank" rel="noopener noreferrer"`).
   - Clear disclosure notes ensure users understand bookings are completed directly on the external partner's website.

---

## 🧠 Recommendation Flow & Scoring Formula

$$\text{User Preferences} \rightarrow \text{TF-IDF Similarity} + \text{Aspect Match} + \text{Smoothed Sentiment} + \text{Smoothed Rating} \rightarrow \text{Ranking}$$

$$\text{Recommendation Score} = 0.35 \times \text{Similarity} + 0.25 \times \text{Aspect Match} + 0.20 \times \text{Smoothed Sentiment} + 0.20 \times \text{Rating Score}$$

### Key Features:
- **Aspect-Based Sentiment Extraction:** 9 hospitality aspects (Cleanliness, Room, Staff, Service, Food, Location, Price, Facilities, Comfort).
- **Graceful Fallback Mode:** Relaxes one constraint at a time if exact search criteria yield zero results, with full transparency to the user.
- **Location Normalization:** Smart location handling (e.g. "Delhi" seamlessly matches "Delhi_Transit").
- **Client-Side Sorting:** Sort recommendations dynamically by Best Match, Highest Rated, Lowest Price, or Highest Sentiment without re-querying backend.

---

## 📡 API Endpoints

### 1. `POST /recommend`
Generates personalized hotel recommendations based on constraints and free-form preference text. Returns hotel metadata along with external booking platform search URLs.

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
Detailed hotel profile page showing exact dataset address, aspect-wise feedback bars, ML sentiment breakdown, verified "Why Recommended" reasons, external booking options with pre-filled platform search links, and paginated customer reviews.

### 3. `GET /api/hotel/<int:hotel_id>/reviews`
REST endpoint returning paginated customer reviews with sentiment filtering (`?page=1&per_page=10&sentiment=positive`).

### 4. `GET /health`
System health check returning indexed review count (192,015), hotel count (2,775), and covered Indian locations (251).
