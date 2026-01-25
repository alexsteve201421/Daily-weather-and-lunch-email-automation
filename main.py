import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone

import requests


# ----------------------------
# Settings (from GitHub Secrets / Variables)
# ----------------------------
CITY = os.getenv("CITY", "Irvine,US")  # example: "Irvine,US"
API_KEY = os.environ["OPENWEATHER_API_KEY"]

EMAIL_FROM = os.environ["EMAIL_FROM"]          # your Gmail address
EMAIL_TO = os.environ["EMAIL_TO"]              # your mom's email
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]  # Gmail App Password (NOT your normal password)

SIGNATURE_NAME = os.getenv("SIGNATURE_NAME", "Milan")  # you wanted "Milan" at the bottom

# We want lunch weather around 12:05 local time in the CITY
LUNCH_LOCAL_HOUR = int(os.getenv("LUNCH_LOCAL_HOUR", "12"))
LUNCH_LOCAL_MINUTE = int(os.getenv("LUNCH_LOCAL_MINUTE", "5"))


# ----------------------------
# Helpers: weather -> scenario -> lunch
# ----------------------------
def temp_bucket_f(temp_f: float) -> str:
    # Adjust these if you want:
    # Cool < 60, Mild 60-74, Warm >= 75
    if temp_f < 60:
        return "Cool"
    elif temp_f < 75:
        return "Mild"
    else:
        return "Warm"


def sky_bucket(description: str) -> str:
    d = (description or "").lower()

    # rain-ish first
    rain_words = ["rain", "drizzle", "shower", "thunderstorm"]
    if any(w in d for w in rain_words):
        return "Rain"

    # "marine layer" / fog / mist often shows as mist/fog/haze
    marine_words = ["mist", "fog", "haze"]
    if any(w in d for w in marine_words):
        return "Overcast / Marine Layer"

    # cloudy-ish
    overcast_words = ["overcast", "broken clouds"]
    if any(w in d for w in overcast_words):
        return "Overcast / Marine Layer"

    # partly cloudy-ish
    partly_words = ["few clouds", "scattered clouds", "partly"]
    if any(w in d for w in partly_words):
        return "Clear / Partly Cloudy"

    # clear / sunny
    clear_words = ["clear sky", "clear", "sunny"]
    if any(w in d for w in clear_words):
        return "Clear / Partly Cloudy"

    # fallback
    return "Clear / Partly Cloudy"


def pick_lunch(temp_b: str, sky_b: str) -> str:
    """
    One lunch per scenario (your mapping).
    """
    # Your 5 combos:
    # Mild + Clear / Partly Cloudy = bean and cheese burrito
    # Warm + Clear / Sunny (we treat as Clear/Partly) = hummus sandwich
    # Cool + Clear / Cloudy (we treat cloud-ish as Clear/Partly or Marine Layer) = quesadilla
    # Mild + Overcast / Marine Layer = pasta
    # Mild + Rain = surprise me

    if temp_b == "Mild" and sky_b == "Clear / Partly Cloudy":
        return "Bean and cheese burrito"
    if temp_b == "Warm" and sky_b == "Clear / Partly Cloudy":
        return "Hummus sandwich"
    if temp_b == "Cool" and (sky_b in ["Clear / Partly Cloudy", "Overcast / Marine Layer"]):
        return "Quesadilla"
    if temp_b == "Mild" and sky_b == "Overcast / Marine Layer":
        return "Pasta"
    if temp_b == "Mild" and sky_b == "Rain":
        return "Surprise me"

    # Sensible fallback if something unexpected happens
    return "Surprise me"


# ----------------------------
# OpenWeather: get forecast closest to 12:05 local time
# ----------------------------
def get_forecast_near_lunchtime(city: str, api_key: str):
    """
    Uses 5-day / 3-hour forecast. Picks the forecast entry closest to 12:05 local time today.
    Returns: (temp_f, description, chosen_local_dt, city_tz_offset_seconds)
    """
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"q": city, "appid": api_key, "units": "imperial"}

    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    tz_offset = int(data["city"].get("timezone", 0))  # seconds offset from UTC
    tz = timezone(timedelta(seconds=tz_offset))

    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(tz)

    # Target lunchtime today in the city's local time
    target_local = now_local.replace(
        hour=LUNCH_LOCAL_HOUR,
        minute=LUNCH_LOCAL_MINUTE,
        second=0,
        microsecond=0,
    )

    # If it's already past lunchtime locally, target tomorrow's lunchtime
    if now_local > target_local:
        target_local = target_local + timedelta(days=1)

    # Forecast entries are in UTC timestamps (dt). We'll compare in local time.
    best_item = None
    best_diff = None
    best_local_dt = None

    for item in data.get("list", []):
        dt_utc = datetime.fromtimestamp(int(item["dt"]), tz=timezone.utc)
        dt_local = dt_utc.astimezone(tz)
        diff = abs((dt_local - target_local).total_seconds())

        if best_diff is None or diff < best_diff:
            best_diff = diff
            best_item = item
            best_local_dt = dt_local

    if not best_item:
        raise RuntimeError("No forecast data returned.")

    temp_f = float(best_item["main"]["temp"])
    description = str(best_item["weather"][0]["description"])

    return temp_f, description, best_local_dt, tz_offset


# ----------------------------
# Email sending (Gmail SMTP)
# ----------------------------
def send_email(subject: str, body: str):
    msg = EmailMessage()
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject
    msg.set_content(body)

    # Gmail SMTP (App Password required)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_FROM, GMAIL_APP_PASSWORD)
        smtp.send_message(msg)


# ----------------------------
# Main
# ----------------------------
def main():
    # (Extra safety) Only run on weekdays (Mon-Fri) in the city's local time
    # Your workflow is already weekdays, but this prevents accidental manual weekend sends.
    # Comment this out if you want weekend emails too.
    # We'll determine local weekday using the forecast city's timezone.
    try:
        temp_f, desc, forecast_local_dt, tz_offset = get_forecast_near_lunchtime(CITY, API_KEY)
        tz = timezone(timedelta(seconds=tz_offset))
        now_local = datetime.now(timezone.utc).astimezone(tz)

        if now_local.weekday() >= 5:
            print("Weekend detected (local). Skipping email.")
            return

        t_bucket = temp_bucket_f(temp_f)
        s_bucket = sky_bucket(desc)
        lunch = pick_lunch(t_bucket, s_bucket)

        # A real email-style message
        date_str = forecast_local_dt.strftime("%A, %B %d")
        time_str = forecast_local_dt.strftime("%-I:%M %p") if os.name != "nt" else forecast_local_dt.strftime("%I:%M %p").lstrip("0")

        subject = f"Lunch idea for {date_str}"
        body = (
            f"Hi Mom,\n\n"
            f"Here’s today’s lunch idea based on the forecast for {CITY} around {time_str}:\n\n"
            f"• Forecast: {round(temp_f)}°F, {desc}\n"
            f"• Lunch suggestion: {lunch}\n\n"
            f"Love,\n"
            f"{SIGNATURE_NAME}\n"
        )

        # Logs (shows in Actions)
        print(f"Forecast used: {CITY} @ {forecast_local_dt.isoformat()}")
        print(f"Weather: {round(temp_f)}°F, {desc}")
        print(f"Buckets: {t_bucket} + {s_bucket}")
        print(f"Lunch: {lunch}")

        send_email(subject, body)
        print("Email sent successfully.")

    except Exception as e:
        # Make failures obvious in Actions
        print(f"ERROR: {e}")
        raise


if __name__ == "__main__":
    main()



