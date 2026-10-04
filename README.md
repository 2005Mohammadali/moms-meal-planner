# Tomorrow's Tadka

## Run privately on your computer (Ollama)
1. Install Ollama, then `ollama pull llama3.2:3b`
2. `pip install -r requirements.txt`
3. `python server.py` and open http://localhost:5000
For zero network calls at all: `OFFLINE=1 python server.py` (Windows PowerShell: `$env:OFFLINE=1; python server.py`)


