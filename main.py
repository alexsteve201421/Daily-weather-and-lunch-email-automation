import os
import requests

# Get city (optional, defaults to Irvine)
CITY = os.getenv("CITY", "Irvine,US")

# Get API key from GitHub Actions secret
API_KEY = os.environ["OPENWEATHER_API_KEY"]

# OpenWeather endpoint
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
description = data["weather"][0]["description"]

# Print result (this shows up in Actions logs)
print(f"Weather for {CITY}: {temp}°F, {description}")

