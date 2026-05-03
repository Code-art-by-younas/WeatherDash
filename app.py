"""
WeatherDash - Flask Backend with Caching
OpenWeather API Integration | Server-side time-based caching (10 min)
"""

import os
import time
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv  # optional, remove if not using .env

load_dotenv()  # remove if not using .env

app = Flask(__name__)

# Configuration
API_KEY = os.getenv("OPENWEATHER_API_KEY", "your_api_key_here")
BASE_URL = "https://api.openweathermap.org/data/2.5"
CACHE_DURATION = 600  # 10 minutes (in seconds)

# Simple in-memory cache
cache = {}

def get_cached_weather(city):
    """Return cached data if valid, else None"""
    if city in cache:
        data, timestamp = cache[city]
        if time.time() - timestamp < CACHE_DURATION:
            return data
        else:
            del cache[city]
    return None

def set_cached_weather(city, data):
    """Store data in cache with current timestamp"""
    cache[city] = (data, time.time())

def fetch_weather_data(city):
    """Fetch current weather and 5-day forecast from OpenWeather API"""
    try:
        # Current weather
        current_url = f"{BASE_URL}/weather?q={city}&appid={API_KEY}&units=metric"
        current_resp = requests.get(current_url, timeout=10)
        if current_resp.status_code != 200:
            return None, "City not found or API error"

        current = current_resp.json()

        # 5-day forecast (every 3 hours)
        forecast_url = f"{BASE_URL}/forecast?q={city}&appid={API_KEY}&units=metric"
        forecast_resp = requests.get(forecast_url, timeout=10)
        if forecast_resp.status_code != 200:
            return None, "Forecast data unavailable"

        forecast = forecast_resp.json()

        # Extract daily forecast (one per day at 12:00)
        daily_forecast = []
        seen_dates = set()
        for item in forecast["list"]:
            date = item["dt_txt"].split()[0]
            if date not in seen_dates and len(daily_forecast) < 5:
                seen_dates.add(date)
                daily_forecast.append({
                    "date": date,
                    "temp": round(item["main"]["temp"]),
                    "condition": item["weather"][0]["description"].capitalize(),
                    "icon": item["weather"][0]["icon"]
                })

        result = {
            "city": current["name"],
            "country": current["sys"]["country"],
            "temp": round(current["main"]["temp"]),
            "feels_like": round(current["main"]["feels_like"]),
            "humidity": current["main"]["humidity"],
            "condition": current["weather"][0]["description"].capitalize(),
            "icon": current["weather"][0]["icon"],
            "wind_speed": current["wind"]["speed"],
            "forecast": daily_forecast
        }
        return result, None

    except requests.exceptions.RequestException as e:
        return None, f"Network error: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

@app.route("/")
def index():
    """Serve main page"""
    return render_template("index.html")

@app.route("/api/weather")
def weather_api():
    """JSON endpoint with caching"""
    city = request.args.get("city", "").strip()
    if not city:
        return jsonify({"error": "City name is required"}), 400

    # Check cache
    cached = get_cached_weather(city.lower())
    if cached:
        return jsonify({"data": cached, "cached": True})

    # Fetch fresh data
    data, error = fetch_weather_data(city)
    if error:
        return jsonify({"error": error}), 404

    # Store in cache
    set_cached_weather(city.lower(), data)
    return jsonify({"data": data, "cached": False})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)