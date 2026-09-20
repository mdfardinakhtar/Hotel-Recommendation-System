import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import pandas as pd
import numpy as np
import joblib
import re
import urllib.parse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
app.secret_key = "indian-hotel-recommendation-secret-key"

# --------------------------------------------------
# Load Data & Build Feature Representations
# --------------------------------------------------
REVIEWS_FILE = "data/hotel_reviews_ml_scored.csv"
PROFILE_FILE = "data/hotel_recommendation_profiles.csv"

# Read original datasets (untouched raw data)
reviews = pd.read_csv(REVIEWS_FILE)
profiles = pd.read_csv(PROFILE_FILE)

# Build one aggregated review document per hotel for TF-IDF
hotel_text = reviews.groupby(
    ["Hotel_ID", "Hotel_Name", "Location"], as_index=False
).agg(
    Hotel_Review_Text=("review_text", lambda x: " ".join(x.astype(str)))
)

# Train TF-IDF representation on aggregated hotel review text
vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    min_df=2,
    max_features=60000
)
hotel_matrix = vectorizer.fit_transform(hotel_text["Hotel_Review_Text"])

# Keep unique profile row per hotel
profile_cols = [
    "Hotel_ID", "Avg_Price", "Smoothed_Rating",
    "Rating_Score", "Smoothed_Positive_Rate", "Review_Count"
] + [c for c in profiles.columns if c.endswith("_Positive_Rate")]

profile_cols = list(dict.fromkeys(profile_cols))
profiles_unique = profiles[profile_cols].drop_duplicates("Hotel_ID")

# Merge text and profiles
hotel_data = hotel_text.merge(profiles_unique, on="Hotel_ID", how="left")

# Extract original price and discount metadata from reviews dataset
price_meta = reviews.groupby("Hotel_ID").agg(
    Original_Price=("Original_Price_Num", "median"),
    Discount_Pct=("Discount_Pct", "median")
).reset_index()

hotel_data = hotel_data.merge(price_meta, on="Hotel_ID", how="left")

# --------------------------------------------------
# Hotel Address In-Memory Lookup (Hotel_ID -> Address)
# --------------------------------------------------
def clean_address_duplication(address_str, city_name):
    """
    Ensure the city name is not repeated unnecessarily inside the address string.
    e.g., 'Near ISKCON temple Bangalore, Bangalore, Karnataka' -> 'Near ISKCON temple Bangalore, Karnataka'
    Preserves all building numbers, streets, localities, landmarks, city, state, and PIN codes.
    """
    c = str(city_name).strip() if city_name else ""
    if not c or not address_str:
        return address_str
    if " (Transit)" in c:
        c = c.replace(" (Transit)", "").strip()
    c_esc = re.escape(c)
    pattern = re.compile(r'(\b' + c_esc + r'\b.*?),\s*' + c_esc + r'\b', re.IGNORECASE)
    cleaned = pattern.sub(r'\1', address_str)
    pattern_consec = re.compile(r'\b(' + c_esc + r')(?:\s*,\s*\1\b)+', re.IGNORECASE)
    cleaned = pattern_consec.sub(r'\1', cleaned)
    cleaned = re.sub(r',\s*,+', ',', cleaned)
    cleaned = re.sub(r',\s*', ', ', cleaned)
    cleaned = re.sub(r'^\s*,\s*', '', cleaned)
    cleaned = re.sub(r'\s*,\s*$', '', cleaned).strip()
    return cleaned or address_str


def format_address_for_display(address, city=None, location=None):
    """
    Format address for display ensuring no unnecessary duplicate city occurrences.
    Preserves all building numbers, streets, localities, landmarks, city, state, and PIN codes.
    """
    if not address or address == "Address not available":
        return address or "Address not available"
    city_name = city or (str(location).replace("_", " ") if location else "")
    return clean_address_duplication(address, city_name)


# --------------------------------------------------
# Indian City to State Mapping (all 251 locations)
# --------------------------------------------------
CITY_STATE_MAP = {
    "Abohar": "Punjab", "Agartala": "Tripura", "Agra": "Uttar Pradesh",
    "Ahmedabad": "Gujarat", "Ahmednagar": "Maharashtra", "Aizawl": "Mizoram",
    "Ajmer": "Rajasthan", "Akola": "Maharashtra", "Alappuzha": "Kerala",
    "Alibag": "Maharashtra", "Aligarh": "Uttar Pradesh", "Alipurduar": "West Bengal",
    "Almora": "Uttarakhand", "Alwar": "Rajasthan", "Ambala": "Haryana",
    "Amravati": "Maharashtra", "Amritsar": "Punjab", "Anand": "Gujarat",
    "Anantapur": "Andhra Pradesh", "Angul": "Odisha", "Ankleshwar": "Gujarat",
    "Arakku": "Andhra Pradesh", "Arrah": "Bihar", "Asansol": "West Bengal",
    "Aurangabad": "Maharashtra", "Ayodhya": "Uttar Pradesh", "Baddi": "Himachal Pradesh",
    "Bagalkot": "Karnataka", "Bahraich": "Uttar Pradesh", "Balaghat": "Madhya Pradesh",
    "Balangir": "Odisha", "Balasore": "Odisha", "Ballia": "Uttar Pradesh",
    "Balrampur": "Uttar Pradesh", "Balurghat": "West Bengal", "Banda": "Uttar Pradesh",
    "Bangalore": "Karnataka", "Banka": "Bihar", "Bankura": "West Bengal",
    "Barabanki": "Uttar Pradesh", "Baramati": "Maharashtra", "Baran": "Rajasthan",
    "Barbil": "Odisha", "Bardhaman": "West Bengal", "Bareilly": "Uttar Pradesh",
    "Bargarh": "Odisha", "Barmer": "Rajasthan", "Barnala": "Punjab",
    "Baripada": "Odisha", "Baroda": "Gujarat", "Bastar": "Chhattisgarh",
    "Basti": "Uttar Pradesh", "Batala": "Punjab", "Bathinda": "Punjab",
    "Beawar": "Rajasthan", "Begusarai": "Bihar", "Belgaum": "Karnataka",
    "Bellary": "Karnataka", "Betul": "Madhya Pradesh", "Bhadohi": "Uttar Pradesh",
    "Bhagalpur": "Bihar", "Bharatpur": "Rajasthan", "Bharuch": "Gujarat",
    "Bhavnagar": "Gujarat", "Bhilai": "Chhattisgarh", "Bhilwara": "Rajasthan",
    "Bhimavaram": "Andhra Pradesh", "Bhind": "Madhya Pradesh", "Bhiwadi": "Rajasthan",
    "Bhiwani": "Haryana", "Bhopal": "Madhya Pradesh", "Bhubaneswar": "Odisha",
    "Bhuj": "Gujarat", "Bhusawal": "Maharashtra", "Bidar": "Karnataka",
    "Bijapur": "Karnataka", "Bikaner": "Rajasthan", "Bilaspur": "Chhattisgarh",
    "Bina": "Madhya Pradesh", "Bodhgaya": "Bihar", "Bokaro": "Jharkhand",
    "Bolpur": "West Bengal", "Bongaigaon": "Assam", "Budaun": "Uttar Pradesh",
    "Bulandshahr": "Uttar Pradesh", "Bundi": "Rajasthan", "Burhanpur": "Madhya Pradesh",
    "Buxar": "Bihar", "Calicut": "Kerala", "Chamba": "Himachal Pradesh",
    "Chamoli": "Uttarakhand", "Champawat": "Uttarakhand", "Chandannagar": "West Bengal",
    "Chandigarh": "Chandigarh", "Chandrapur": "Maharashtra", "Chapra": "Bihar",
    "Chennai": "Tamil Nadu", "Chhatarpur": "Madhya Pradesh", "Chhindwara": "Madhya Pradesh",
    "Chikmagalur": "Karnataka", "Chiplun": "Maharashtra", "Chitrakoot": "Uttar Pradesh",
    "Chittorgarh": "Rajasthan", "Coimbatore": "Tamil Nadu", "Coochbehar": "West Bengal",
    "Coonoor": "Tamil Nadu", "Cuddalore": "Tamil Nadu", "Cuttack": "Odisha",
    "Dahod": "Gujarat", "Dalhousie": "Himachal Pradesh", "Daman": "Daman and Diu",
    "Damoh": "Madhya Pradesh", "Darbhanga": "Bihar", "Darjeeling": "West Bengal",
    "Datia": "Madhya Pradesh", "Dausa": "Rajasthan", "Davangere": "Karnataka",
    "Dehradun": "Uttarakhand", "Deoghar": "Jharkhand", "Deoria": "Uttar Pradesh",
    "Dewas": "Madhya Pradesh", "Dhanbad": "Jharkhand", "Dhar": "Madhya Pradesh",
    "Dharamshala": "Himachal Pradesh", "Dharmapuri": "Tamil Nadu", "Dharwad": "Karnataka",
    "Dholpur": "Rajasthan", "Dhule": "Maharashtra", "Dibrugarh": "Assam",
    "Digha": "West Bengal", "Dimapur": "Nagaland", "Dindigul": "Tamil Nadu",
    "Diu": "Daman and Diu", "Dumka": "Jharkhand", "Durg": "Chhattisgarh",
    "Durgapur": "West Bengal", "Dwarka": "Gujarat", "Eluru": "Andhra Pradesh",
    "Erode": "Tamil Nadu", "Etah": "Uttar Pradesh", "Etawah": "Uttar Pradesh",
    "Faizabad": "Uttar Pradesh", "Faridabad": "Haryana", "Farrukhabad": "Uttar Pradesh",
    "Fatehabad": "Haryana", "Fatehpur": "Uttar Pradesh", "Fazilka": "Punjab",
    "Firozabad": "Uttar Pradesh", "Firozpur": "Punjab", "Gadag": "Karnataka",
    "Gadchiroli": "Maharashtra", "Gandhidham": "Gujarat", "Gandhinagar": "Gujarat",
    "Gangtok": "Sikkim", "Gaya": "Bihar", "Ghaziabad": "Uttar Pradesh",
    "Ghazipur": "Uttar Pradesh", "Giridih": "Jharkhand", "Goa": "Goa",
    "Godhra": "Gujarat", "Gonda": "Uttar Pradesh", "Gondia": "Maharashtra",
    "Gorakhpur": "Uttar Pradesh", "Gulbarga": "Karnataka", "Gumla": "Jharkhand",
    "Guna": "Madhya Pradesh", "Guntur": "Andhra Pradesh", "Gurdaspur": "Punjab",
    "Gurgaon": "Haryana", "Guwahati": "Assam", "Gwalior": "Madhya Pradesh",
    "Hajipur": "Bihar", "Haldia": "West Bengal", "Haldwani": "Uttarakhand",
    "Hampi": "Karnataka", "Hansi": "Haryana", "Hanumangarh": "Rajasthan",
    "Hapur": "Uttar Pradesh", "Harda": "Madhya Pradesh", "Hardoi": "Uttar Pradesh",
    "Haridwar": "Uttarakhand", "Hassan": "Karnataka", "Hathras": "Uttar Pradesh",
    "Haveri": "Karnataka", "Hazaribagh": "Jharkhand", "Himmatnagar": "Gujarat",
    "Hisar": "Haryana", "Hoshangabad": "Madhya Pradesh", "Hoshiarpur": "Punjab",
    "Hospet": "Karnataka", "Hosur": "Tamil Nadu", "Hubli": "Karnataka",
    "Hyderabad": "Telangana", "Idukki": "Kerala", "Imphal": "Manipur",
    "Indore": "Madhya Pradesh", "Itanagar": "Arunachal Pradesh", "Jabalpur": "Madhya Pradesh",
    "Jagdalpur": "Chhattisgarh", "Jaipur": "Rajasthan", "Jaisalmer": "Rajasthan",
    "Jajpur": "Odisha", "Jalandhar": "Punjab", "Jalaun": "Uttar Pradesh",
    "Jalgaon": "Maharashtra", "Jalna": "Maharashtra", "Jalpaiguri": "West Bengal",
    "Jammu": "Jammu and Kashmir", "Jamnagar": "Gujarat", "Jamshedpur": "Jharkhand",
    "Jaunpur": "Uttar Pradesh", "Jhabua": "Madhya Pradesh", "Jhajjar": "Haryana",
    "Jhalawar": "Rajasthan", "Jhansi": "Uttar Pradesh", "Jhunjhunu": "Rajasthan",
    "Jind": "Haryana", "Jodhpur": "Rajasthan", "Jorhat": "Assam",
    "Junagadh": "Gujarat", "Kadapa": "Andhra Pradesh", "Kaithal": "Haryana",
    "Kakinada": "Andhra Pradesh", "Kalaburagi": "Karnataka", "Kanchipuram": "Tamil Nadu",
    "Kannauj": "Uttar Pradesh", "Kannur": "Kerala", "Kanpur": "Uttar Pradesh",
    "Kanyakumari": "Tamil Nadu", "Kapurthala": "Punjab", "Karaikudi": "Tamil Nadu",
    "Karnal": "Haryana", "Karur": "Tamil Nadu", "Kasganj": "Uttar Pradesh",
    "Kashipur": "Uttarakhand", "Katihar": "Bihar", "Katra": "Jammu and Kashmir",
    "Kavali": "Andhra Pradesh", "Khammam": "Telangana", "Khandwa": "Madhya Pradesh",
    "Khanna": "Punjab", "Kharagpur": "West Bengal", "Kochi": "Kerala",
    "Kodaikanal": "Tamil Nadu", "Kohima": "Nagaland", "Kolar": "Karnataka",
    "Kolhapur": "Maharashtra", "Kolkata": "West Bengal", "Kollam": "Kerala",
    "Kota": "Rajasthan", "Kotdwar": "Uttarakhand", "Kottayam": "Kerala",
    "Kozhikode": "Kerala", "Krishnanagar": "West Bengal", "Kullu": "Himachal Pradesh",
    "Kumbakonam": "Tamil Nadu", "Kurnool": "Andhra Pradesh", "Kurukshetra": "Haryana",
    "Lakhimpur": "Uttar Pradesh", "Lalitpur": "Uttar Pradesh", "Latur": "Maharashtra",
    "Lucknow": "Uttar Pradesh", "Ludhiana": "Punjab", "Madikeri": "Karnataka",
    "Madurai": "Tamil Nadu", "Mahabaleshwar": "Maharashtra", "Mahbubnagar": "Telangana",
    "Mainpuri": "Uttar Pradesh", "Malappuram": "Kerala", "Malda": "West Bengal",
    "Malegaon": "Maharashtra", "Manali": "Himachal Pradesh", "Mandapam": "Tamil Nadu",
    "Mandi": "Himachal Pradesh", "Mandsaur": "Madhya Pradesh", "Mandya": "Karnataka",
    "Mangalore": "Karnataka", "Manipal": "Karnataka", "Mathura": "Uttar Pradesh",
    "Meerut": "Uttar Pradesh", "Mehsana": "Gujarat", "Mirzapur": "Uttar Pradesh",
    "Moga": "Punjab", "Mohali": "Punjab", "Moradabad": "Uttar Pradesh",
    "Morbi": "Gujarat", "Morena": "Madhya Pradesh", "Motihari": "Bihar",
    "Mount Abu": "Rajasthan", "Muktsar": "Punjab", "Mumbai": "Maharashtra",
    "Munger": "Bihar", "Murshidabad": "West Bengal", "Mussoorie": "Uttarakhand",
    "Muzaffarnagar": "Uttar Pradesh", "Muzaffarpur": "Bihar", "Mysore": "Karnataka",
    "Nadiad": "Gujarat", "Nagaon": "Assam", "Nagapattinam": "Tamil Nadu",
    "Nagaur": "Rajasthan", "Nagercoil": "Tamil Nadu", "Nagpur": "Maharashtra",
    "Nainital": "Uttarakhand", "Nalanda": "Bihar", "Nanded": "Maharashtra",
    "Nandurbar": "Maharashtra", "Nandyal": "Andhra Pradesh", "Nashik": "Maharashtra",
    "Navsari": "Gujarat", "Neemuch": "Madhya Pradesh", "Nellore": "Andhra Pradesh",
    "Nizamabad": "Telangana", "Noida": "Uttar Pradesh", "Ongole": "Andhra Pradesh",
    "Ooty": "Tamil Nadu", "Osmanabad": "Maharashtra", "Palakkad": "Kerala",
    "Palanpur": "Gujarat", "Pali": "Rajasthan", "Palwal": "Haryana",
    "Panchkula": "Haryana", "Panipat": "Haryana", "Panjim": "Goa",
    "Parbhani": "Maharashtra", "Pathankot": "Punjab", "Patiala": "Punjab",
    "Patna": "Bihar", "Phagwara": "Punjab", "Pilibhit": "Uttar Pradesh",
    "Pondicherry": "Puducherry", "Porbandar": "Gujarat", "Pratapgarh": "Uttar Pradesh",
    "Prayagraj": "Uttar Pradesh", "Pudukkottai": "Tamil Nadu", "Pune": "Maharashtra",
    "Puri": "Odisha", "Purnea": "Bihar", "Purulia": "West Bengal",
    "Rae Bareli": "Uttar Pradesh", "Raichur": "Karnataka", "Raigad": "Maharashtra",
    "Raigarh": "Chhattisgarh", "Raipur": "Chhattisgarh", "Rajahmundry": "Andhra Pradesh",
    "Rajapalayam": "Tamil Nadu", "Rajkot": "Gujarat", "Rajnandgaon": "Chhattisgarh",
    "Rajsamand": "Rajasthan", "Ramanathapuram": "Tamil Nadu", "Ramgarh": "Jharkhand",
    "Rampur": "Uttar Pradesh", "Ranchi": "Jharkhand", "Raniganj": "West Bengal",
    "Ratlam": "Madhya Pradesh", "Ratnagiri": "Maharashtra", "Rewa": "Madhya Pradesh",
    "Rewari": "Haryana", "Rishikesh": "Uttarakhand", "Rohtak": "Haryana",
    "Roorkee": "Uttarakhand", "Rourkela": "Odisha", "Sagar": "Madhya Pradesh",
    "Saharanpur": "Uttar Pradesh", "Saharsa": "Bihar", "Salem": "Tamil Nadu",
    "Samastipur": "Bihar", "Sambalpur": "Odisha", "Sangli": "Maharashtra",
    "Satara": "Maharashtra", "Satna": "Madhya Pradesh", "Sawai Madhopur": "Rajasthan",
    "Secunderabad": "Telangana", "Sehore": "Madhya Pradesh", "Shahjahanpur": "Uttar Pradesh",
    "Shillong": "Meghalaya", "Shimla": "Himachal Pradesh", "Shivamogga": "Karnataka",
    "Shivpuri": "Madhya Pradesh", "Shirdi": "Maharashtra", "Sikar": "Rajasthan",
    "Silchar": "Assam", "Siliguri": "West Bengal", "Singrauli": "Madhya Pradesh",
    "Sirsa": "Haryana", "Sitamarhi": "Bihar", "Sitapur": "Uttar Pradesh",
    "Solan": "Himachal Pradesh", "Solapur": "Maharashtra", "Sonipat": "Haryana",
    "Srikakulam": "Andhra Pradesh", "Srinagar": "Jammu and Kashmir", "Surat": "Gujarat",
    "Surendranagar": "Gujarat", "Tanjore": "Tamil Nadu", "Tezpur": "Assam",
    "Thalassery": "Kerala", "Thanjavur": "Tamil Nadu", "Thekkady": "Kerala",
    "Thiruvalla": "Kerala", "Thiruvananthapuram": "Kerala", "Thoothukudi": "Tamil Nadu",
    "Thrissur": "Kerala", "Tinsukia": "Assam", "Tirunelveli": "Tamil Nadu",
    "Tirupati": "Andhra Pradesh", "Tirupur": "Tamil Nadu", "Tiruvannamalai": "Tamil Nadu",
    "Trichy": "Tamil Nadu", "Tumkur": "Karnataka", "Udaipur": "Rajasthan",
    "Udupi": "Karnataka", "Ujjain": "Madhya Pradesh", "Ulhasnagar": "Maharashtra",
    "Umaria": "Madhya Pradesh", "Una": "Himachal Pradesh", "Valsad": "Gujarat",
    "Vapi": "Gujarat", "Varanasi": "Uttar Pradesh", "Vellore": "Tamil Nadu",
    "Vidisha": "Madhya Pradesh", "Vijayawada": "Andhra Pradesh", "Villupuram": "Tamil Nadu",
    "Visakhapatnam": "Andhra Pradesh", "Vizianagaram": "Andhra Pradesh", "Vrindavan": "Uttar Pradesh",
    "Wardha": "Maharashtra", "Wayanad": "Kerala", "Yamunanagar": "Haryana",
    "Yavatmal": "Maharashtra", "Zirakpur": "Punjab", "Delhi": "Delhi",
    "Delhi_Transit": "Delhi",
    # Additional 70 locations
    "Balugaon": "Odisha", "Banjar": "Himachal Pradesh", "Barpeta": "Assam",
    "Bawal": "Haryana", "Behrampur": "Odisha", "Berhampore": "West Bengal",
    "Bhadra": "Rajasthan", "Bijainagar": "Rajasthan", "Buldhana": "Maharashtra",
    "Charkhi-Dadri": "Haryana", "Chittoor": "Andhra Pradesh", "Coorg": "Karnataka",
    "Courtallam": "Tamil Nadu", "Degana": "Rajasthan", "Ernakulam": "Kerala",
    "Hubli-Dharwad": "Karnataka", "Islampur": "West Bengal", "Kaimukhiya": "Uttar Pradesh",
    "Kalimpong": "West Bengal", "Karimnagar": "Telangana", "Karjat": "Maharashtra",
    "Karwar": "Karnataka", "Kasauli": "Himachal Pradesh", "Kaziranga": "Assam",
    "Keonjhar": "Odisha", "Khajuraho": "Madhya Pradesh", "Kharar": "Punjab",
    "Koderma": "Jharkhand", "Kovalam": "Kerala", "Lansdowne": "Uttarakhand",
    "Latagudi": "West Bengal", "Lonavala": "Maharashtra", "Mahud": "Maharashtra",
    "Mandarmoni": "West Bengal", "Manesar": "Haryana", "Mcleod-Ganj": "Himachal Pradesh",
    "Munnar": "Kerala", "Namakkal": "Tamil Nadu", "Narnaul": "Haryana",
    "Navi_Mumbai": "Maharashtra", "Nawada": "Bihar", "Orchha": "Madhya Pradesh",
    "Pahalgam": "Jammu and Kashmir", "Palampur": "Himachal Pradesh", "Palani": "Tamil Nadu",
    "Pallu": "Rajasthan", "Pathanamthitta": "Kerala", "Patnitop": "Jammu and Kashmir",
    "Port-Blair": "Andaman and Nicobar Islands", "Pushkar": "Rajasthan", "Raebareily": "Uttar Pradesh",
    "Rajgir": "Bihar", "Rajpura": "Punjab", "Ranjangaon": "Maharashtra",
    "Ranthambore": "Rajasthan", "Rudrapur": "Uttarakhand", "Sibsagar": "Assam",
    "Sillery-Gaon": "West Bengal", "Sirhind": "Punjab", "Sonbhadra": "Uttar Pradesh",
    "Songadh": "Gujarat", "Srinagar-Uttarakhand": "Uttarakhand", "Tajpur": "West Bengal",
    "Tenali": "Andhra Pradesh", "Tijara": "Rajasthan", "Tiruppur": "Tamil Nadu",
    "Trivandrum": "Kerala", "Udupi-Manipal": "Karnataka", "Vadodara": "Gujarat",
    "Varkala": "Kerala"
}


def extract_address_and_pure_name(raw_name, loc):
    """
    Extract pure hotel name and reconstruct comprehensive address using dataset fields.
    1. Extracts prepositional landmarks (Near, Opposite, Opp, Behind, Beside, Adjacent to, etc.)
    2. Extracts comma-separated area/locality suffixes
    3. Handles special transit hubs (e.g. Delhi_Transit -> Near IGI Airport, Mahipalpur)
    4. Associates location with Indian State
    5. Applies format_address_for_display to adhere strictly to the City Duplication Rule.
    """
    raw_name_clean = str(raw_name).strip()
    loc_clean = str(loc).strip() if loc else ""
    city_display = "Delhi (Transit)" if loc_clean == "Delhi_Transit" else loc_clean.replace("_", " ")
    state = CITY_STATE_MAP.get(loc_clean, "")

    # 1. Prepositional landmarks
    prep_pattern = r'^(.*?)\s*(?:,\s*)?\b(Near|Opposite|Opp\.?|Behind|Beside|Adjacent to|Adjacent|Close to|Next to|Facing|Towards|At|Off)\s+(.+)$'
    m = re.search(prep_pattern, raw_name_clean, re.IGNORECASE)
    if m:
        pure_name = m.group(1).rstrip(', ').strip()
        landmark = (m.group(2) + ' ' + m.group(3)).rstrip('.').strip()
        raw_address = f"{landmark}, {city_display}, {state}" if state else f"{landmark}, {city_display}"
        display_address = format_address_for_display(raw_address, city_display, loc_clean)
        return pure_name, raw_address, display_address

    # 2. Delhi_Transit airport transit hub
    if loc_clean == "Delhi_Transit":
        pure_name = raw_name_clean.rstrip(',').strip()
        raw_address = "Near IGI Airport, Mahipalpur, Delhi"
        display_address = format_address_for_display(raw_address, city_display, loc_clean)
        return pure_name, raw_address, display_address

    # 3. Comma-separated locality suffix (e.g. 'OYO Townhouse 407 Legacy, Civil Line.')
    comma_pattern = r'^(.*?)\s*,\s*([^,]+)$'
    m_comma = re.search(comma_pattern, raw_name_clean)
    if m_comma and len(m_comma.group(2).strip()) >= 3:
        locality = m_comma.group(2).rstrip('.').strip()
        pure_name = m_comma.group(1).rstrip(', ').strip()
        raw_address = f"{locality}, {city_display}, {state}" if state else f"{locality}, {city_display}"
        display_address = format_address_for_display(raw_address, city_display, loc_clean)
        return pure_name, raw_address, display_address

    # 4. Standard hotel with verified location and state in India
    pure_name = raw_name_clean.rstrip(',').strip()
    if loc_clean and state:
        raw_address = f"{city_display}, {state}"
        display_address = format_address_for_display(raw_address, city_display, loc_clean)
        return pure_name, raw_address, display_address
    elif loc_clean:
        raw_address = f"{city_display}"
        display_address = format_address_for_display(raw_address, city_display, loc_clean)
        return pure_name, raw_address, display_address
    else:
        return pure_name, "Address not available", "Address not available"


def build_hotel_display_and_address_lookup(df):
    """
    Build in-memory lookup from Hotel_ID -> {
        'name': pure hotel name only (without landmark/address appended),
        'raw_address': complete address including landmark, city, and state,
        'address': display address without unnecessary duplicate city repetitions,
        'city': human-readable city name
    }
    Uses Hotel_ID as the primary key for matching hotel information.
    Loads from data/hotel_metadata_with_address.csv when available.
    """
    metadata_file = "data/hotel_metadata_with_address.csv"
    if os.path.exists(metadata_file):
        meta_df = pd.read_csv(metadata_file)
        lookup = {}
        for _, row in meta_df.iterrows():
            hid = int(row["Hotel_ID"])
            addr = str(row["Address"]).strip() if pd.notna(row["Address"]) else ""
            city = str(row["City"]).strip() if pd.notna(row["City"]) else ""
            clean_addr = clean_address_duplication(addr, city)
            lookup[hid] = {
                "name": str(row["Hotel_Name"]).strip(),
                "raw_name": str(row["Raw_Hotel_Name"]).strip(),
                "raw_address": addr,
                "address": clean_addr if clean_addr else "Address not available",
                "city": city,
                "state": str(row["State"]).strip() if pd.notna(row["State"]) else "",
                "landmark": str(row["Landmark"]).strip() if pd.notna(row["Landmark"]) else ""
            }
        return lookup

    lookup = {}
    for _, row in df.iterrows():
        hid = int(row["Hotel_ID"])
        raw_name = str(row["Hotel_Name"]).strip()
        loc = str(row["Location"]).strip()
        city_display = "Delhi (Transit)" if loc == "Delhi_Transit" else loc.replace("_", " ")

        pure_name, raw_address, display_address = extract_address_and_pure_name(raw_name, loc)

        lookup[hid] = {
            "name": pure_name,
            "raw_name": raw_name,
            "raw_address": raw_address,
            "address": display_address,
            "city": city_display
        }
    return lookup


HOTEL_DISPLAY_LOOKUP = build_hotel_display_and_address_lookup(hotel_data)
HOTEL_ADDRESS_LOOKUP = {hid: info["address"] for hid, info in HOTEL_DISPLAY_LOOKUP.items()}

# --------------------------------------------------
# Aspect Keywords & Exact Column Mappings
# --------------------------------------------------
ASPECT_KEYWORDS = {
    "Cleanliness": ["clean", "cleanliness", "hygiene", "tidy", "neat"],
    "Room": ["room", "bed", "bathroom", "shower", "bedroom"],
    "Staff": ["staff", "friendly", "helpful", "polite", "reception"],
    "Service": ["service", "housekeeping", "check in", "check-out", "support"],
    "Food": ["food", "breakfast", "restaurant", "meal", "dinner", "lunch"],
    "Location": ["location", "metro", "station", "airport", "market", "near"],
    "Price": ["price", "cheap", "affordable", "budget", "value", "cost", "expensive"],
    "Facilities": ["wifi", "internet", "parking", "pool", "gym", "facilities", "amenities"],
    "Comfort": ["comfortable", "comfort", "quiet", "spacious", "noise"]
}

# Note: Location aspect in profiles is 'Hotel_Location_Aspect_Positive_Rate'
ASPECT_COLUMN_MAP = {
    "Cleanliness": "Cleanliness_Positive_Rate",
    "Room": "Room_Positive_Rate",
    "Staff": "Staff_Positive_Rate",
    "Service": "Service_Positive_Rate",
    "Food": "Food_Positive_Rate",
    "Location": "Hotel_Location_Aspect_Positive_Rate",
    "Price": "Price_Positive_Rate",
    "Facilities": "Facilities_Positive_Rate",
    "Comfort": "Comfort_Positive_Rate"
}

# --------------------------------------------------
# Popular External Booking Platforms Configuration
# --------------------------------------------------
BOOKING_PLATFORMS = [
    {
        "id": "makemytrip",
        "name": "MakeMyTrip",
        "badge": "Popular in India",
        "logo_text": "MMT",
        "bg_color": "#e41d36",
        "search_url_template": "https://www.makemytrip.com/hotels/hotel-listing/?searchText={query}",
        "description": "Explore room choices, verified guest ratings, and seasonal discounts on MakeMyTrip."
    },
    {
        "id": "goibibo",
        "name": "Goibibo",
        "badge": "Best Deals",
        "logo_text": "go",
        "bg_color": "#f26722",
        "search_url_template": "https://www.goibibo.com/hotels/find-hotels-in-any/?searchText={query}",
        "description": "Search verified hotel deals, instant booking offers, and user reviews on Goibibo."
    },
    {
        "id": "booking_com",
        "name": "Booking.com",
        "badge": "Global Stays",
        "logo_text": "B.",
        "bg_color": "#003580",
        "search_url_template": "https://www.booking.com/searchresults.html?ss={query}",
        "description": "Compare room types, price tiers, and flexible cancellation options on Booking.com."
    },
    {
        "id": "agoda",
        "name": "Agoda",
        "badge": "Great Value",
        "logo_text": "agoda",
        "bg_color": "#5392f9",
        "search_url_template": "https://www.agoda.com/search?text={query}",
        "description": "Find competitive accommodation tariffs and traveler review ratings on Agoda."
    },
    {
        "id": "oyo",
        "name": "OYO",
        "badge": "Budget & Value",
        "logo_text": "OYO",
        "bg_color": "#ee2e24",
        "search_url_template": "https://www.oyorooms.com/search?location={query}",
        "description": "Find verified budget stays, sanitized rooms, and direct booking benefits on OYO."
    }
]


def get_booking_platform_links(hotel_name, city, address=None, location=None):
    """
    Generate hotel-specific search URLs for major external booking platforms.
    Combines clean hotel name, destination city, and landmark if available.
    Ensures safe URL encoding for seamless external redirection.
    """
    clean_name = re.sub(r"[^\w\s]", " ", str(hotel_name)).strip()
    clean_city = re.sub(r"[^\w\s]", " ", str(city)).strip()

    # Extract landmark/locality if not already redundant with name or city
    extra_terms = []
    if address and address != "Address not available":
        parts = [p.strip() for p in address.split(",") if p.strip()]
        if parts:
            first_part = re.sub(r"[^\w\s]", " ", parts[0]).strip()
            if (first_part and
                first_part.lower() not in clean_name.lower() and
                first_part.lower() not in clean_city.lower()):
                extra_terms.append(first_part)

    query_parts = [clean_name, clean_city] + extra_terms[:1]
    query_str = " ".join([p for p in query_parts if p]).strip()
    encoded_query = urllib.parse.quote_plus(query_str)

    platform_links = []
    for platform in BOOKING_PLATFORMS:
        platform_links.append({
            "id": platform["id"],
            "name": platform["name"],
            "badge": platform["badge"],
            "logo_text": platform["logo_text"],
            "bg_color": platform["bg_color"],
            "description": platform["description"],
            "search_query": query_str,
            "url": platform["search_url_template"].format(query=encoded_query),
            "button_text": f"Search on {platform['name']}"
        })

    return platform_links


def detect_aspects(preference):
    """Detect which aspect keywords are present in user query."""
    text = preference.lower()
    return [
        aspect for aspect, terms in ASPECT_KEYWORDS.items()
        if any(term in text for term in terms)
    ]


def filter_by_location(df, location_input):
    """
    Intelligently match location input with dataset location names.
    Supports Delhi -> Delhi_Transit normalization and space/underscore tolerance.
    """
    if not location_input:
        return df

    loc_str = str(location_input).strip()
    if not loc_str:
        return df

    norm_input = loc_str.lower().replace("_", " ").strip()
    # Normalize Delhi user input to match dataset's 'Delhi_Transit'
    if norm_input in ["delhi", "delhi (transit)", "delhi transit", "new delhi"]:
        target_token = "delhi_transit"
    else:
        target_token = loc_str.lower()

    # 1. Exact match
    exact_mask = df["Location"].astype(str).str.lower() == target_token
    if exact_mask.any():
        return df[exact_mask]

    # 2. Normalized space/underscore match
    norm_series = df["Location"].astype(str).str.lower().str.replace("_", " ")
    norm_target = target_token.replace("_", " ")
    norm_mask = norm_series == norm_target
    if norm_mask.any():
        return df[norm_mask]

    # 3. Starts-with match (e.g. 'delhi' matching 'Delhi_Transit')
    prefix_mask = norm_series.str.startswith(norm_target)
    if prefix_mask.any():
        return df[prefix_mask]

    # 4. Substring contains match
    contains_mask = norm_series.str.contains(norm_target, regex=False)
    if contains_mask.any():
        return df[contains_mask]

    return df[exact_mask]


def generate_why_recommended(row, preference, aspects, budget, location):
    """
    Generate verifiable, data-backed reasons for recommendation.
    Never invents unverified claims.
    """
    reasons = []

    # Aspect satisfaction
    if aspects:
        for asp in aspects:
            col = ASPECT_COLUMN_MAP.get(asp, f"{asp}_Positive_Rate")
            val = row.get(col)
            if val is not None and not pd.isna(val) and float(val) >= 70:
                reasons.append(f"Strong {asp.lower()} satisfaction ({round(float(val), 1)}% positive)")

    # Positive sentiment
    sentiment_val = row.get("Smoothed_Positive_Rate")
    if sentiment_val is not None and not pd.isna(sentiment_val) and float(sentiment_val) >= 75:
        reviews_cnt = int(row.get("Review_Count", 0))
        reasons.append(f"High customer sentiment ({round(float(sentiment_val), 1)}% positive across {reviews_cnt} reviews)")

    # Star rating
    rating_val = row.get("Smoothed_Rating")
    if rating_val is not None and not pd.isna(rating_val) and float(rating_val) >= 4.0:
        reasons.append(f"Top customer rating ({round(float(rating_val), 2)} / 5 stars)")
    elif rating_val is not None and not pd.isna(rating_val) and float(rating_val) >= 3.5:
        reasons.append(f"Good customer rating ({round(float(rating_val), 2)} / 5 stars)")

    # Budget match
    price_val = row.get("Avg_Price")
    if budget is not None and price_val is not None and not pd.isna(price_val) and float(price_val) <= float(budget):
        reasons.append(f"Fits budget at ₹{int(float(price_val))}/night (limit: ₹{int(float(budget))})")

    # Semantic preference match
    sim_val = row.get("Preference_Similarity")
    if sim_val is not None and not pd.isna(sim_val) and float(sim_val) >= 20:
        reasons.append(f"Matches query preferences ({round(float(sim_val), 1)}% semantic similarity)")

    # Location confirmation
    if location and str(row.get("Location", "")).lower() == str(location).lower():
        reasons.append(f"Located in {row.get('Location')}")

    # Fallback reason if list is empty
    if not reasons:
        reasons.append(f"High overall recommendation score ({round(float(row.get('Recommendation_Score', 0)), 1)}%)")

    return reasons[:4]


def get_recommendations(preference, location=None, max_price=None,
                        min_rating=None, top_n=10):
    """
    Main recommendation engine:
    1. Compute TF-IDF cosine similarity with user preference.
    2. Compute aspect match across detected keywords.
    3. Apply core scoring formula:
       35% Preference Similarity + 25% Aspect Match + 20% Sentiment + 20% Rating.
    4. Apply location and filter constraints.
    5. Graceful fallback: If exact constraints yield 0 results, relax one constraint at a time.
    """
    result = hotel_data.copy()

    # 1. Preference similarity
    query_vector = vectorizer.transform([preference])
    result["Preference_Similarity"] = (
        cosine_similarity(query_vector, hotel_matrix).ravel() * 100
    )

    # 2. Aspect match
    aspects = detect_aspects(preference)
    aspect_columns = [
        ASPECT_COLUMN_MAP.get(aspect, f"{aspect}_Positive_Rate")
        for aspect in aspects
        if ASPECT_COLUMN_MAP.get(aspect, f"{aspect}_Positive_Rate") in result.columns
    ]

    if aspect_columns:
        result["Aspect_Match"] = result[aspect_columns].mean(axis=1).fillna(0)
    else:
        result["Aspect_Match"] = result["Smoothed_Positive_Rate"].fillna(0)

    # 3. Core recommendation score (unchanged)
    result["Recommendation_Score"] = (
        0.35 * result["Preference_Similarity"].fillna(0) +
        0.25 * result["Aspect_Match"].fillna(0) +
        0.20 * result["Smoothed_Positive_Rate"].fillna(0) +
        0.20 * result["Rating_Score"].fillna(0)
    ).round(2)

    # 4. Location filtering
    if location:
        result = filter_by_location(result, location)

    # 5. Exact constraint application
    filtered = result.copy()
    if max_price is not None:
        filtered = filtered[
            filtered["Avg_Price"].isna() | (filtered["Avg_Price"] <= max_price)
        ]

    if min_rating is not None:
        filtered = filtered[
            filtered["Smoothed_Rating"].fillna(0) >= min_rating
        ]

    # 6. Evaluation & Graceful Fallback
    if len(filtered) > 0:
        final_df = filtered
        relaxed_info = {
            "is_relaxed": False,
            "relaxed_filter": None,
            "message": None
        }
    else:
        final_df = filtered
        relaxed_info = {
            "is_relaxed": False,
            "relaxed_filter": None,
            "message": "No hotels matched all your filters. Try increasing your budget, lowering the minimum rating, or removing one filter."
        }

        # Step A: Try relaxing minimum rating first (e.g. reduce by 0.5 or down to 3.5)
        if min_rating is not None and len(result) > 0:
            relaxed_rating_val = max(3.0, round(min_rating - 0.5, 1))
            rating_attempt = result.copy()
            if max_price is not None:
                rating_attempt = rating_attempt[
                    rating_attempt["Avg_Price"].isna() | (rating_attempt["Avg_Price"] <= max_price)
                ]
            rating_attempt = rating_attempt[
                rating_attempt["Smoothed_Rating"].fillna(0) >= relaxed_rating_val
            ]
            if len(rating_attempt) > 0:
                final_df = rating_attempt
                loc_name = str(location) if location else "this area"
                relaxed_info = {
                    "is_relaxed": True,
                    "relaxed_filter": "rating",
                    "original_value": min_rating,
                    "relaxed_value": relaxed_rating_val,
                    "message": f"No hotels matched all your filters (min rating: {min_rating}★). Showing recommendations with relaxed rating filter ({relaxed_rating_val}★) in {loc_name}."
                }

        # Step B: If still 0, try relaxing budget constraint (increase by 50% or drop budget)
        if len(final_df) == 0 and max_price is not None and len(result) > 0:
            relaxed_budget_val = round(max_price * 1.5)
            budget_attempt = result.copy()
            if min_rating is not None:
                budget_attempt = budget_attempt[
                    budget_attempt["Smoothed_Rating"].fillna(0) >= min_rating
                ]
            budget_attempt = budget_attempt[
                budget_attempt["Avg_Price"].isna() | (budget_attempt["Avg_Price"] <= relaxed_budget_val)
            ]
            if len(budget_attempt) == 0:
                # Try without budget restriction
                budget_attempt = result.copy()
                if min_rating is not None:
                    budget_attempt = budget_attempt[
                        budget_attempt["Smoothed_Rating"].fillna(0) >= min_rating
                    ]
            if len(budget_attempt) > 0:
                final_df = budget_attempt
                loc_name = str(location) if location else "this area"
                relaxed_info = {
                    "is_relaxed": True,
                    "relaxed_filter": "budget",
                    "original_value": max_price,
                    "relaxed_value": relaxed_budget_val,
                    "message": f"No hotels matched within your budget of ₹{int(max_price)}. Showing available recommendations with relaxed budget in {loc_name}."
                }

        # Step C: If still 0, relax both budget and rating within location
        if len(final_df) == 0 and len(result) > 0:
            final_df = result
            loc_name = str(location) if location else "this area"
            relaxed_info = {
                "is_relaxed": True,
                "relaxed_filter": "budget and rating",
                "message": f"No hotels matched both your budget and rating filters. Showing top available hotels in {loc_name}."
            }

    # Sort final recommendations by recommendation score and review count
    final_df = final_df.sort_values(
        ["Recommendation_Score", "Review_Count"],
        ascending=False
    ).head(top_n)

    return final_df, aspects, relaxed_info


# --------------------------------------------------
# Flask Routes
# --------------------------------------------------
@app.route("/")
def home():
    raw_locations = sorted(
        reviews["Location"].dropna().astype(str).unique().tolist()
    )
    # User-friendly display names (e.g. 'Delhi_Transit' -> 'Delhi' and 'Delhi (Transit)')
    locations = []
    for loc in raw_locations:
        if loc == "Delhi_Transit":
            locations.append({"value": "Delhi_Transit", "label": "Delhi"})
            locations.append({"value": "Delhi_Transit", "label": "Delhi (Transit)"})
        elif "_" in loc:
            label = loc.replace("_", " ")
            locations.append({"value": loc, "label": label})
        else:
            label = loc
            locations.append({"value": loc, "label": label})

    return render_template("index.html", locations=locations)


@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json(silent=True) or request.form

    preference = str(data.get("preference", "")).strip()
    location = str(data.get("location", "")).strip()
    budget = str(data.get("budget", "")).strip()
    min_rating = str(data.get("min_rating", "")).strip()

    if not preference:
        preference = "clean comfortable hotel with good service"

    max_price = None
    if budget:
        try:
            max_price = float(budget)
        except ValueError:
            pass

    minimum_rating = None
    if min_rating:
        try:
            minimum_rating = float(min_rating)
        except ValueError:
            pass

    result, aspects, relaxed_info = get_recommendations(
        preference=preference,
        location=location or None,
        max_price=max_price,
        min_rating=minimum_rating,
        top_n=10
    )

    hotels = []
    for _, row in result.iterrows():
        hid = int(row["Hotel_ID"])
        display_info = HOTEL_DISPLAY_LOOKUP.get(hid, {
            "name": str(row["Hotel_Name"]),
            "address": "Address not available",
            "city": str(row["Location"]).replace("_", " ")
        })
        platform_links = get_booking_platform_links(
            hotel_name=display_info["name"],
            city=display_info["city"],
            address=display_info["address"],
            location=row["Location"]
        )
        hotels.append({
            "hotel_id": hid,
            "name": display_info["name"],
            "raw_name": str(row["Hotel_Name"]),
            "location": str(row["Location"]),
            "city": display_info["city"],
            "address": display_info["address"],
            "raw_address": display_info.get("raw_address", display_info["address"]),
            "price": None if pd.isna(row["Avg_Price"]) else round(float(row["Avg_Price"])),
            "original_price": None if pd.isna(row.get("Original_Price")) else round(float(row["Original_Price"])),
            "discount": None if pd.isna(row.get("Discount_Pct")) else round(float(row["Discount_Pct"])),
            "rating": None if pd.isna(row["Smoothed_Rating"]) else round(float(row["Smoothed_Rating"]), 2),
            "sentiment": None if pd.isna(row["Smoothed_Positive_Rate"]) else round(float(row["Smoothed_Positive_Rate"]), 1),
            "aspect_match": round(float(row["Aspect_Match"]), 1),
            "similarity": round(float(row["Preference_Similarity"]), 1),
            "score": round(float(row["Recommendation_Score"]), 2),
            "reviews": int(row["Review_Count"]) if not pd.isna(row["Review_Count"]) else 0,
            "why_recommended": generate_why_recommended(row, preference, aspects, max_price, location),
            "booking_platforms": platform_links
        })

    return jsonify({
        "success": True,
        "detected_aspects": aspects,
        "count": len(hotels),
        "is_relaxed": relaxed_info.get("is_relaxed", False),
        "relaxed_filter": relaxed_info.get("relaxed_filter"),
        "message": relaxed_info.get("message"),
        "hotels": hotels
    })


@app.route("/hotel/<int:hotel_id>")
def hotel_details(hotel_id):
    hotel_row = hotel_data[hotel_data["Hotel_ID"] == hotel_id]
    if len(hotel_row) == 0:
        return render_template("404.html", message=f"Hotel with ID #{hotel_id} not found in dataset."), 404

    row = hotel_row.iloc[0]

    # Pre-calculated aspect scores for all 9 aspects
    all_aspects = [
        "Cleanliness", "Room", "Staff", "Service", "Food",
        "Location", "Price", "Facilities", "Comfort"
    ]
    aspect_scores = []
    for aspect in all_aspects:
        col = ASPECT_COLUMN_MAP.get(aspect, f"{aspect}_Positive_Rate")
        val = row.get(col)
        if val is not None and not pd.isna(val):
            aspect_scores.append({
                "name": aspect,
                "score": round(float(val), 1),
                "has_data": True
            })
        else:
            aspect_scores.append({
                "name": aspect,
                "score": None,
                "has_data": False
            })

    # Hotel reviews from dataset
    hotel_reviews_df = reviews[reviews["Hotel_ID"] == hotel_id]
    total_reviews_count = len(hotel_reviews_df)

    # ML Sentiment breakdown (POSITIVE vs NEGATIVE)
    ml_pos = int((hotel_reviews_df["ML_Sentiment"].astype(str).str.upper() == "POSITIVE").sum())
    ml_neg = int((hotel_reviews_df["ML_Sentiment"].astype(str).str.upper() == "NEGATIVE").sum())
    ml_total = ml_pos + ml_neg
    ml_pos_pct = round((ml_pos / ml_total) * 100, 1) if ml_total > 0 else 0.0
    ml_neg_pct = round(100.0 - ml_pos_pct, 1) if ml_total > 0 else 0.0

    # User labeled review sentiment breakdown (Positive, Neutral, Negative)
    user_pos = int((hotel_reviews_df["Sentiment"].astype(str).str.capitalize() == "Positive").sum())
    user_neu = int((hotel_reviews_df["Sentiment"].astype(str).str.capitalize() == "Neutral").sum())
    user_neg = int((hotel_reviews_df["Sentiment"].astype(str).str.capitalize() == "Negative").sum())
    user_total = total_reviews_count
    user_pos_pct = round((user_pos / user_total) * 100, 1) if user_total > 0 else 0.0
    user_neu_pct = round((user_neu / user_total) * 100, 1) if user_total > 0 else 0.0
    user_neg_pct = round((user_neg / user_total) * 100, 1) if user_total > 0 else 0.0

    # Review pagination & filtering
    page = request.args.get("page", 1, type=int)
    sentiment_filter = request.args.get("sentiment", "all").strip().lower()
    per_page = 10

    filtered_reviews = hotel_reviews_df
    if sentiment_filter == "positive":
        filtered_reviews = filtered_reviews[filtered_reviews["ML_Sentiment"].astype(str).str.upper() == "POSITIVE"]
    elif sentiment_filter == "negative":
        filtered_reviews = filtered_reviews[filtered_reviews["ML_Sentiment"].astype(str).str.upper() == "NEGATIVE"]

    filtered_count = len(filtered_reviews)
    total_pages = max(1, (filtered_count + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * per_page
    sliced_reviews = filtered_reviews.iloc[start_idx:start_idx + per_page]

    reviews_list = []
    for _, rev in sliced_reviews.iterrows():
        reviews_list.append({
            "user_name": str(rev.get("user_name", "Anonymous Guest")),
            "date": str(rev.get("date", "Verified Stay")),
            "rating": None if pd.isna(rev.get("Review_Rating")) else round(float(rev["Review_Rating"]), 1),
            "sentiment": str(rev.get("Sentiment", "Neutral")),
            "ml_sentiment": str(rev.get("ML_Sentiment", "POSITIVE")).upper(),
            "confidence": None if pd.isna(rev.get("ML_Sentiment_Confidence")) else round(float(rev["ML_Sentiment_Confidence"]) * 100, 1),
            "review_text": str(rev.get("review_text", "")).strip()
        })

    # Recommendation context from search query params (if user clicked from results)
    rec_context = {
        "score": request.args.get("score", type=float),
        "similarity": request.args.get("similarity", type=float),
        "aspect_match": request.args.get("aspect_match", type=float),
        "pref": request.args.get("pref", type=str, default="").strip()
    }

    hid = int(row["Hotel_ID"])
    display_info = HOTEL_DISPLAY_LOOKUP.get(hid, {
        "name": str(row["Hotel_Name"]),
        "address": "Address not available",
        "city": str(row["Location"]).replace("_", " ")
    })
    hotel_info = {
        "hotel_id": hid,
        "name": display_info["name"],
        "raw_name": str(row["Hotel_Name"]),
        "location": str(row["Location"]),
        "city": display_info["city"],
        "address": display_info["address"],
        "raw_address": display_info.get("raw_address", display_info["address"]),
        "price": None if pd.isna(row["Avg_Price"]) else round(float(row["Avg_Price"])),
        "original_price": None if pd.isna(row.get("Original_Price")) else round(float(row["Original_Price"])),
        "discount": None if pd.isna(row.get("Discount_Pct")) else round(float(row["Discount_Pct"])),
        "rating": None if pd.isna(row["Smoothed_Rating"]) else round(float(row["Smoothed_Rating"]), 2),
        "rating_score": None if pd.isna(row["Rating_Score"]) else round(float(row["Rating_Score"]), 1),
        "sentiment_rate": None if pd.isna(row["Smoothed_Positive_Rate"]) else round(float(row["Smoothed_Positive_Rate"]), 1),
        "review_count": total_reviews_count
    }

    # Generate verified why-recommended explanation
    why_reasons = generate_why_recommended(
        row,
        rec_context["pref"],
        detect_aspects(rec_context["pref"]) if rec_context["pref"] else [],
        None,
        row["Location"]
    )

    sentiment_stats = {
        "ml_pos": ml_pos,
        "ml_neg": ml_neg,
        "ml_total": ml_total,
        "ml_pos_pct": ml_pos_pct,
        "ml_neg_pct": ml_neg_pct,
        "user_pos": user_pos,
        "user_neu": user_neu,
        "user_neg": user_neg,
        "user_total": user_total,
        "user_pos_pct": user_pos_pct,
        "user_neu_pct": user_neu_pct,
        "user_neg_pct": user_neg_pct
    }

    # External booking platform links
    booking_platforms = get_booking_platform_links(
        hotel_name=display_info["name"],
        city=display_info["city"],
        address=display_info["address"],
        location=row["Location"]
    )

    return render_template(
        "hotel_details.html",
        hotel=hotel_info,
        aspect_scores=aspect_scores,
        sentiment_stats=sentiment_stats,
        reviews=reviews_list,
        page=page,
        total_pages=total_pages,
        total_reviews_filtered=filtered_count,
        sentiment_filter=sentiment_filter,
        rec_context=rec_context,
        why_reasons=why_reasons,
        booking_platforms=booking_platforms
    )


@app.route("/api/hotel/<int:hotel_id>/reviews")
def api_hotel_reviews(hotel_id):
    hotel_revs = reviews[reviews["Hotel_ID"] == hotel_id]
    if len(hotel_revs) == 0:
        return jsonify({"success": False, "message": "Hotel reviews not found", "reviews": []}), 404

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    sentiment_filter = request.args.get("sentiment", "all").strip().lower()

    filtered_revs = hotel_revs
    if sentiment_filter == "positive":
        filtered_revs = filtered_revs[filtered_revs["ML_Sentiment"].astype(str).str.upper() == "POSITIVE"]
    elif sentiment_filter == "negative":
        filtered_revs = filtered_revs[filtered_revs["ML_Sentiment"].astype(str).str.upper() == "NEGATIVE"]

    total = len(filtered_revs)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * per_page
    sliced = filtered_revs.iloc[start_idx:start_idx + per_page]

    items = []
    for _, r in sliced.iterrows():
        items.append({
            "user_name": str(r.get("user_name", "Anonymous Guest")),
            "date": str(r.get("date", "Verified Stay")),
            "rating": None if pd.isna(r.get("Review_Rating")) else float(r["Review_Rating"]),
            "sentiment": str(r.get("Sentiment", "Neutral")),
            "ml_sentiment": str(r.get("ML_Sentiment", "POSITIVE")).upper(),
            "confidence": None if pd.isna(r.get("ML_Sentiment_Confidence")) else round(float(r["ML_Sentiment_Confidence"]) * 100, 1),
            "review_text": str(r.get("review_text", "")).strip()
        })

    return jsonify({
        "success": True,
        "hotel_id": hotel_id,
        "page": page,
        "per_page": per_page,
        "total_reviews": total,
        "total_pages": total_pages,
        "sentiment_filter": sentiment_filter,
        "reviews": items
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "running",
        "reviews": int(len(reviews)),
        "hotels": int(hotel_data["Hotel_ID"].nunique()),
        "locations": int(hotel_data["Location"].nunique())
    })


@app.route("/favicon.ico")
def favicon():
    return app.send_static_file("favicon.ico")


if __name__ == "__main__":
    app.run(debug=True)

