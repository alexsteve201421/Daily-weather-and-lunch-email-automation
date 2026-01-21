import os
import requests

# City (optional). If CITY isn't set, default to Irvine,US
CITY = os.getenv("CITY", "Irvine,US")

# API key from GitHub Actions secret
API_KEY = os.environ["OPENWEATHER_API_KEY"]

# Current weather endpoint
url = "https://api.openweathermap.org/data/2.5/weather"
params = {
    "q": CITY,
    "appid": API_KEY,
    "units": "imperial"
}

# Call the API
response = requests.get(url, params=params, timeout=20)
response.raise_for_status()
data = response.json()

# Extract info
temp = round(data["main"]["temp"])
description = data["weather"][0]["description"].lower()

# --- Decide temperature bucket ---
if temp < 60:
    temp_bucket = "Cool"
elif temp < 75:
    temp_bucket = "Mild"
else:
    temp_bucket = "Warm"

# --- Decide sky bucket ---
rain_words = ["rain", "drizzle", "shower", "thunderstorm"]
overcast_words = ["overcast", "mist", "fog", "marine"]

if any(word in description for word in rain_words):
    sky_bucket = "Rain"
elif any(word in description for word in overcast_words):
    sky_bucket = "Overcast / Marine Layer"
elif "cloud" in description or "clear" in description or "sun" in description:
    sky_bucket = "Clear / Partly Cloudy"
else:
    sky_bucket = "Clear / Partly Cloudy"

scenario = f"{temp_bucket} + {sky_bucket}"

print(f"Weather for {CITY}: {temp}°F, {description}")
print(f"Scenario: {scenario}")

