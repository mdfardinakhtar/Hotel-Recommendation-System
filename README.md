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

Run the automated test suite to validate recommendation quality, constraint filtering, graceful fallback, and data integrity:
```bash
python test_recommendations.py
```

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
Detailed hotel profile page showing aspect-wise feedback bars, ML sentiment breakdown (Positive vs Negative), verified "Why Recommended" reasons, and paginated authentic customer reviews.

### 3. `GET /api/hotel/<int:hotel_id>/reviews`
REST endpoint returning paginated customer reviews with sentiment filtering (`?page=1&per_page=10&sentiment=positive`).

### 4. `GET /health`
System health check returning indexed review count, hotel count, and covered Indian locations.
