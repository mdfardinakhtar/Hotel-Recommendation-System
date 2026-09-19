/**
 * Indian Hotel Recommendation System - Frontend Controller
 * Handles async recommendations, client-side sorting, quick suggestions,
 * and expandable review explanations.
 */

// Global state for client-side sorting and navigation context
let currentHotels = [];
let currentPreference = "";

// Map selectable UI options to keywords/phrases aligned with existing backend aspect matching
const PREFERENCE_MAP = {
    "clean_room": { label: "Clean Room", phrase: "clean room cleanliness" },
    "friendly_staff": { label: "Friendly Staff", phrase: "friendly staff" },
    "good_food": { label: "Good Food", phrase: "good food" },
    "comfortable_room": { label: "Comfortable Room", phrase: "comfortable room comfort" },
    "good_cleanliness": { label: "Good Cleanliness", phrase: "cleanliness clean" },
    "affordable": { label: "Affordable", phrase: "affordable price" },
    "good_location": { label: "Good Location", phrase: "good location" },
    "good_service": { label: "Good Service", phrase: "good service" },
    "family_friendly": { label: "Family Friendly", phrase: "family friendly" },
    "good_facilities": { label: "Good Facilities", phrase: "good facilities" }
};

// Set tracking active selected preference keys
const selectedPreferences = new Set();

function togglePreference(key) {
    if (!PREFERENCE_MAP[key]) return;

    const btn = document.querySelector(`.pref-card[data-key="${key}"]`);

    if (selectedPreferences.has(key)) {
        selectedPreferences.delete(key);
        if (btn) btn.classList.remove("selected");
    } else {
        selectedPreferences.add(key);
        if (btn) btn.classList.add("selected");
    }

    updatePreferenceState();
}

function clearAllPreferences() {
    selectedPreferences.clear();
    document.querySelectorAll(".pref-card").forEach(btn => btn.classList.remove("selected"));
    updatePreferenceState();
}

function updatePreferenceState() {
    const clearBtn = document.getElementById("clear-pref-btn");
    if (clearBtn) {
        if (selectedPreferences.size > 0) {
            clearBtn.classList.remove("hidden");
        } else {
            clearBtn.classList.add("hidden");
        }
    }

    const prefInput = document.getElementById("preference");
    if (prefInput) {
        if (selectedPreferences.size > 0) {
            const phrases = Array.from(selectedPreferences).map(k => PREFERENCE_MAP[k].phrase);
            prefInput.value = phrases.join(" ");
        } else {
            prefInput.value = "";
        }
    }
}

function applyQuickPref(text) {
    clearAllPreferences();
    const lower = text.toLowerCase();
    for (const [key, item] of Object.entries(PREFERENCE_MAP)) {
        if (lower.includes(item.label.toLowerCase()) || lower.includes(key.replace("_", " "))) {
            togglePreference(key);
        }
    }
    const prefInput = document.getElementById("preference");
    if (prefInput) prefInput.value = text;
}

async function getRecommendations() {
    const searchBtn = document.getElementById("search-btn");
    const loadingState = document.getElementById("loading-state");
    const fallbackBanner = document.getElementById("fallback-banner");
    const emptyState = document.getElementById("empty-state");
    const errorState = document.getElementById("error-state");
    const resultsWrapper = document.getElementById("results-wrapper");
    const resultsGrid = document.getElementById("results-grid");
    const fallbackMessage = document.getElementById("fallback-message");
    const fallbackTitle = document.getElementById("fallback-title");
    const detectedAspectsText = document.getElementById("detected-aspects-text");
    const resultsCountTitle = document.getElementById("results-count-title");
    const sortBySelect = document.getElementById("sort-by");

    // Gather form input values
    const location = document.getElementById("location").value;
    const budget = document.getElementById("budget").value;
    const minRating = document.getElementById("min_rating").value;

    // Convert selected preferences into backend-compatible semantic query string
    let preference = "";
    if (selectedPreferences.size > 0) {
        const phrases = Array.from(selectedPreferences).map(k => PREFERENCE_MAP[k].phrase);
        preference = phrases.join(" ");
    } else {
        const prefInput = document.getElementById("preference");
        preference = prefInput ? prefInput.value.trim() : "";
    }

    currentPreference = preference;

    const requestData = {
        location: location,
        budget: budget,
        min_rating: minRating,
        preference: preference
    };

    // UI Loading state transition
    searchBtn.disabled = true;
    loadingState.classList.remove("hidden");
    fallbackBanner.classList.add("hidden");
    emptyState.classList.add("hidden");
    errorState.classList.add("hidden");
    resultsWrapper.classList.add("hidden");
    resultsGrid.innerHTML = "";

    try {
        const response = await fetch("/recommend", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            throw new Error(`Server returned HTTP ${response.status}`);
        }

        const result = await response.json();
        loadingState.classList.add("hidden");
        searchBtn.disabled = false;

        // Check if fallback relaxation was triggered
        if (result.is_relaxed && result.message) {
            fallbackTitle.textContent = result.relaxed_filter 
                ? `Filter Relaxed: ${result.relaxed_filter.toUpperCase()}`
                : "Search Filters Relaxed";
            fallbackMessage.textContent = result.message;
            fallbackBanner.classList.remove("hidden");
        }

        // Empty state check
        if (!result.success || !result.hotels || result.hotels.length === 0) {
            emptyState.classList.remove("hidden");
            return;
        }

        // Store state for frontend sorting
        currentHotels = result.hotels;

        // Display results metadata
        const aspectList = result.detected_aspects && result.detected_aspects.length > 0
            ? result.detected_aspects.join(", ")
            : "general hospitality";
        
        detectedAspectsText.textContent = `Targeted aspects detected from your preference: ${aspectList}`;
        resultsCountTitle.textContent = `Top ${result.hotels.length} Hotel Recommendations`;

        // Reset sort select to recommended
        if (sortBySelect) {
            sortBySelect.value = "recommended";
        }

        // Render cards
        renderHotelCards(currentHotels);
        resultsWrapper.classList.remove("hidden");

    } catch (error) {
        console.error("Recommendation request failed:", error);
        loadingState.classList.add("hidden");
        searchBtn.disabled = false;
        const errMsg = document.getElementById("error-message");
        if (errMsg) {
            errMsg.textContent = `Could not load recommendations: ${error.message}. Ensure the Flask server is running.`;
        }
        errorState.classList.remove("hidden");
    }
}

function handleSortChange() {
    const sortBy = document.getElementById("sort-by").value;
    if (!currentHotels || currentHotels.length === 0) return;

    let sortedList = [...currentHotels];

    if (sortBy === "recommended") {
        sortedList.sort((a, b) => (b.score || 0) - (a.score || 0));
    } else if (sortBy === "rating") {
        sortedList.sort((a, b) => (b.rating || 0) - (a.rating || 0));
    } else if (sortBy === "price") {
        sortedList.sort((a, b) => {
            const priceA = a.price !== null ? a.price : 999999;
            const priceB = b.price !== null ? b.price : 999999;
            return priceA - priceB;
        });
    } else if (sortBy === "sentiment") {
        sortedList.sort((a, b) => (b.sentiment || 0) - (a.sentiment || 0));
    }

    renderHotelCards(sortedList);
}

function toggleWhyAccordion(index) {
    const body = document.getElementById(`why-body-${index}`);
    const icon = document.getElementById(`why-icon-${index}`);
    if (body) {
        if (body.classList.contains("hidden")) {
            body.classList.remove("hidden");
            if (icon) icon.textContent = "▲";
        } else {
            body.classList.add("hidden");
            if (icon) icon.textContent = "▼";
        }
    }
}

function renderHotelCards(hotels) {
    const container = document.getElementById("results-grid");
    container.innerHTML = "";

    hotels.forEach((hotel, idx) => {
        const card = document.createElement("article");
        card.className = "hotel-card";

        const priceText = hotel.price !== null 
            ? `₹${Number(hotel.price).toLocaleString("en-IN")}` 
            : "Price on Request";

        const ratingText = hotel.rating !== null ? `${hotel.rating} / 5` : "N/A";
        const sentimentText = hotel.sentiment !== null ? `${hotel.sentiment}% Positive` : "N/A";
        const aspectMatchText = `${hotel.aspect_match}% Aspect Match`;
        const similarityText = `${hotel.similarity}% Similarity`;
        const scoreText = `${hotel.score}%`;

        // Reasons HTML list
        let reasonsHtml = "";
        if (hotel.why_recommended && hotel.why_recommended.length > 0) {
            reasonsHtml = hotel.why_recommended.map(r => `
                <li><span class="check">✓</span> <span>${escapeHtml(r)}</span></li>
            `).join("");
        } else {
            reasonsHtml = `<li><span class="check">✓</span> <span>Strong alignment with requested preference keywords.</span></li>`;
        }

        // Details URL with context parameters
        const detailsUrl = `/hotel/${hotel.hotel_id}?score=${hotel.score}&similarity=${hotel.similarity}&aspect_match=${hotel.aspect_match}&pref=${encodeURIComponent(currentPreference)}`;

        card.innerHTML = `
            <div>
                <div class="card-top-row">
                    <h3 class="hotel-name">${escapeHtml(hotel.name)}</h3>
                    <span class="score-badge" title="Combined recommendation score">Score: ${scoreText}</span>
                </div>

                <div class="hotel-location">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                        <circle cx="12" cy="10" r="3"></circle>
                    </svg>
                    <span>${escapeHtml(hotel.location)}</span>
                </div>

                <div class="card-metric-row">
                    <div class="card-price-box">
                        <span class="card-price">${priceText}</span>
                        <span class="card-price-sub">/ night</span>
                    </div>
                    <div class="card-rating-box">
                        <span>★</span>
                        <span>${ratingText}</span>
                    </div>
                </div>

                <div class="card-tags-row">
                    <span class="tag-badge tag-sentiment">✓ ${sentimentText}</span>
                    <span class="tag-badge tag-aspect">✓ ${aspectMatchText}</span>
                    <span class="tag-badge tag-reviews">${hotel.reviews} reviews</span>
                </div>

                <div class="why-accordion">
                    <div class="why-toggle" onclick="toggleWhyAccordion(${idx})">
                        <span>Why recommended?</span>
                        <span id="why-icon-${idx}">▼</span>
                    </div>
                    <div id="why-body-${idx}" class="why-body hidden">
                        <ul>${reasonsHtml}</ul>
                    </div>
                </div>
            </div>

            <div class="card-footer-action">
                <a href="${detailsUrl}" class="card-action-btn">
                    View Details & Review Insights &rarr;
                </a>
            </div>
        `;

        container.appendChild(card);
    });
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
