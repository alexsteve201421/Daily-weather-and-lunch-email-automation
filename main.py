import os
import requests
import smtplib
import ssl
import datetime
from email.message import EmailMessage

# -----------------------------
# SETTINGS (read from env)
# -----------------------------
CITY = os.getenv("CITY", "Irvine,US")

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# Weekend override for testing
# Set in Actions env as: FORCE_SEND: "true"
FORCE_SEND = os.getenv("FORCE_SEND", "false").lower() == "true"


# -----------------------------
# 1) WEEKDAY / WEEKEND LOGIC
# -----------------------------
now_local = datetime.datetime.now()
is_weekend = now_local.weekday() >= 5  # 5=Sat, 6=Sun

if is_weekend and not FORCE_SEND:
    print("Weekend detected (local). Skipping email.")
    raise SystemExit(0)


# -----------------------------
# 2) GET CURRENT WEATHER
# -----------------------------
if not OPENWEATHER_API_KEY:
    raise ValueError("Missing OPENWEATHER_API_KEY environment variable.")

url = "https://api.openweathermap.org/data/2.5/weather"
params = {
    "q": CITY,
    "appid": OPENWEATHER_API_KEY,
    "units": "imperial",
}

response = requests.get(url, params=params, timeout=20)
response.raise_for_status()
data = response.json()

temp_f = round(data["main"]["temp"])
description = data["weather"][0]["description"].lower()


# -----------------------------
# 3) CLASSIFY WEATHER INTO BUCKETS
# -----------------------------
# Temperature bucket
if temp_f < 60:
    temp_bucket = "Cool"
elif temp_f < 75:
    temp_bucket = "Mild"
else:
    temp_bucket = "Warm"

# Sky bucket
rain_words = ["rain", "drizzle", "thunderstorm", "shower"]
marine_words = ["mist", "fog", "haze"]
overcast_words = ["overcast", "cloud", "clouds"]

if any(w in description for w in rain_words):
    sky_bucket = "Rain"
elif any(w in description for w in marine_words):
    sky_bucket = "Overcast / Marine Layer"
elif any(w in description for w in overcast_words):
    # If it’s cloudy but not marine/fog, treat as partly cloudy/overcast bucket
    sky_bucket = "Clear / Partly Cloudy"
else:
    sky_bucket = "Clear / Partly Cloudy"

scenario = f"{temp_bucket} + {sky_bucket}"


# -----------------------------
# 4) LUNCH LOGIC (BASED ON WEATHER)
# Your exact mapping:
# Mild + Clear/Partly Cloudy = bean and cheese burrito
# Warm + Clear/Sunny = hummus sandwich
# Cool + Clear/Cloudy = quesadilla
# Mild + Overcast/Marine Layer = pasta
# Mild + Rain = surprise me
# -----------------------------
def choose_lunch(temp_bucket: str, sky_bucket: str) -> str:
    # Warm + Clear / Partly Cloudy -> hummus sandwich
    if temp_bucket == "Warm" and sky_bucket == "Clear / Partly Cloudy":
        return "Hummus sandwich"

    # Mild + Clear / Partly Cloudy -> bean and cheese burrito
    if temp_bucket == "Mild" and sky_bucket == "Clear / Partly Cloudy":
        return "Bean and cheese burrito"

    # Mild + Overcast / Marine Layer -> pasta
    if temp_bucket == "Mild" and sky_bucket == "Overcast / Marine Layer":
        return "Pasta"

    # Mild + Rain -> surprise me
    if temp_bucket == "Mild" and sky_bucket == "Rain":
        return "Surprise me"

    # Cool + (anything not rain) -> quesadilla
    if temp_bucket == "Cool" and sky_bucket != "Rain":
        return "Quesadilla"

    # Fallback
    return "Surprise me"


lunch = choose_lunch(temp_bucket, sky_bucket)


# -----------------------------
# 5) BUILD A REAL EMAIL + SEND
# -----------------------------
if not EMAIL_FROM or not EMAIL_TO or not GMAIL_APP_PASSWORD:
    raise ValueError(
        "Missing one or more email env vars: EMAIL_FROM, EMAIL_TO, GMAIL_APP_PASSWORD"
    )

# Friendly subject + body (real email)
subject = f"Daily Weather + Lunch — {CITY.split(',')[0]}"

date_str = now_local.strftime("%A, %B %d")
time_str = now_local.strftime("%I:%M %p").lstrip("0")

body = f"""Hi Mom,

Here’s today’s quick update for {CITY}:

Weather right now: {temp_f}°F, {description}
Category: {scenario}

Lunch idea for today: {lunch}

Love,
Milan
"""

msg = EmailMessage()
msg["From"] = EMAIL_FROM
msg["To"] = EMAIL_TO
msg["Subject"] = subject
msg.set_content(body)

context = ssl.create_default_context()

with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
    server.login(EMAIL_FROM, GMAIL_APP_PASSWORD)
    server.send_message(msg)

print("Email sent successfully.")
print(f"Weather: {temp_f}F, {description}")
print(f"Scenario: {scenario}")
print(f"Lunch: {lunch}")



