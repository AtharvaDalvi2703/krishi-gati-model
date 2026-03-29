# 🌾 Krishi-Gati - Local Version

**AI-Powered Market Advisory System for Indian Farmers**

This is a fully local version that runs without Databricks or cloud services. It uses local CSV files for data and works completely offline (AI features are optional).

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## 📁 Project Structure

```
krishi-gati/
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── nashik_mandi_coords.csv     # Mandi locations (26 mandis)
├── predicted_mandi_prices.csv  # Price forecasts (4 days)
└── README.md                   # This file
```

## 🎯 Features

- **📍 Mandi Locator**: Find nearest mandis from your village
- **💰 Price Predictions**: 4-day price forecasts for Onion, Potato, Wheat
- **🚛 Transport Calculator**: Optimal vehicle selection and cost estimation
- **📊 Profit Optimizer**: Analyzes multiple scenarios to maximize profit
- **🗺️ Interactive Map**: Visual display of routes and mandis
- **🌐 Bilingual**: Works with Hindi, Marathi, and English input

## 💬 How to Use

Enter your details in any of these formats:

**English:**
- `I am from Dindori with 1500 kg onion`
- `Nashik farmer, 2000 kg potato to sell`

**Hindi:**
- `मैं दिंडोरी का किसान हूँ, 15 क्विंटल प्याज बेचना है`
- `नाशिक से 1000 किलो आलू`

**Hinglish:**
- `Satana se 1000 kg pyaz bechna hai`
- `Lasalgaon farmer with 20 quintal kanda`

## 🔧 Optional: Enable AI Features

For better text extraction, set your Gemini API key:

```bash
export GEMINI_API_KEY="your-api-key-here"
```

Get a free API key at: https://makersuite.google.com/app/apikey

**Note:** The app works perfectly fine without AI - it has built-in pattern matching for common inputs.

## 📊 Data Sources

- **Mandi Coordinates**: 26 markets in Nashik district
- **Price Forecasts**: Predicted prices for next 4 days
- **Supported Crops**: Onion (प्याज), Potato (आलू), Wheat (गेहूं)

## 🚛 Vehicle Options

| Vehicle | Capacity | Rate/km | Fixed Cost |
|---------|----------|---------|------------|
| Tata Ace | 750 kg | ₹18 | ₹300 |
| Mahindra Bolero | 1500 kg | ₹25 | ₹500 |
| Eicher 14ft | 4000 kg | ₹45 | ₹1200 |
| Truck (10 Ton) | 10000 kg | ₹70 | ₹2500 |

## 🔒 Privacy

- All data stays on your local machine
- No internet required for core functionality
- AI features (optional) use Google Gemini API

## 📞 Troubleshooting

**App won't start?**
```bash
pip install --upgrade streamlit folium streamlit-folium pandas
```

**Map not showing?**
- Make sure you have an internet connection for map tiles
- Or use offline tiles if available

**Wrong location detected?**
- Be more specific with village name
- Include "Nashik" or district name

## 🙏 Made with ❤️ for Indian Farmers

---

*भारतीय किसानों के लिए प्यार से बनाया गया*
