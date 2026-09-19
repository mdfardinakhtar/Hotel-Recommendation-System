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

// ==========================================================================
// Destination City Searchable Autocomplete State & Controller
// ==========================================================================
let selectedCityValue = "";
let selectedCityLabel = "";
let filteredCities = [];
let focusedCityIndex = -1;
let isCityDropdownOpen = false;

function initCityAutocomplete() {
    filteredCities = Array.isArray(window.SERVER_LOCATIONS) ? [...window.SERVER_LOCATIONS] : [];
    
    // Check if hidden location input or search input already has a value
    const hiddenInput = document.getElementById("location");
    const searchInput = document.getElementById("city-search-input");
    const clearBtn = document.getElementById("clear-city-btn");
    
    if (hiddenInput && hiddenInput.value) {
        selectedCityValue = hiddenInput.value;
        const match = findCityMatch(hiddenInput.value);
        if (match) {
            selectedCityLabel = match.label;
            if (searchInput) searchInput.value = match.label;
            if (clearBtn) clearBtn.classList.remove("hidden");
        }
    }
    
    renderCityDropdownList();

    // Close dropdown when clicking anywhere outside the city autocomplete group
    document.addEventListener("click", function(e) {
        const group = document.querySelector(".city-autocomplete-group");
        if (group && !group.contains(e.target)) {
            closeCityDropdown();
        }
    });
}

function handleCitySearchInput(query) {
    const rawQuery = (query || "").trim();
    const qLower = rawQuery.toLowerCase();
    const clearBtn = document.getElementById("clear-city-btn");
    
    // Toggle clear button based on text presence
    if (clearBtn) {
        if (rawQuery.length > 0) {
            clearBtn.classList.remove("hidden");
        } else {
            clearBtn.classList.add("hidden");
        }
    }
    
    if (!qLower) {
        filteredCities = Array.isArray(window.SERVER_LOCATIONS) ? [...window.SERVER_LOCATIONS] : [];
        selectedCityValue = "";
        selectedCityLabel = "";
        const hiddenInput = document.getElementById("location");
        if (hiddenInput) hiddenInput.value = "";
    } else {
        const allLocs = Array.isArray(window.SERVER_LOCATIONS) ? window.SERVER_LOCATIONS : [];
        filteredCities = allLocs.filter(item => {
            const label = (item.label || "").toLowerCase();
            const val = (item.value || "").toLowerCase();
            const normalizedVal = val.replace(/_/g, " ");

            // Match if query is in label or dataset value
            if (label.includes(qLower) || val.includes(qLower) || normalizedVal.includes(qLower)) {
                return true;
            }

            // Delhi tolerance: 'del' / 'delhi' matches 'Delhi (Transit)'
            if (qLower.startsWith("del") && (label.includes("delhi") || val.includes("delhi"))) {
                return true;
            }

            return false;
        });

        // If user query exactly matches a city, update hidden input
        const exactMatch = findCityMatch(rawQuery);
        const hiddenInput = document.getElementById("location");
        if (exactMatch && (exactMatch.label.toLowerCase() === qLower || exactMatch.value.toLowerCase() === qLower)) {
            hiddenInput.value = exactMatch.value;
            selectedCityValue = exactMatch.value;
        } else if (hiddenInput) {
            if (selectedCityLabel && !selectedCityLabel.toLowerCase().includes(qLower)) {
                hiddenInput.value = "";
                selectedCityValue = "";
            }
        }
    }

    focusedCityIndex = -1;
    openCityDropdown();
    renderCityDropdownList(rawQuery);
}

function renderCityDropdownList(query = "") {
    const listContainer = document.getElementById("city-dropdown-list");
    if (!listContainer) return;

    if (!filteredCities || filteredCities.length === 0) {
        listContainer.innerHTML = `<div class="city-no-match">No city found</div>`;
        return;
    }

    const qLower = (query || "").trim().toLowerCase();

    listContainer.innerHTML = filteredCities.map((item, idx) => {
        const isSelected = item.value === selectedCityValue && selectedCityValue !== "";
        const isFocused = idx === focusedCityIndex;
        let classes = "city-option";
        if (isSelected) classes += " selected";
        if (isFocused) classes += " focused";

        // Highlight matching query string in label
        let displayHtml = escapeHtml(item.label);
        if (qLower && item.label) {
            const startIdx = item.label.toLowerCase().indexOf(qLower);
            if (startIdx >= 0) {
                const before = escapeHtml(item.label.substring(0, startIdx));
                const matchText = escapeHtml(item.label.substring(startIdx, startIdx + qLower.length));
                const after = escapeHtml(item.label.substring(startIdx + qLower.length));
                displayHtml = `${before}<span class="city-option-highlight">${matchText}</span>${after}`;
            }
        }

        const checkMark = isSelected ? `<span class="city-option-check">✓</span>` : "";

        return `
            <div class="${classes}" 
                 role="option" 
                 aria-selected="${isSelected}"
                 data-index="${idx}"
                 onclick="selectCity('${escapeAttr(item.value)}', '${escapeAttr(item.label)}')">
                <span>${displayHtml}</span>
                ${checkMark}
            </div>
        `;
    }).join("");
}

function selectCity(value, label) {
    selectedCityValue = value;
    selectedCityLabel = label;

    const hiddenInput = document.getElementById("location");
    const searchInput = document.getElementById("city-search-input");
    const clearBtn = document.getElementById("clear-city-btn");

    if (hiddenInput) hiddenInput.value = value;
    if (searchInput) {
        searchInput.value = label;
    }
    if (clearBtn) {
        if (value || (label && label !== "All India (Search Everywhere)")) {
            clearBtn.classList.remove("hidden");
        } else {
            clearBtn.classList.add("hidden");
        }
    }

    closeCityDropdown();
}

function clearSelectedCity() {
    selectedCityValue = "";
    selectedCityLabel = "";
    const hiddenInput = document.getElementById("location");
    const searchInput = document.getElementById("city-search-input");
    const clearBtn = document.getElementById("clear-city-btn");

    if (hiddenInput) hiddenInput.value = "";
    if (searchInput) {
        searchInput.value = "";
        searchInput.focus();
    }
    if (clearBtn) clearBtn.classList.add("hidden");

    filteredCities = Array.isArray(window.SERVER_LOCATIONS) ? [...window.SERVER_LOCATIONS] : [];
    focusedCityIndex = -1;
    renderCityDropdownList("");
    openCityDropdown();
}

function openCityDropdown() {
    const menu = document.getElementById("city-dropdown-menu");
    const wrapper = document.querySelector(".city-input-wrapper");
    if (menu) menu.classList.remove("hidden");
    if (wrapper) wrapper.classList.add("open");
    isCityDropdownOpen = true;

    if (!filteredCities || filteredCities.length === 0) {
        filteredCities = Array.isArray(window.SERVER_LOCATIONS) ? [...window.SERVER_LOCATIONS] : [];
        renderCityDropdownList(document.getElementById("city-search-input")?.value || "");
    }
}

function closeCityDropdown() {
    const menu = document.getElementById("city-dropdown-menu");
    const wrapper = document.querySelector(".city-input-wrapper");
    if (menu) menu.classList.add("hidden");
    if (wrapper) wrapper.classList.remove("open");
    isCityDropdownOpen = false;
    focusedCityIndex = -1;
}

function toggleCityDropdown(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    if (isCityDropdownOpen) {
        closeCityDropdown();
    } else {
        const input = document.getElementById("city-search-input");
        if (input) input.focus();
        openCityDropdown();
    }
}

function handleCityKeydown(e) {
    if (!isCityDropdownOpen) {
        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
            openCityDropdown();
            e.preventDefault();
            return;
        }
    }

    if (e.key === "ArrowDown") {
        e.preventDefault();
        if (filteredCities.length === 0) return;
        focusedCityIndex = Math.min(focusedCityIndex + 1, filteredCities.length - 1);
        renderCityDropdownList(document.getElementById("city-search-input")?.value || "");
        scrollFocusedCityIntoView();
    } else if (e.key === "ArrowUp") {
        e.preventDefault();
        if (filteredCities.length === 0) return;
        focusedCityIndex = Math.max(focusedCityIndex - 1, 0);
        renderCityDropdownList(document.getElementById("city-search-input")?.value || "");
        scrollFocusedCityIntoView();
    } else if (e.key === "Enter") {
        if (isCityDropdownOpen) {
            if (focusedCityIndex >= 0 && focusedCityIndex < filteredCities.length) {
                e.preventDefault();
                const target = filteredCities[focusedCityIndex];
                selectCity(target.value, target.label);
            } else if (filteredCities.length === 1) {
                e.preventDefault();
                const target = filteredCities[0];
                selectCity(target.value, target.label);
            } else {
                closeCityDropdown();
            }
        }
    } else if (e.key === "Escape") {
        closeCityDropdown();
        e.preventDefault();
    } else if (e.key === "Tab") {
        closeCityDropdown();
    }
}

function scrollFocusedCityIntoView() {
    const focusedEl = document.querySelector(".city-option.focused");
    if (focusedEl) {
        focusedEl.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
}

function findCityMatch(str) {
    if (!str || !window.SERVER_LOCATIONS) return null;
    const q = str.trim().toLowerCase();
    const locs = window.SERVER_LOCATIONS;

    // 1. Exact value match
    let match = locs.find(loc => loc.value && loc.value.toLowerCase() === q);
    if (match) return match;

    // 2. Exact label match
    match = locs.find(loc => loc.label && loc.label.toLowerCase() === q);
    if (match) return match;

    // 3. Delhi variations
    if (q === "delhi" || q === "new delhi" || q === "delhi transit" || q === "delhi (transit)") {
        match = locs.find(loc => loc.value === "Delhi_Transit");
        if (match) return match;
    }

    // 4. Starts-with match
    match = locs.find(loc => loc.label && loc.label.toLowerCase().startsWith(q));
    if (match) return match;

    // 5. Value starts-with
    match = locs.find(loc => loc.value && loc.value.toLowerCase().startsWith(q));
    if (match) return match;

    // 6. Substring contains
    match = locs.find(loc => loc.label && loc.label.toLowerCase().includes(q));
    if (match) return match;

    return null;
}

function escapeAttr(str) {
    if (!str) return "";
    return String(str).replace(/'/g, "\\'").replace(/"/g, "&quot;");
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
    let location = document.getElementById("location") ? document.getElementById("location").value.trim() : "";
    const searchInput = document.getElementById("city-search-input");
    if (!location && searchInput && searchInput.value.trim()) {
        const textVal = searchInput.value.trim();
        const match = findCityMatch(textVal);
        if (match) {
            location = match.value;
            if (document.getElementById("location")) document.getElementById("location").value = match.value;
        } else {
            location = textVal;
        }
    }
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
                    <div class="hotel-title-group">
                        <h3 class="hotel-name">${escapeHtml(hotel.name)}</h3>
                        <div class="hotel-address">
                            <span class="addr-pin">📍</span>
                            <span class="addr-text">${escapeHtml(hotel.address || "Address not available")}</span>
                        </div>
                        <div class="hotel-location">${escapeHtml(hotel.city || (hotel.location === 'Delhi_Transit' ? 'Delhi (Transit)' : hotel.location.replace(/_/g, ' ')))}</div>
                    </div>
                    <span class="score-badge" title="Combined recommendation score">Score: ${scoreText}</span>
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

// Initialize city autocomplete component when DOM is loaded
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initCityAutocomplete);
} else {
    initCityAutocomplete();
}
