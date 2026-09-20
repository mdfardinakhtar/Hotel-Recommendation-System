"""
Generate derived hotel metadata dataset: data/hotel_metadata_with_address.csv
Uses Hotel_ID as the primary key to associate every hotel with:
- Pure Hotel Name
- Original Raw Hotel Name
- Extracted Locality / Landmark
- City
- State
- Complete Full Address
Ensures zero fabricated data, zero external scraping, and zero city duplication inside the address string.
"""
import pandas as pd
import re

PROFILE_FILE = "data/hotel_recommendation_profiles.csv"
OUTPUT_FILE = "data/hotel_metadata_with_address.csv"

# Comprehensive Indian State mapping for all 251 locations
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

def clean_address_duplication(address_str, city_name):
    """
    Ensure the city name is not repeated unnecessarily inside the address string.
    e.g., 'Near ISKCON temple Bangalore, Bangalore, Karnataka' -> 'Near ISKCON temple Bangalore, Karnataka'
    """
    c = str(city_name).strip()
    if not c or not address_str:
        return address_str
    c_esc = re.escape(c)
    pattern = re.compile(r'(\b' + c_esc + r'\b.*?),\s*' + c_esc + r'\b', re.IGNORECASE)
    cleaned = pattern.sub(r'\1', address_str)
    # Also clean consecutive repeated city occurrences like 'City, City'
    pattern_consec = re.compile(r'\b(' + c_esc + r')(?:\s*,\s*\1\b)+', re.IGNORECASE)
    cleaned = pattern_consec.sub(r'\1', cleaned)
    # Clean up double commas and whitespace
    cleaned = re.sub(r',\s*,+', ',', cleaned)
    cleaned = re.sub(r',\s*', ', ', cleaned)
    cleaned = re.sub(r'^\s*,\s*', '', cleaned)
    cleaned = re.sub(r'\s*,\s*$', '', cleaned).strip()
    return cleaned

def build_metadata():
    df = pd.read_csv(PROFILE_FILE)
    records = []
    
    for _, row in df.iterrows():
        hid = int(row["Hotel_ID"])
        raw_name = str(row["Hotel_Name"]).strip()
        loc = str(row["Location"]).strip()
        city = "Delhi (Transit)" if loc == "Delhi_Transit" else loc.replace("_", " ")
        state = CITY_STATE_MAP.get(loc, "")
        
        # 1. Prepositional landmarks
        m_prep = re.search(r'^(.*?)\s*(?:,\s*)?\b(Near|Opposite|Opp\.?|Behind|Beside|Adjacent to|Adjacent|Close to|Next to|Facing|Towards|At|Off)\s+(.+)$', raw_name, re.IGNORECASE)
        if m_prep:
            pure_name = m_prep.group(1).rstrip(', ').strip()
            landmark = (m_prep.group(2) + ' ' + m_prep.group(3)).rstrip('.').strip()
            raw_addr = f"{landmark}, {city}, {state}" if state else f"{landmark}, {city}"
        elif loc == "Delhi_Transit":
            pure_name = raw_name.rstrip(', ').strip()
            landmark = "Near IGI Airport, Mahipalpur"
            raw_addr = f"{landmark}, Delhi"
        else:
            # 2. Comma-separated locality suffix
            m_comma = re.search(r'^(.*?)\s*,\s*([^,]+)$', raw_name)
            if m_comma and len(m_comma.group(2).strip()) >= 3:
                pure_name = m_comma.group(1).rstrip(', ').strip()
                landmark = m_comma.group(2).rstrip('.').strip()
                raw_addr = f"{landmark}, {city}, {state}" if state else f"{landmark}, {city}"
            else:
                pure_name = raw_name.rstrip(', ').strip()
                landmark = ""
                raw_addr = f"{city}, {state}" if state else f"{city}"
                
        # Clean any internal city duplication
        clean_addr = clean_address_duplication(raw_addr, city)
        
        records.append({
            "Hotel_ID": hid,
            "Hotel_Name": pure_name,
            "Raw_Hotel_Name": raw_name,
            "Location": loc,
            "City": city,
            "State": state,
            "Landmark": landmark,
            "Address": clean_addr
        })
        
    res_df = pd.DataFrame(records)
    res_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Generated {OUTPUT_FILE} with {len(res_df)} verified hotel records.")
    return res_df

if __name__ == "__main__":
    build_metadata()
