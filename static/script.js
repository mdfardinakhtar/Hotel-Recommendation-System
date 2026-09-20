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
        updateTopBackButton(true);
        saveSearchState();

        if (window.location.hash !== "#results") {
            history.pushState({ step: "results" }, "", "#results");
        }

        resultsWrapper.scrollIntoView({ behavior: "smooth", block: "start" });
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
    saveSearchState();
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

function formatAddressForDisplay(address, city, location) {
    if (!address || address === "Address not available") return address || "Address not available";
    const cityVariants = [];
    if (city) {
        const cClean = String(city).trim();
        if (cClean && !cityVariants.includes(cClean)) cityVariants.push(cClean);
        if (cClean.includes(" (Transit)")) {
            const sub = cClean.replace(" (Transit)", "").trim();
            if (sub && !cityVariants.includes(sub)) cityVariants.push(sub);
        }
    }
    if (location) {
        const locStr = String(location).trim();
        if (locStr && !cityVariants.includes(locStr)) cityVariants.push(locStr);
        const locClean = locStr.replace(/_/g, " ").trim();
        if (locClean && !cityVariants.includes(locClean)) cityVariants.push(locClean);
        if (locStr === "Delhi_Transit" && !cityVariants.includes("Delhi")) cityVariants.push("Delhi");
    }
    cityVariants.sort((a, b) => b.length - a.length);

    let formatted = address;
    for (const v of cityVariants) {
        if (!v) continue;
        const esc = v.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        formatted = formatted.replace(new RegExp(`,\\s*${esc}\\s*,`, 'gi'), ',');
        formatted = formatted.replace(new RegExp(`,\\s*${esc}\\s*$`, 'gi'), '');
        formatted = formatted.replace(new RegExp(`^\\s*${esc}\\s*,\\s*`, 'gi'), '');
        formatted = formatted.replace(new RegExp(`\\s*\\(\\s*${esc}\\s*\\)`, 'gi'), '');
    }
    formatted = formatted.replace(/,\s*,+/g, ',');
    formatted = formatted.replace(/,\s*/g, ', ');
    formatted = formatted.replace(/^\s*,\s*/g, '');
    formatted = formatted.replace(/\s*,\s*$/g, '').trim();
    return formatted || "Address not available";
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

        const ratingVal = hotel.rating !== null ? `${hotel.rating}` : "N/A";
        const sentimentVal = hotel.sentiment !== null ? `${hotel.sentiment}%` : "N/A";
        const aspectMatchVal = `${hotel.aspect_match}%`;
        const similarityVal = `${hotel.similarity}%`;
        const scoreVal = `${hotel.score}%`;
        const displayAddress = formatAddressForDisplay(hotel.address, hotel.city, hotel.location);
        const displayCity = hotel.city || (hotel.location === 'Delhi_Transit' ? 'Delhi' : hotel.location.replace(/_/g, ' '));

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

        // External booking platform buttons (5 platforms)
        let platformsHtml = "";
        if (hotel.booking_platforms && hotel.booking_platforms.length > 0) {
            const buttonsHtml = hotel.booking_platforms.map(p => `
                <a href="${escapeAttr(p.url)}" 
                   target="_blank" 
                   rel="noopener noreferrer" 
                   class="card-platform-search-btn platform-btn-${escapeAttr(p.id)}" 
                   title="Search for ${escapeAttr(hotel.name)} on ${escapeAttr(p.name)}">
                    <span class="platform-dot" style="background:${p.bg_color || '#2563eb'}"></span>
                    <span class="platform-btn-name">${escapeHtml(p.button_text || `Search on ${p.name}`)}</span>
                    <svg class="platform-ext-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                        <polyline points="15 3 21 3 21 9"></polyline>
                        <line x1="10" y1="14" x2="21" y2="3"></line>
                    </svg>
                </a>
            `).join("");

            platformsHtml = `
                <div class="card-booking-discovery">
                    <div class="card-discovery-header">
                        <h4 class="card-discovery-title">Where can I find this hotel?</h4>
                        <span class="card-discovery-badge">External Search</span>
                    </div>
                    <div class="card-platform-btn-grid">
                        ${buttonsHtml}
                    </div>
                    <div class="card-discovery-disclaimers">
                        <p class="card-disclaimer-item">Your booking will be completed on the selected booking platform. Prices and availability may vary.</p>
                    </div>
                </div>
            `;
        }

        card.innerHTML = `
            <!-- 1. HOTEL NAME -->
            <div class="card-header-section">
                <h3 class="hotel-name">${escapeHtml(hotel.name)}</h3>
            </div>

            <!-- 2. FULL HOTEL ADDRESS -->
            <div class="hotel-address">
                <span class="addr-pin">📍</span>
                <span class="addr-text">${escapeHtml(displayAddress)}</span>
            </div>

            <!-- 3. CITY / LOCATION -->
            <div class="hotel-location">${escapeHtml(displayCity)}</div>

            <!-- 4. PRICE -->
            <div class="card-price-row">
                <span class="card-price">${priceText}</span>
                <span class="card-price-sub">/ night</span>
            </div>

            <!-- 5. RATING & REVIEW COUNT -->
            <div class="card-rating-row">
                <span class="card-rating-pill">★ ${ratingVal} Rating</span>
                <span class="card-reviews-count">${hotel.reviews} reviews</span>
            </div>

            <!-- 6. KEY METRICS: SENTIMENT, PREFERENCE MATCH, ASPECT MATCH, REC SCORE -->
            <div class="card-metrics-grid">
                <div class="card-metric-item">
                    <span class="metric-val text-pos">${sentimentVal} Positive</span>
                </div>
                <div class="card-metric-item">
                    <span class="metric-val text-pref">${similarityVal} Preference Match</span>
                </div>
                <div class="card-metric-item">
                    <span class="metric-val text-aspect">${aspectMatchVal} Aspect Match</span>
                </div>
                <div class="card-metric-item metric-score-item">
                    <span class="metric-label">Score:</span>
                    <span class="metric-val score-highlight">${scoreVal}</span>
                </div>
            </div>

            <!-- 7. WHY RECOMMENDED ACCORDION -->
            <div class="why-accordion">
                <div class="why-toggle" onclick="toggleWhyAccordion(${idx})">
                    <span>Why recommended?</span>
                    <span id="why-icon-${idx}">▼</span>
                </div>
                <div id="why-body-${idx}" class="why-body hidden">
                    <ul>${reasonsHtml}</ul>
                </div>
            </div>

            <!-- 8. VIEW DETAILS BUTTON -->
            <div class="card-action-primary">
                <a href="${detailsUrl}" class="btn-view-details">
                    <span>View Details</span>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                        <polyline points="12 5 19 12 12 19"></polyline>
                    </svg>
                </a>
            </div>

            <!-- 9. WHERE CAN I FIND THIS HOTEL? PLATFORM DISCOVERY SECTION -->
            ${platformsHtml}
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

// ==========================================================================
// Navigation History & State Preservation Controller
// ==========================================================================

function updateTopBackButton(show) {
    const topBackBtn = document.getElementById("top-back-btn");
    if (topBackBtn) {
        if (show) {
            topBackBtn.classList.remove("hidden");
        } else {
            topBackBtn.classList.add("hidden");
        }
    }
}

function saveSearchState() {
    try {
        const state = {
            cityValue: selectedCityValue,
            cityLabel: selectedCityLabel,
            cityInput: document.getElementById("city-search-input")?.value || "",
            budget: document.getElementById("budget")?.value || "",
            minRating: document.getElementById("min_rating")?.value || "",
            selectedPreferences: Array.from(selectedPreferences),
            currentPreference: currentPreference,
            hotels: currentHotels,
            aspectsText: document.getElementById("detected-aspects-text")?.textContent || "",
            resultsCountText: document.getElementById("results-count-title")?.textContent || "",
            isRelaxed: !document.getElementById("fallback-banner")?.classList.contains("hidden"),
            fallbackTitle: document.getElementById("fallback-title")?.textContent || "",
            fallbackMessage: document.getElementById("fallback-message")?.textContent || "",
            sortBy: document.getElementById("sort-by")?.value || "recommended",
            hasResults: true
        };
        sessionStorage.setItem("hotel_recommendation_search_state", JSON.stringify(state));
    } catch (e) {
        console.warn("Could not persist search state to sessionStorage:", e);
    }
}

function restoreSearchStateIfPresent() {
    try {
        const raw = sessionStorage.getItem("hotel_recommendation_search_state");
        if (!raw) return false;
        const state = JSON.parse(raw);
        if (!state || !state.hasResults || !state.hotels || state.hotels.length === 0) return false;

        // Restore city selection
        if (state.cityValue) {
            selectCity(state.cityValue, state.cityLabel || state.cityValue);
        } else if (state.cityInput) {
            const searchInput = document.getElementById("city-search-input");
            if (searchInput) searchInput.value = state.cityInput;
        }

        // Restore budget
        const budgetInput = document.getElementById("budget");
        if (budgetInput && state.budget !== undefined) {
            budgetInput.value = state.budget;
        }

        // Restore min rating
        const minRatingSelect = document.getElementById("min_rating");
        if (minRatingSelect && state.minRating !== undefined) {
            minRatingSelect.value = state.minRating;
        }

        // Restore preference chips
        clearAllPreferences();
        if (Array.isArray(state.selectedPreferences)) {
            state.selectedPreferences.forEach(key => togglePreference(key));
        }

        // Restore current preference
        currentPreference = state.currentPreference || "";
        const prefInput = document.getElementById("preference");
        if (prefInput) prefInput.value = currentPreference;

        // Restore metadata
        const detectedAspectsText = document.getElementById("detected-aspects-text");
        const resultsCountTitle = document.getElementById("results-count-title");
        if (detectedAspectsText && state.aspectsText) detectedAspectsText.textContent = state.aspectsText;
        if (resultsCountTitle && state.resultsCountText) resultsCountTitle.textContent = state.resultsCountText;

        // Restore fallback banner if active
        const fallbackBanner = document.getElementById("fallback-banner");
        const fallbackTitle = document.getElementById("fallback-title");
        const fallbackMessage = document.getElementById("fallback-message");
        if (state.isRelaxed && fallbackBanner) {
            if (fallbackTitle && state.fallbackTitle) fallbackTitle.textContent = state.fallbackTitle;
            if (fallbackMessage && state.fallbackMessage) fallbackMessage.textContent = state.fallbackMessage;
            fallbackBanner.classList.remove("hidden");
        } else if (fallbackBanner) {
            fallbackBanner.classList.add("hidden");
        }

        // Restore sort selection
        const sortBySelect = document.getElementById("sort-by");
        if (sortBySelect && state.sortBy) {
            sortBySelect.value = state.sortBy;
        }

        // Restore hotels list
        currentHotels = state.hotels;

        // Render cards
        if (state.sortBy && state.sortBy !== "recommended") {
            handleSortChange();
        } else {
            renderHotelCards(currentHotels);
        }

        // Reveal results and top Back button
        const resultsWrapper = document.getElementById("results-wrapper");
        if (resultsWrapper) {
            resultsWrapper.classList.remove("hidden");
        }
        updateTopBackButton(true);

        return true;
    } catch (err) {
        console.warn("Could not restore search state:", err);
        return false;
    }
}

function handleGoBack() {
    const resultsWrapper = document.getElementById("results-wrapper");
    const isResultsVisible = resultsWrapper && !resultsWrapper.classList.contains("hidden");

    if (isResultsVisible) {
        // If results are open, going Back takes the user to the Search form
        if (window.location.hash === "#results") {
            window.history.back();
        } else {
            showSearchView();
        }
    } else {
        // If already at Search page, check browser history or fallback to home
        if (document.referrer && (document.referrer.indexOf(window.location.host) !== -1 || document.referrer.startsWith(window.location.origin))) {
            window.history.back();
        } else if (window.history.length > 1) {
            window.history.back();
        } else {
            window.location.href = "/";
        }
    }
}

function showSearchView() {
    const resultsWrapper = document.getElementById("results-wrapper");
    const fallbackBanner = document.getElementById("fallback-banner");
    const emptyState = document.getElementById("empty-state");
    const errorState = document.getElementById("error-state");

    if (resultsWrapper) resultsWrapper.classList.add("hidden");
    if (fallbackBanner) fallbackBanner.classList.add("hidden");
    if (emptyState) emptyState.classList.add("hidden");
    if (errorState) errorState.classList.add("hidden");
    updateTopBackButton(false);

    if (window.location.hash === "#results") {
        history.replaceState({ step: "search" }, "", window.location.pathname);
    }

    const searchCard = document.querySelector(".search-card");
    if (searchCard) {
        searchCard.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

function resetSearchFlow() {
    // Hide results and message banners
    const resultsWrapper = document.getElementById("results-wrapper");
    const fallbackBanner = document.getElementById("fallback-banner");
    const emptyState = document.getElementById("empty-state");
    const errorState = document.getElementById("error-state");

    if (resultsWrapper) resultsWrapper.classList.add("hidden");
    if (fallbackBanner) fallbackBanner.classList.add("hidden");
    if (emptyState) emptyState.classList.add("hidden");
    if (errorState) errorState.classList.add("hidden");
    updateTopBackButton(false);

    // Clear saved session storage
    try {
        sessionStorage.removeItem("hotel_recommendation_search_state");
    } catch (e) {}

    // Reset location & city input
    clearSelectedCity();

    // Reset budget input
    const budgetInput = document.getElementById("budget");
    if (budgetInput) budgetInput.value = "";

    // Reset rating select
    const minRatingSelect = document.getElementById("min_rating");
    if (minRatingSelect) minRatingSelect.value = "any";

    // Reset preference chips
    clearAllPreferences();
    currentPreference = "";
    const prefInput = document.getElementById("preference");
    if (prefInput) prefInput.value = "";

    // Reset current hotels array
    currentHotels = [];

    // Reset URL hash
    if (window.location.hash === "#results") {
        try {
            history.pushState(null, "", window.location.pathname);
        } catch (e) {}
    }

    // Scroll to the search form
    const searchCard = document.querySelector(".search-card");
    if (searchCard) {
        searchCard.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

// Popstate listener for browser back/forward navigation
window.addEventListener("popstate", function(event) {
    if (event.state && event.state.step === "results") {
        restoreSearchStateIfPresent();
    } else if (window.location.hash === "#results") {
        restoreSearchStateIfPresent();
    } else {
        showSearchView();
    }
});

// Pageshow listener for bfcache restoration
window.addEventListener("pageshow", function(event) {
    if (window.location.hash === "#results") {
        const resultsWrapper = document.getElementById("results-wrapper");
        if (!resultsWrapper || resultsWrapper.classList.contains("hidden") || !currentHotels || currentHotels.length === 0) {
            restoreSearchStateIfPresent();
        } else {
            updateTopBackButton(true);
        }
    }
});

function initApp() {
    initCityAutocomplete();
    // If arriving with #results hash or returning from details page
    if (window.location.hash === "#results") {
        restoreSearchStateIfPresent();
    }
}

// Initialize application when DOM is loaded
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initApp);
} else {
    initApp();
}
