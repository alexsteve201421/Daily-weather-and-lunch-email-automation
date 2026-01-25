import os
import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

# ---------------------------
# Settings (via GitHub Actions env/secrets)
# ---------------------------
CITY = os.getenv("CITY", "Irvine,US")
API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")

EMAIL_FROM = os.environ.get("EMAIL_FROM", "")
# Put multiple emails in EMAIL_TO separated by commas:
# e.g. "mom@gmail.com,dad@gmail.com,person3@gmail.com"
EMAIL_TO_RAW = os.environ.get("EMAIL_TO", "")

GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

# Optional: set to "1" to allow sending on weekends for testing
OVERRIDE_WEEKEND = os.getenv("OVERRIDE_WEEKEND", "0") == "1"

# Optional: customize signature name (defaults to "Milan" per your request)
SIGNATURE_NAME = os.getenv("SIGNATURE_NAME", "Milan")

# ---------------------------
# Helpers
# ---------------------------
def parse_recipients(raw: str) -> list[str]:
    """
    Accepts a comma-separated list of emails.
    Returns a cleaned list (no blanks).
    """
    return [e.strip() for e in raw.split(",") if e.strip()]


def is_weekday_local(tz_name: str = "America/Los_Angeles") -> bool:
    """
    Uses a real timezone so DST is handled automatically.
    Monday=0 ... Sunday=6
    """
    now_local = datetime.now(ZoneInfo(tz_name))
    return now_local.weekday() < 5


def get_current_weather(city: str, api_key: str) -> tuple[int, str]:
    """
    Returns (temp_f_rounded, description_lower).
    """
    if not api_key:
        raise RuntimeError("OPENWEATHER_API_KEY is missing.")

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": api_key, "units": "imperial"}

    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    temp_f = round(data["main"]["temp"])
    description = data["weather"][0]["description"].lower()
    return temp_f, description


def choose_lunch(temp_f: int, description: str) -> str:
    """
    Your fixed mapping (one option per combo).
    """
    desc = description.lower()

    # --- Sky bucket ---
    rain_words = ("rain", "drizzle", "thunder", "storm", "shower")
    if any(w in desc for w in rain_words):
        sky = "Rain"
    else:
        # Treat fog/mist/haze as marine layer-ish
        marine_words = ("mist", "fog", "haze")
        if any(w in desc for w in marine_words):
            sky = "Marine Layer"
        else:
            # Cloudiness bucket
            if "overcast" in desc or ("cloud" in desc and "broken" in desc):
                sky = "Overcast"
            elif "cloud" in desc:
                sky = "Partly Cloudy"
            else:
                sky = "Clear"

    # --- Temp bucket ---
    if temp_f < 60:
        temp_bucket = "Cool"
    elif temp_f < 75:
        temp_bucket = "Mild"
    else:
        temp_bucket = "Warm"

    # --- Map to lunch (your requested combos) ---
    # Mild + Clear/Partly Cloudy = bean and cheese burrito
    if temp_bucket == "Mild" and sky in ("Clear", "Partly Cloudy"):
        return "Bean and cheese burrito"

    # Warm + Clear/Sunny = hummus sandwich
    if temp_bucket == "Warm" and sky == "Clear":
        return "Hummus sandwich"

    # Cool + Clear/Cloudy = quesadilla
    if temp_bucket == "Cool" and sky in ("Clear", "Partly Cloudy", "Overcast"):
        return "Quesadilla"

    # Mild + Overcast/Marine Layer = pasta
    if temp_bucket == "Mild" and sky in ("Overcast", "Marine Layer"):
        return "Pasta"

    # Mild + Rain = surprise me
    if temp_bucket == "Mild" and sky == "Rain":
        return "Surprise me"

    # Fallbacks (in case Irvine does something weird)
    if sky == "Rain":
        return "Surprise me"
    if temp_bucket == "Warm":
        return "Hummus sandwich"
    if temp_bucket == "Cool":
        return "Quesadilla"
    return "Bean and cheese burrito"


def build_email(subject: str, body_text: str, sender: str, recipients: list[str]) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)  # multiple recipients
    msg["Subject"] = subject
    msg.set_content(body_text)
    return msg


def send_email_gmail(sender: str, app_password: str, msg: EmailMessage) -> None:
    if not sender or not app_password:
        raise RuntimeError("EMAIL_FROM or GMAIL_APP_PASSWORD missing.")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender, app_password)
        server.send_message(msg)


# ---------------------------
# Main
# ---------------------------
def main():
    recipients = parse_recipients(EMAIL_TO_RAW)
    if not recipients:
        raise RuntimeError("EMAIL_TO is missing or empty (use comma-separated emails).")

    # Weekday check (DST-safe)
    if not OVERRIDE_WEEKEND and not is_weekday_local("America/Los_Angeles"):
        print("Weekend detected (local). Skipping email.")
        return

    # Get current weather (at send time)
    temp_f, desc = get_current_weather(CITY, API_KEY)

    lunch = choose_lunch(temp_f, desc)

    # “Real email” style
    subject = "Today’s weather + lunch"
    body = (
        f"Hi,\n\n"
        f"Here’s today’s quick update:\n\n"
        f"Weather in {CITY}: {temp_f}°F, {desc}\n"
        f"Lunch idea: {lunch}\n\n"
        f"Have a great day.\n\n"
        f"– {SIGNATURE_NAME}\n"
        f"Milan\n"
    )

    msg = build_email(subject, body, EMAIL_FROM, recipients)
    send_email_gmail(EMAIL_FROM, GMAIL_APP_PASSWORD, msg)

    print("Email sent successfully.")
    print(f"Weather: {temp_f}F, {desc}")
    print(f"Lunch: {lunch}")
    print(f"Sent to: {', '.join(recipients)}")


if __name__ == "__main__":
    main()



