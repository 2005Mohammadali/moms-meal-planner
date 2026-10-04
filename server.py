import os
import json
import time
import datetime
import urllib.parse
import urllib.request
from collections import defaultdict, deque

from flask import Flask, jsonify, request, send_from_directory

PROVIDER = os.getenv("PROVIDER", "ollama").lower()
OFFLINE = os.getenv("OFFLINE", "0") == "1"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_KEY = os.getenv("GROQ_API_KEY", "")
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_HOUR", "10"))

app = Flask(__name__, static_folder=None)  # only "/" and the API are public, not the whole folder
hits = defaultdict(deque)


# ---------- helpers ----------
def get_json(url, timeout=4):
    req = urllib.request.Request(url, headers={"User-Agent": "TomorrowsTadka/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def current_season(month):  # Indian seasons
    if month in (6, 7, 8, 9):
        return "Monsoon"
    if month == 10:
        return "Post-monsoon"
    if month in (11, 12, 1, 2):
        return "Winter"
    return "Summer"


def weather_text(code):
    if code == 0:
        return "Clear sky"
    if code in (1, 2, 3):
        return "Partly cloudy"
    if code in (45, 48):
        return "Foggy"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "Rainy"
    if code in (71, 73, 75, 77, 85, 86):
        return "Snowy"
    if code in (95, 96, 99):
        return "Thunderstorm"
    return "Pleasant"


def too_many_requests():
    ip = (request.headers.get("X-Forwarded-For", request.remote_addr) or "").split(",")[0].strip()
    now = time.time()
    q = hits[ip]
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        return True
    q.append(now)
    return False


# ---------- routes ----------
@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/api/context")
def context():
    """Season + provider info always. City/weather only when the user gives a city or coordinates."""
    ctx = {
        "provider": PROVIDER,
        "season": current_season(datetime.date.today().month),
        "city": "",
        "weather": "",
    }
    if OFFLINE:
        return jsonify(ctx)

    city = request.args.get("city", "").strip()
    lat, lon = request.args.get("lat"), request.args.get("lon")
    try:
        if city and not lat:
            geo = get_json(
                "https://geocoding-api.open-meteo.com/v1/search?count=1&name=" + urllib.parse.quote(city)
            )
            if not geo.get("results"):
                ctx["error"] = "Could not find that city."
                return jsonify(ctx)
            g = geo["results"][0]
            lat, lon = g["latitude"], g["longitude"]
            ctx["city"] = ", ".join(x for x in (g.get("name"), g.get("country")) if x)
        elif lat and lon:
            ctx["city"] = "Your location"
        if lat and lon:
            w = get_json(
                f"https://api.open-meteo.com/v1/forecast?latitude={float(lat)}&longitude={float(lon)}"
                "&current=temperature_2m,weather_code"
            )["current"]
            ctx["weather"] = f"{weather_text(w['weather_code'])}, {round(w['temperature_2m'])}°C"
    except Exception:
        ctx["error"] = "Weather lookup failed. You can still get recipes."
    return jsonify(ctx)


def build_prompt(d):
    common = f"""Dietary preference: {d.get('diet', 'None')}
Meal type: {d.get('meal', 'Any')}
Cuisine: {d.get('cuisine', 'Home style')}
Spice level: {d.get('spice', 'Medium')}
Maximum cooking time: {d.get('time', '30')} minutes
Servings: {d.get('servings', '2')}
Extra notes: {d.get('notes') or 'none'}"""

    if d.get("mode") == "leftover":
        intro = f"""You are a warm, practical home-cooking chef. Create recipes that use mostly these
leftover/available ingredients: {d.get('ingredients', '')}.
You may assume basic pantry items (oil, salt, spices, water)."""
    else:
        intro = f"""You are a warm, practical home-cooking chef. Surprise the cook with comforting
recipes for tomorrow that suit the place and weather.
Location: {d.get('city') or 'not given'}
Weather today: {d.get('weather') or 'not given'}
Season: {d.get('season', '')}
Use vegetables that are in season there and common pantry staples."""

    return f"""{intro}

{common}

Give exactly 2 different recipes. Reply with ONLY valid JSON in this shape:
{{"recipes": [
  {{"name": "recipe name", "emoji": "one emoji", "vibe": "one short appetizing sentence",
    "time": "e.g. 25 min", "servings": "e.g. 2",
    "ingredients": ["1 cup rice", "..."],
    "steps": ["step 1 text", "step 2 text"]}}
]}}"""


def call_llm(prompt):
    if PROVIDER == "groq":
        if not GROQ_KEY:
            raise RuntimeError("GROQ_API_KEY is not set on the server.")
        body = json.dumps({
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "max_tokens": 1500,
            "temperature": 0.8,
        }).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {GROQ_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read().decode())["choices"][0]["message"]["content"]

    import ollama  # imported lazily so the hosted deploy doesn't need it
    resp = ollama.chat(model=OLLAMA_MODEL, messages=[{"role": "user", "content": prompt}], format="json")
    return resp["message"]["content"]


@app.route("/api/recipes", methods=["POST"])
def recipes():
    data = request.get_json(force=True, silent=True) or {}
    if data.get("mode") == "leftover" and not data.get("ingredients", "").strip():
        return jsonify({"error": "Please list at least one ingredient."}), 400
    if PROVIDER == "groq" and too_many_requests():
        return jsonify({"error": "You have used your recipe quota for this hour. Please come back a little later."}), 429
    try:
        parsed = json.loads(call_llm(build_prompt(data)))
        items = parsed.get("recipes", [])
        if not items:
            raise ValueError("no recipes returned")
        return jsonify({"recipes": items[:2]})
    except json.JSONDecodeError:
        return jsonify({"error": "The chef scribbled something unreadable. Please try again."}), 502
    except Exception as e:
        hint = "Is Ollama running?" if PROVIDER == "ollama" else "The AI service is busy or its free quota is used up."
        return jsonify({"error": f"Could not reach the kitchen. {hint} ({type(e).__name__})"}), 500


if __name__ == "__main__":
    # Local use. On Render, gunicorn starts the app instead (see requirements.txt / start command).
    app.run(port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
