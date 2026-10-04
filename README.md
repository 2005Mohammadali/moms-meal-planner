# Tomorrow's Tadka

# 🍳 Tomorrow's Tadka

*"The question we all ask every evening: What should I cook tomorrow?"*

Tomorrow's Tadka is a chef-inspired web application designed to help you make the most of what you have in your kitchen or align your meals with the current weather and season. Powered locally by Llama (via Ollama or Groq), it delivers practical, home-style recipes with a warm culinary interface.

## ✨ Key Features
- **🛒 Leftover Rescue Mode:** Input random fridge ingredients to instantly generate creative meals using basic pantry staples.
- **✨ Surprise Me Mode:** Automatically detects your location, live weather, and seasonal produce to suggest comforting, highly relatable local dishes.
- **🔒 Privacy-First:** Runs locally on your machine via Ollama, keeping your data private.
- **🎨 Chef-Inspired UI:** Features custom culinary typography, an interactive card layout, and smooth mode-switching transitions.

## 🛠️ Tech Stack
- **Frontend:** HTML5, CSS3, Vanilla JavaScript (Custom culinary design system)
- **Backend:** Python, Flask, Gunicorn
- **AI Integration:** Llama 3.2 / 3.1 via Ollama (local) or Groq API
- **APIs:** Open-Meteo (Geocoding & Weather forecasting)

## Run privately on your computer (Ollama)
1. Install Ollama, then `ollama pull llama3.2:3b`
2. `pip install -r requirements.txt`
3. `python server.py` and open http://localhost:5000
For zero network calls at all: `OFFLINE=1 python server.py` (Windows PowerShell: `$env:OFFLINE=1; python server.py`)


