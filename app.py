#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Krishi-Gati Local App
AI-Powered Market Advisory System for Indian Farmers
Fully Local Version - No Databricks Required
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import json
import math
import time
import requests
import os
from datetime import datetime
from pathlib import Path

# =============================================
# CONFIGURATION
# =============================================

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.resolve()

# Vehicle Catalog
VEHICLE_CATALOG = {
    'Tata Ace': {'capacity_kg': 750, 'rate_per_km': 18, 'fixed_cost': 300, 'avg_speed_kmh': 40},
    'Mahindra Bolero Pickup': {'capacity_kg': 1500, 'rate_per_km': 25, 'fixed_cost': 500, 'avg_speed_kmh': 50},
    'Eicher 14ft': {'capacity_kg': 4000, 'rate_per_km': 45, 'fixed_cost': 1200, 'avg_speed_kmh': 45},
    'Truck (10 Ton)': {'capacity_kg': 10000, 'rate_per_km': 70, 'fixed_cost': 2500, 'avg_speed_kmh': 40}
}

# Quality and Decay Parameters
OPPORTUNITY_COST_PER_DAY = 400
WEIGHT_DECAY = {'onion': 0.01, 'potato': 0.008, 'wheat': 0.001}
QUALITY_PENALTY_PER_Q = {'onion': 30.0, 'potato': 24.0, 'wheat': 8.0}
STORAGE_RENT_PER_Q = {'onion': 10.0, 'potato': 12.0, 'wheat': 14}

# Known locations in Nashik district (fallback for geocoding)
KNOWN_LOCATIONS = {
    'nashik': (20.005, 73.7889),
    'nasik': (20.005, 73.7889),
    'dindori': (20.2012, 73.8322),
    'lasalgaon': (20.1437, 74.2231),
    'pimpalgaon': (20.1656, 73.9856),
    'malegaon': (20.5524, 74.5244),
    'nandgaon': (20.3117, 74.6548),
    'satana': (20.59, 74.2),
    'kalvan': (20.4851, 73.9169),
    'manmad': (20.2483, 74.4379),
    'chandvad': (20.3306, 74.2464),
    'sinner': (19.8486, 74.0019),
    'yeola': (20.0353, 74.4856),
    'nampur': (20.5843, 74.1167),
    'devala': (20.35, 74.15),
    'vani': (20.32, 73.89),
    'niphad': (20.1437, 74.2231),
    'vinchur': (20.1171, 74.2305),
    'umrane': (20.4, 74.28),
    'suragana': (20.41, 73.61),
    'igatpuri': (19.6958, 73.5564),
    'trimbakeshwar': (19.9324, 73.5301),
    'ozar': (20.0884, 73.9294),
    'sinnar': (19.8486, 74.0019),
}

# =============================================
# DATA LOADING FUNCTIONS (LOCAL CSV)
# =============================================

@st.cache_data(ttl=3600)
def load_mandi_coords():
    """Load mandi coordinates from local CSV file."""
    csv_path = SCRIPT_DIR / "nashik_mandi_coords.csv"
    try:
        df = pd.read_csv(csv_path)
        return df
    except Exception as e:
        st.error(f"Error loading mandi coordinates: {e}")
        # Fallback data
        return pd.DataFrame({
            'District_Name': ['Nashik', 'Nashik', 'Nashik'],
            'Market_Name': ['Dindori', 'Satana', 'Lasalgaon'],
            'latitude': [20.2012, 20.59, 20.1437],
            'longitude': [73.8322, 74.2, 74.2231]
        })

@st.cache_data(ttl=3600)
def load_price_forecasts():
    """Load price forecasts from local CSV file."""
    csv_path = SCRIPT_DIR / "predicted_mandi_prices.csv"
    try:
        df = pd.read_csv(csv_path)
        # Clean up date format
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        return df
    except Exception as e:
        st.error(f"Error loading price forecasts: {e}")
        # Fallback data
        return pd.DataFrame({
            'Date': pd.date_range('2026-03-29', periods=7),
            'Mandi': ['Dindori'] * 7,
            'Commodity': ['Onion'] * 7,
            'Predicted_Price': [1400, 1420, 1440, 1460, 1480, 1500, 1520]
        })

# =============================================
# CORE FUNCTIONS
# =============================================

def get_coords_local(city, region="Maharashtra, India"):
    """Get coordinates - first check local database, then try geopy."""
    if not city:
        return None, None
    
    # Normalize city name
    city_lower = city.lower().strip()
    
    # First check our known locations
    if city_lower in KNOWN_LOCATIONS:
        return KNOWN_LOCATIONS[city_lower]
    
    # Check if it's a partial match
    for known_city, coords in KNOWN_LOCATIONS.items():
        if known_city in city_lower or city_lower in known_city:
            return coords
    
    # Try geopy as fallback (with error handling for network issues)
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="krishi_gati_local_app")
        search_queries = [
            f"{city}, Nashik, Maharashtra, India",
            f"{city}, Maharashtra, India",
            f"{city}, India"
        ]
        
        for query in search_queries:
            try:
                loc = geolocator.geocode(query, timeout=5)
                if loc:
                    # Validate it's in India
                    if 6 <= loc.latitude <= 38 and 68 <= loc.longitude <= 98:
                        return (loc.latitude, loc.longitude)
            except:
                continue
    except:
        pass
    
    # Final fallback - return Nashik city center
    return (20.005, 73.7889)

def extract_logic_local(text):
    """Extract agricultural data from farmer's text using pattern matching."""
    text_lower = text.lower()
    
    # Location extraction patterns
    location = None
    
    # Common location patterns
    location_keywords = ['from', 'में', 'का', 'की', 'के', 'village', 'गाँव', 'गांव', 'town']
    
    # Try to find location from known places
    for place in KNOWN_LOCATIONS.keys():
        if place in text_lower:
            location = place.capitalize()
            break
    
    # If no known location, try to extract using patterns
    if not location:
        words = text.replace(',', ' ').replace('.', ' ').split()
        for i, word in enumerate(words):
            word_lower = word.lower()
            if word_lower in ['from', 'में', 'का', 'की']:
                if i + 1 < len(words):
                    location = words[i + 1].strip()
                    break
            # Check if word looks like a place name (capitalized, not a number)
            if word[0].isupper() and not word.isdigit() and len(word) > 2:
                if word_lower not in ['i', 'my', 'have', 'want', 'sell', 'the', 'and', 'मैं', 'मेरे']:
                    location = word
                    break
    
    # Default to Nashik if nothing found
    if not location:
        location = "Nashik"
    
    # Crop and quantity extraction
    crops = [
        {"name": "onion", "quantity_kg": 0},
        {"name": "potato", "quantity_kg": 0},
        {"name": "wheat", "quantity_kg": 0}
    ]
    
    # Crop name mappings (Hindi/Marathi to English)
    crop_mappings = {
        'onion': ['onion', 'प्याज', 'प्याज़', 'कांदा', 'kanda', 'pyaz', 'pyaaz'],
        'potato': ['potato', 'आलू', 'aloo', 'alu', 'batata', 'बटाटा'],
        'wheat': ['wheat', 'गेहूं', 'गेहूँ', 'gehun', 'gehu', 'गहू', 'गव्हा']
    }
    
    # Find quantities using regex-like patterns
    import re
    
    # Pattern: number followed by kg/quintal/ton or crop name
    quantity_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:kg|किलो|kilo)',
        r'(\d+(?:\.\d+)?)\s*(?:quintal|क्विंटल|quintals)',
        r'(\d+(?:\.\d+)?)\s*(?:ton|टन|tons)',
    ]
    
    for crop_english, aliases in crop_mappings.items():
        for alias in aliases:
            if alias in text_lower:
                # Find nearby numbers
                # Look for patterns like "1000 kg onion" or "onion 1000 kg"
                for pattern in quantity_patterns:
                    matches = re.findall(pattern, text_lower)
                    if matches:
                        qty = float(matches[0])
                        # Convert quintals to kg
                        if 'quintal' in text_lower or 'क्विंटल' in text_lower:
                            qty *= 100
                        # Convert tons to kg
                        if 'ton' in text_lower or 'टन' in text_lower:
                            qty *= 1000
                        
                        for crop in crops:
                            if crop['name'] == crop_english:
                                crop['quantity_kg'] = int(qty)
                        break
                
                # If no quantity found but crop mentioned, default to 1000 kg
                for crop in crops:
                    if crop['name'] == crop_english and crop['quantity_kg'] == 0:
                        # Look for any number in text
                        numbers = re.findall(r'(\d+)', text)
                        if numbers:
                            qty = int(numbers[0])
                            if qty < 10:
                                qty *= 100  # Assume quintals
                            crop['quantity_kg'] = qty
                        else:
                            crop['quantity_kg'] = 1000  # Default
                break
    
    return {
        "location_name": location,
        "crops": crops
    }

def extract_logic_gemini(text):
    """Uses Gemini to extract structured data from farmer's text."""
    try:
        import google.generativeai as genai
        
        api_key = os.getenv('GEMINI_API_KEY', '')
        if not api_key:
            return extract_logic_local(text)
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-lite')

        prompt = f"""
        Extract agricultural data from this text: "{text}"

        Return ONLY a JSON object with this exact structure:
        {{
            "location_name": "Extract city/village name here",
            "crops": [
                {{"name": "onion", "quantity_kg": 0}},
                {{"name": "potato", "quantity_kg": 0}},
                {{"name": "wheat", "quantity_kg": 0}}
            ]
        }}

        Rules:
        1. If a crop is mentioned, put the quantity in kg. If not mentioned, put 0.
        2. Translate Marathi/Hindi crop names to English (e.g., Kanda/प्याज -> onion, Aloo/आलू -> potato, Gehun/गेहूं -> wheat).
        3. Convert quintals to kg (1 quintal = 100 kg).
        4. Return ONLY the JSON, no markdown, no explanation.
        """

        response = model.generate_content(prompt)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()

        return json.loads(clean_json)
    except Exception as e:
        # Fallback to local extraction
        return extract_logic_local(text)

def process_farmer_request(text_input, use_ai=True):
    """Main function to process farmer input."""
    if not text_input:
        return {"error": "No text input provided."}

    # Try AI extraction first, fallback to local
    if use_ai:
        extracted_data = extract_logic_gemini(text_input)
    else:
        extracted_data = extract_logic_local(text_input)
    
    city = extracted_data.get("location_name")
    lat, lon = get_coords_local(city, region="Maharashtra, India")

    if not lat:
        lat, lon = 20.005, 73.7889  # Default to Nashik
        city = city or "Nashik"

    green_json = {
        "farmer_location": {"name": city, "lat": lat, "lon": lon},
        "crops": extracted_data["crops"],
        "window_size_days": 7
    }

    return {"green_json": green_json}

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate Haversine distance between two points."""
    R = 6371.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def get_mandi_distances(farmer_lat, farmer_lon):
    """Calculates distance from farmer to all mandis."""
    mandi_df = load_mandi_coords()
    
    mandi_df['distance_km'] = mandi_df.apply(
        lambda row: round(calculate_haversine_distance(
            farmer_lat, farmer_lon, 
            row['latitude'], row['longitude']
        ), 2),
        axis=1
    )
    
    return mandi_df.sort_values('distance_km')

def get_real_road_distance(row, f_lat, f_lon):
    """Get road distance - uses straight-line approximation if network unavailable."""
    # Use straight-line distance with 1.3x factor for road
    straight_line = calculate_haversine_distance(f_lat, f_lon, row['latitude'], row['longitude'])
    road_km = straight_line * 1.3
    # Estimate duration: average 35 km/h in rural Maharashtra
    duration_mins = (road_km / 35) * 60
    return pd.Series([round(road_km, 2), round(duration_mins, 0)])

def calculate_mandi_logistics(df, weights_kg_dict):
    """Calculates the best vehicle and total cost."""
    total_weight = sum(weights_kg_dict.values())
    
    def get_row_transport_stats(row):
        suitable_vehicles = [v for v, specs in VEHICLE_CATALOG.items()
                           if specs['capacity_kg'] >= total_weight]
        
        if suitable_vehicles:
            best_v_name = min(suitable_vehicles,
                            key=lambda x: VEHICLE_CATALOG[x]['rate_per_km'])
            units_needed = 1
        else:
            best_v_name = max(VEHICLE_CATALOG,
                            key=lambda x: VEHICLE_CATALOG[x]['capacity_kg'])
            capacity = VEHICLE_CATALOG[best_v_name]['capacity_kg']
            units_needed = math.ceil(total_weight / capacity)
        
        v_specs = VEHICLE_CATALOG[best_v_name]
        distance_cost = row['road_km'] * v_specs['rate_per_km'] * units_needed
        fixed_total = v_specs['fixed_cost'] * units_needed
        total_cost = distance_cost + fixed_total
        
        return pd.Series([best_v_name, units_needed, round(total_cost, 2)])
    
    df[['selected_vehicle', 'units_needed', 'total_logistics_cost']] = \
        df.apply(get_row_transport_stats, axis=1)
    
    return df

def calculate_optimal_timing(logistics_df, weights_kg_dict):
    """Calculates optimal selling time."""
    forecast_df = load_price_forecasts()
    
    # Clean mandi names for matching
    forecast_df['Mandi_Clean'] = forecast_df['Mandi'].str.split('(').str[0].str.strip()
    
    price_pivot = forecast_df.pivot_table(
        index=['Date', 'Mandi_Clean'],
        columns='Commodity',
        values='Predicted_Price'
    ).reset_index().fillna(0)
    
    # Normalize column names
    price_pivot.columns = [col.lower() if col not in ['Date', 'Mandi_Clean'] else col
                          for col in price_pivot.columns]
    
    price_pivot['Date'] = pd.to_datetime(price_pivot['Date'])
    today = price_pivot['Date'].min()
    
    results = []
    
    for _, mandi_row in logistics_df.iterrows():
        m_name = mandi_row['Market_Name'].split('(')[0].strip()
        t_cost = mandi_row['total_logistics_cost']
        
        mandi_prices = price_pivot[price_pivot['Mandi_Clean'] == m_name]
        
        for _, day in mandi_prices.iterrows():
            days_waiting = (day['Date'] - today).days
            
            total_rent = 0
            if days_waiting > 0:
                for crop, weight in weights_kg_dict.items():
                    crop_lower = crop.lower()
                    total_rent += (weight / 100) * \
                                 STORAGE_RENT_PER_Q.get(crop_lower, 10.0) * days_waiting
            
            revenue = 0
            for crop, weight in weights_kg_dict.items():
                crop_lower = crop.lower()
                adj_weight = weight * (1 - (WEIGHT_DECAY.get(crop_lower, 0) * days_waiting))
                market_price = day.get(crop_lower, 0)
                adj_price = market_price - \
                          (QUALITY_PENALTY_PER_Q.get(crop_lower, 0) * days_waiting)
                revenue += (adj_weight * adj_price / 100)
            
            net_profit = revenue - t_cost - total_rent - \
                        (OPPORTUNITY_COST_PER_DAY * days_waiting)
            
            results.append({
                'Arrival_Date': day['Date'].strftime('%d %b'),
                'Mandi': m_name,
                'Days_Wait': days_waiting,
                'Gross_Revenue': round(revenue, 2),
                'Transport_Cost': round(t_cost, 2),
                'Storage_Rent': round(total_rent, 2),
                'Net_Profit': round(net_profit, 2),
                'latitude': mandi_row['latitude'],
                'longitude': mandi_row['longitude'],
                'selected_vehicle': mandi_row['selected_vehicle']
            })
    
    if not results:
        return pd.DataFrame()
    
    return pd.DataFrame(results).sort_values('Net_Profit', ascending=False)

def run_krishi_gati_pipeline(farmer_input_text, use_ai=True):
    """Complete end-to-end pipeline."""
    result = process_farmer_request(text_input=farmer_input_text, use_ai=use_ai)
    
    if "error" in result:
        return {"error": result["error"]}
    
    green_json = result['green_json']
    farmer_location = green_json['farmer_location']
    crops = green_json['crops']
    
    # Calculate distances
    distances_df = get_mandi_distances(
        farmer_location['lat'],
        farmer_location['lon']
    )
    top_10_mandis = distances_df.head(10).copy()
    
    # Get road distances (approximated)
    top_10_mandis[['road_km', 'duration_mins']] = top_10_mandis.apply(
        get_real_road_distance,
        axis=1,
        args=(farmer_location['lat'], farmer_location['lon'])
    )
    top_5_mandis = top_10_mandis.sort_values('road_km').head(5)
    
    # Calculate logistics
    weights_dict = {crop['name']: crop['quantity_kg']
                   for crop in crops if crop['quantity_kg'] > 0}
    
    if not weights_dict:
        return {"error": "No crops with quantity specified. Please mention crop name and quantity."}
    
    logistics_df = calculate_mandi_logistics(top_5_mandis, weights_dict)
    
    # Calculate optimal timing
    recommendations = calculate_optimal_timing(logistics_df, weights_dict)
    
    if recommendations.empty:
        return {"error": "Could not calculate recommendations. Please try again."}
    
    top_5_recommendations = recommendations.head(5)
    
    winner = top_5_recommendations.iloc[0] if len(top_5_recommendations) > 0 else None
    
    output_json = top_5_recommendations[[
        'Mandi', 'Arrival_Date', 'Days_Wait',
        'latitude', 'longitude', 'selected_vehicle', 'Net_Profit'
    ]].to_dict(orient='records')
    
    return {
        "input_data": green_json,
        "recommendations": output_json,
        "summary": {
            "best_mandi": winner['Mandi'] if winner is not None else None,
            "best_profit": float(winner['Net_Profit']) if winner is not None else 0,
            "total_scenarios_analyzed": len(recommendations)
        }
    }

def detect_language(text):
    """Detects the language of input text."""
    if any('\u0900' <= char <= '\u097F' for char in text):
        return 'hindi'
    return 'english'

def translate_response_local(english_text, target_language='hindi'):
    """Simple translation helper - returns English if translation unavailable."""
    if target_language == 'english':
        return english_text
    
    # Try using Gemini for translation
    try:
        import google.generativeai as genai
        api_key = os.getenv('GEMINI_API_KEY', '')
        if api_key:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash-lite')
            lang_name = "Hindi" if target_language == 'hindi' else "Marathi"
            
            prompt = f"""
            Translate the following English text to {lang_name}.
            Keep numbers, dates, and proper nouns as they are.
            Return ONLY the translation, no explanation.
            
            English text:
            {english_text}
            """
            
            response = model.generate_content(prompt)
            return response.text.strip()
    except:
        pass
    
    return english_text

def format_recommendation_message(result, language='english'):
    """Formats the recommendation into a user-friendly message - bilingual output."""
    if "error" in result:
        return f"❌ Error: {result['error']}"
    
    summary = result['summary']
    top_rec = result['recommendations'][0]
    
    # Always show English
    english_message = f"""🏆 <b>Best Recommendation / सर्वश्रेष्ठ सिफारिश:</b>

📍 <b>Market / मंडी:</b> {summary['best_mandi']}
📅 <b>Sell Date / बिक्री तिथि:</b> {top_rec['Arrival_Date']}
⏳ <b>Wait Time / प्रतीक्षा:</b> {top_rec['Days_Wait']} days / दिन
🚛 <b>Vehicle / वाहन:</b> {top_rec['selected_vehicle']}
💰 <b>Expected Profit / अपेक्षित लाभ:</b> ₹{summary['best_profit']:,.2f}

📊 We analyzed {summary['total_scenarios_analyzed']} scenarios! / {summary['total_scenarios_analyzed']} परिदृश्यों का विश्लेषण किया!
"""
    
    return english_message

# =============================================
# STREAMLIT WEB APP
# =============================================

st.set_page_config(
    page_title="🌾 Krishi-Gati - Farmer Market Advisor",
    page_icon="🌾",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #2E7D32;
        text-align: center;
        padding: 1rem 0;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #555;
        text-align: center;
        margin-bottom: 2rem;
    }
    .result-box {
        background-color: #A9A9A9;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #4CAF50;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #E3F2FD;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2196F3;
        margin: 0.5rem 0;
    }
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        font-size: 1.1rem;
        padding: 0.75rem 2rem;
        border-radius: 8px;
    }
    .stButton > button:hover {
        background-color: #388E3C;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🌾 Krishi-Gati</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Find the Best Market for Your Crops | आपकी फसल के लिए सर्वश्रेष्ठ मंडी खोजें</div>', unsafe_allow_html=True)

# Sidebar with info
with st.sidebar:
    st.markdown("### ℹ️ About")
    st.markdown("""
    **Krishi-Gati** helps farmers find the best market (mandi) to sell their crops.
    
    **Features:**
    - 📍 Find nearest mandis
    - 💰 Price predictions for 4 days
    - 🚛 Transport cost calculation
    - 📊 Profit optimization
    
    **Supported Crops:**
    - 🧅 Onion (प्याज/कांदा)
    - 🥔 Potato (आलू/बटाटा)
    - 🌾 Wheat (गेहूं)
    """)
    
    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    use_ai = st.checkbox("Use AI for text extraction", value=True, 
                         help="Uses Gemini AI if API key is available")
    
    st.markdown("---")
    st.markdown("### 📊 Data Info")
    mandi_df = load_mandi_coords()
    price_df = load_price_forecasts()
    st.info(f"📍 {len(mandi_df)} Mandis loaded")
    st.info(f"📈 {len(price_df)} Price forecasts")

# Instructions
with st.expander("📝 How to use | उपयोग कैसे करें", expanded=False):
    st.markdown("""
    **English:** 
    1. Enter your village/city name
    2. Mention your crop (onion, potato, or wheat)
    3. Mention quantity in kg or quintals
    4. Click "Get Recommendation"
    
    **हिंदी:** 
    1. अपने गाँव/शहर का नाम लिखें
    2. अपनी फसल बताएं (प्याज, आलू, या गेहूं)
    3. मात्रा किलो या क्विंटल में बताएं
    4. "Get Recommendation" बटन दबाएं
    
    **Examples:**
    - `I am from Dindori and have 1500 kg onion to sell`
    - `मैं नाशिक का किसान हूँ, मेरे पास 20 क्विंटल आलू है`
    - `Satana se 1000 kg pyaz bechna hai`
    """)

# Initialize session state for results persistence
if 'result' not in st.session_state:
    st.session_state.result = None
if 'input_language' not in st.session_state:
    st.session_state.input_language = 'english'
if 'last_input' not in st.session_state:
    st.session_state.last_input = ""

# Input section
st.markdown("### 💬 Enter Your Details | अपना विवरण दर्ज करें")

col1, col2 = st.columns([3, 1])

with col1:
    farmer_input = st.text_area(
        "Tell us about your crops (Hindi/Marathi/English):",
        placeholder="Example: मैं दिंडोरी का किसान हूँ और मेरे पास 1500 किलो प्याज हैं\nOr: I am from Nashik with 1000 kg potatoes",
        height=100,
        key="farmer_input_area"
    )

with col2:
    st.write("")
    st.write("")
    submit_button = st.button("🚀 Get Recommendation", type="primary", use_container_width=True)

# Quick input buttons
st.markdown("**Quick Examples:**")
quick_cols = st.columns(4)
with quick_cols[0]:
    if st.button("🧅 Dindori 1500kg Onion"):
        st.session_state.quick_input = "I am from Dindori with 1500 kg onion"
        st.rerun()
with quick_cols[1]:
    if st.button("🥔 Nashik 2000kg Potato"):
        st.session_state.quick_input = "Nashik farmer with 2000 kg potato"
        st.rerun()
with quick_cols[2]:
    if st.button("🌾 Satana 1000kg Wheat"):
        st.session_state.quick_input = "From Satana, 1000 kg wheat to sell"
        st.rerun()
with quick_cols[3]:
    if st.button("🧅 लासलगाव 10 क्विंटल प्याज"):
        st.session_state.quick_input = "लासलगाव से 10 क्विंटल प्याज बेचना है"
        st.rerun()

# Handle quick input
if 'quick_input' in st.session_state:
    farmer_input = st.session_state.quick_input
    del st.session_state.quick_input
    submit_button = True

# Process when button is clicked
if submit_button and farmer_input:
    with st.spinner("🔍 Analyzing best markets for you... कृपया प्रतीक्षा करें..."):
        try:
            input_language = detect_language(farmer_input)
            result = run_krishi_gati_pipeline(farmer_input_text=farmer_input, use_ai=use_ai)
            
            # Store results in session state
            st.session_state.result = result
            st.session_state.input_language = input_language
            st.session_state.last_input = farmer_input
            
        except Exception as e:
            st.session_state.result = {"error": str(e)}
            st.session_state.input_language = 'english'

elif submit_button:
    st.warning("⚠️ Please enter your details above. | कृपया ऊपर अपना विवरण दर्ज करें।")

# Display results from session state (persists across reruns)
if st.session_state.result is not None:
    result = st.session_state.result
    input_language = st.session_state.input_language
    
    if "error" in result:
        st.error(f"❌ {result['error']}")
        st.info("💡 Tip: Make sure to mention your location and crop with quantity clearly.")
    else:
        st.success("✅ Analysis Complete! विश्लेषण पूर्ण!")
        
        # Clear results button
        if st.button("🔄 New Search | नई खोज"):
            st.session_state.result = None
            st.session_state.last_input = ""
            st.rerun()
        
        # Show extracted data
        with st.expander("🔍 Extracted Information | निकाली गई जानकारी", expanded=False):
            input_data = result['input_data']
            st.markdown(f"**Location:** {input_data['farmer_location']['name']}")
            st.markdown(f"**Coordinates:** {input_data['farmer_location']['lat']:.4f}, {input_data['farmer_location']['lon']:.4f}")
            crops_text = ", ".join([f"{c['name']}: {c['quantity_kg']} kg" for c in input_data['crops'] if c['quantity_kg'] > 0])
            st.markdown(f"**Crops:** {crops_text}")
        
        col_result, col_map = st.columns([1, 1.5])
        
        with col_result:
            st.markdown("### 🏆 Best Recommendation | सर्वश्रेष्ठ सिफारिश")
            message = format_recommendation_message(result, input_language)
            st.markdown(f'<div class="result-box">{message.replace(chr(10), "<br>")}</div>',
                      unsafe_allow_html=True)
            
            st.markdown("### 📊 Top 5 Markets | शीर्ष 5 मंडियां")
            recs_df = pd.DataFrame(result['recommendations'])
            display_df = recs_df[['Mandi', 'Arrival_Date', 'Days_Wait', 'Net_Profit']].copy()
            display_df.columns = ['Market (मंडी)', 'Date (तारीख)', 'Wait (दिन)', 'Profit (लाभ ₹)']
            display_df['Profit (लाभ ₹)'] = display_df['Profit (लाभ ₹)'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        with col_map:
            st.markdown("### 🗺️ Location Map | स्थान मानचित्र")
            
            farmer_loc = result['input_data']['farmer_location']
            center_lat = farmer_loc['lat']
            center_lon = farmer_loc['lon']
            
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=10,
                tiles="OpenStreetMap"
            )
            
            # Add farmer marker
            folium.Marker(
                location=[center_lat, center_lon],
                popup=f"<b>Your Location</b><br>{farmer_loc['name']}",
                icon=folium.Icon(color='green', icon='home', prefix='fa'),
                tooltip="📍 Your Location"
            ).add_to(m)
            
            # Add mandi markers
            for i, rec in enumerate(result['recommendations'][:5]):
                color = 'red' if i == 0 else 'orange' if i < 3 else 'blue'
                folium.Marker(
                    location=[rec['latitude'], rec['longitude']],
                    popup=f"<b>#{i+1} {rec['Mandi']}</b><br>💰 Profit: ₹{rec['Net_Profit']:,.2f}<br>📅 Date: {rec['Arrival_Date']}<br>🚛 {rec['selected_vehicle']}",
                    icon=folium.Icon(color=color, icon='shopping-cart', prefix='fa'),
                    tooltip=f"#{i+1}: {rec['Mandi']} (₹{rec['Net_Profit']:,.0f})"
                ).add_to(m)
                
                # Draw line from farmer to mandi
                folium.PolyLine(
                    locations=[[center_lat, center_lon], [rec['latitude'], rec['longitude']]],
                    color=color,
                    weight=2 if i > 0 else 3,
                    opacity=0.6 if i > 0 else 0.8,
                    dash_array='5' if i > 0 else None
                ).add_to(m)
            
            st_folium(m, width=None, height=450)
        
        # Additional insights
        st.markdown("---")
        st.markdown("### 📈 Analysis Summary | विश्लेषण सारांश")
        
        insight_cols = st.columns(4)
        with insight_cols[0]:
            st.metric("🎯 Best Market / मंडी", result['summary']['best_mandi'])
        with insight_cols[1]:
            st.metric("💰 Max Profit / लाभ", f"₹{result['summary']['best_profit']:,.0f}")
        with insight_cols[2]:
            st.metric("📊 Scenarios / परिदृश्य", result['summary']['total_scenarios_analyzed'])
        with insight_cols[3]:
            best_rec = result['recommendations'][0]
            st.metric("🚛 Vehicle / वाहन", best_rec['selected_vehicle'])

# Footer
st.markdown("---")
col_foot1, col_foot2, col_foot3 = st.columns(3)
with col_foot1:
    st.markdown("**🌾 Krishi-Gati**")
    st.caption("Empowering Indian Farmers")
with col_foot2:
    st.markdown("**📞 Support**")
    st.caption("Local Version - No Internet Required")
with col_foot3:
    st.markdown("**📍 Coverage**")
    st.caption("Nashik District, Maharashtra")

st.markdown("""
<div style="text-align: center; color: #888; padding: 1rem;">
    Made with ❤️ for Indian Farmers | भारतीय किसानों के लिए प्यार से बनाया गया
</div>
""", unsafe_allow_html=True)
