import os
import requests
from datetime import datetime

# --------------------
# CONFIG
# --------------------
CITY = os.getenv("CITY", "Irvine,US")
API_KEY = os.environ["OPENWEATHER_API_KEY"]

# --------------------
# CURRENT WEATHER (only thing we can use right now)
# --------------------
url = "https://api.openweathermap.org/data/2.5/weather"
params = {
    "q": CITY,
    "appid": API_KEY,
    "units": "imperial"
}

response = requests.get(url, params=params, timeout=20)
response.raise_for_status()
data = response.json()

temp = round(data["main"]["temp"])
desc = data["weather"][0]["description"].lower()

# --------------------
# TEMP BUCKET
# --------------------
if temp < 60:
    temp_bucket = "Cool"
elif temp < 75:
    temp_bucket = "Mild"
else:
    temp_bucket = "Warm"

# --------------------
# SKY BUCKET (based on current description)
# --------------------
if any(word in desc for word in ["rain", "drizzle", "shower"]):
    sky_bucket = "Rain"
elif any(word in desc for word in ["overcast", "mist", "fog"]):
    sky_bucket = "Overcast / Marine Layer"
else:
    sky_bucket = "Clear / Partly Cloudy"

scenario = f"{temp_bucket} + {sky_bucket}"

# --------------------
# YOUR LUNCH LOGIC (1 option each)
# --------------------
if scenario == "Mild + Clear / Partly Cloudy":
    lunch = "Bean and cheese burrito"
elif scenario == "Warm + Clear / Partly Cloudy":
    lunch = "Hummus sandwich"
elif scenario == "Cool + Clear / Partly Cloudy":
    lunch = "Quesadilla"
elif scenario == "Mild + Overcast / Marine Layer":
    lunch = "Pasta"
elif "Rain" in scenario:
    lunch = "Surprise me"
else:
    lunch = "Surprise me"

# --------------------
# "EMAIL" (printed to Actions log for now)
# --------------------
today = datetime.now().strftime("%A, %B %d")

subject = f"Good morning Milan — lunch plan for {today}"

body = f"""
Good morning Milan,

Here’s a quick check-in before the day gets going.

Right now in {CITY.split(',')[0]}, it’s {temp}°F with {desc}.

Based on that, today’s lunch plan is:
➡️ {lunch}

Have a great day at school — hope lunch hits the spot.

Love,
Dad
"""

print("====== EMAIL PREVIEW (NOT SENT YET) ======")
print("Subject:", subject)
print(body)
print("=========================================")
print(f"Scenario: {scenario}")
print(f"Lunch: {lunch}")




