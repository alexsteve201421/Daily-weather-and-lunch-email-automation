import os
import requests
from datetime import datetime

# --------------------
# CONFIG
# --------------------
CITY = os.getenv("CITY", "Irvine,US")
API_KEY = os.environ["OPENWEATHER_API_KEY"]

# --------------------
# GET CURRENT WEATHER
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
description = data["weather"][0]["description"].lower()

# --------------------
# DECIDE LUNCH (INTERNAL LOGIC ONLY)
# --------------------
if temp < 60:
    lunch = "Quesadilla"
elif temp < 75:
    if "cloud" in description or "mist" in description:
        lunch = "Pasta"
    else:
        lunch = "Bean and cheese burrito"
else:
    if "clear" in description or "sun" in description:
        lunch = "Hummus sandwich"
    else:
        lunch = "Surprise me"

# --------------------
# BUILD EMAIL (NO WEATHER LOGIC MENTIONED)
# --------------------
today = datetime.now().strftime("%A, %B %d")

subject = f"Lunch idea for {today}"

email_body = f"""
Good morning Mom,

I just wanted to send a quick lunch idea for today.

For lunch, how about:
➡️ {lunch}

Totally flexible of course — just a suggestion 😊

Love,
Milan
"""

# --------------------
# OUTPUT (EMAIL PREVIEW)
# --------------------
print("====== EMAIL PREVIEW (NOT SENT) ======")
print("Subject:", subject)
print(email_body)
print("====================================")


