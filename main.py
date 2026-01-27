import os
import requests
import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# =========================
# ENV / SETTINGS
# =========================
CITY = os.getenv("CITY", "Irvine,US")
OPENWEATHER_API_KEY = os.environ["OPENWEATHER_API_KEY"]

EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_TO_RAW = os.environ["EMAIL_TO"]  # comma-separated emails
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]

SIGNATURE_NAME = os.getenv("SIGNATURE_NAME", "Milan")

# Weekend override for testing
FORCE_SEND = os.getenv("FORCE_SEND", "false").lower() == "true"

LOCAL_TZ = ZoneInfo("America/Los_Angeles")
now_la = datetime.now(LOCAL_TZ)
formatted_date = now_la.strftime("%A, %B %d, %Y")



# =========================
# HELPERS
# =========================
def parse_recipients(raw):
    return [e.strip() for e in raw.split(",") if e.strip()]


def is_weekday_local():
    return datetime.now(LOCAL_TZ).weekday() < 5


def get_current_weather():
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": CITY, "appid": OPENWEATHER_API_KEY, "units": "imperial"}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    temp = round(data["main"]["temp"])
    desc = data["weather"][0]["description"].lower()
    return temp, desc


def get_noon_forecast():
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"q": CITY, "appid": OPENWEATHER_API_KEY, "units": "imperial"}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    tz_offset = data["city"]["timezone"]
    city_tz = timezone(timedelta(seconds=tz_offset))

    now_local = datetime.now(timezone.utc).astimezone(city_tz)
    target = now_local.replace(hour=12, minute=0, second=0, microsecond=0)

    if now_local > target:
        target += timedelta(days=1)

    best = min(
        data["list"],
        key=lambda item: abs(
            datetime.fromtimestamp(item["dt"], timezone.utc)
            .astimezone(city_tz)
            - target
        ),
    )

    temp = round(best["main"]["temp"])
    desc = best["weather"][0]["description"].lower()
    forecast_time = datetime.fromtimestamp(best["dt"], timezone.utc).astimezone(city_tz)

    return temp, desc, forecast_time


def choose_lunch(temp, desc):
    # Temp bucket
    if temp < 60:
        temp_bucket = "Cool"
    elif temp < 75:
        temp_bucket = "Mild"
    else:
        temp_bucket = "Warm"

    # Sky bucket
    if any(w in desc for w in ["rain", "drizzle", "shower", "thunderstorm"]):
        sky = "Rain"
    elif any(w in desc for w in ["mist", "fog", "haze", "overcast"]):
        sky = "Marine"
    else:
        sky = "Clear"

    # YOUR rules
    if temp_bucket == "Mild" and sky == "Clear":
        return "Bean and cheese burrito"
    if temp_bucket == "Warm" and sky == "Clear":
        return "Hummus sandwich"
    if temp_bucket == "Cool":
        return "Quesadilla"
    if temp_bucket == "Mild" and sky == "Marine":
        return "Pasta"
    if temp_bucket == "Mild" and sky == "Rain":
        return "Surprise me"

    return "Surprise me"


# =========================
# MAIN
# =========================
def main():
    recipients = parse_recipients(EMAIL_TO_RAW)
    if not recipients:
        raise RuntimeError("EMAIL_TO must contain at least one email.")

    if not FORCE_SEND and not is_weekday_local():
        print("Weekend detected — skipping email.")
        return

    # Morning weather (for email display)
    temp_f, desc = get_current_weather()

    # Noon weather (for lunch logic)
    noon_temp, noon_desc, noon_time = get_noon_forecast()
    lunch = choose_lunch(noon_temp, noon_desc)

    subject = f"Today’s Weather & Lunch - {formatted_date}"

    body = (
        f"Hi, mommy\n\n"
        f"Here’s today’s quick update:\n\n"
        f"Weather in {CITY}: {temp_f}°F, {desc}\n"
        f"Lunch idea: {lunch}\n\n"
        f"Have a great day.\n\n"
        f"– {SIGNATURE_NAME}\n"
    )

    msg = EmailMessage()
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(EMAIL_FROM, GMAIL_APP_PASSWORD)
        server.send_message(msg)

    print("Email sent successfully.")
    print(f"Morning weather: {temp_f}F, {desc}")
    print(f"Noon forecast: {noon_temp}F, {noon_desc} @ {noon_time}")
    print(f"Lunch: {lunch}")
    print(f"Sent to: {', '.join(recipients)}")


if __name__ == "__main__":
    main()



