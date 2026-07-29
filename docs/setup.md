# Setup

## Windows

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Linux and macOS

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

OCR is optional. Install Tesseract and its desired language packs, then install `pytesseract`, `Pillow`, and `PyMuPDF`. SiteMind continues without OCR if these tools are unavailable.

For Gemini, set `GEMINI_API_KEY`. For local generation, install Ollama, pull the configured model, and leave `GENERATION_PROVIDER=auto`.

## Create an assistant

Open `http://127.0.0.1:8000`, select **Create Website Assistant**, and enter a public website URL plus conservative crawl limits. The example placeholders are never submitted automatically.

After creation:

1. Use **Progress** to monitor the real crawl and indexing stages.
2. Use **Chat** to ask grounded questions and inspect source highlights.
3. Use **Settings** to change the assistant name, languages, logo, or accent color.
4. Use **Delete Site Data** only when you intend to remove that site's isolated local workspace.

The frontend uses relative API paths, so the same build can be served behind an approved reverse proxy.
