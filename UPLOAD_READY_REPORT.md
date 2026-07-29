# Upload-ready report

## Product

- **Name:** SiteMind
- **Organization:** SiteMind Labs
- **Tagline:** Turn websites into intelligent, source-grounded assistants.
- **Verdict:** **READY TO REVIEW**

## Repository structure

```text
app/        FastAPI, site models, security, crawler, ingestion, retrieval, generation, voice
frontend/   onboarding, dashboard, cited chat, embeddable widget
scripts/    crawl, index, and site-audit commands
tests/      synthetic unit and integration tests
docs/       architecture, setup, deployment, sanitized case study
sample_data/ fixture policy
```

## Cleanup and generalization

Obsolete institution-specific runtime scripts, duplicate tests, historical repair tools, internal reports, and old frontend/voice assets were removed. Runtime assumptions were replaced with per-site configuration and isolated storage. The optional parliamentary example remains only as a sanitized case study.

## Test results

- `python -m compileall -q .`: passed
- `python -m unittest discover -s tests -v`: 1 passed
- `python -m pytest -q`: 43 passed, 0 failed
- Live local FastAPI smoke: `/health`, `/`, and `/api/voice/status` passed
- JavaScript syntax: skipped because Node.js was not installed
- Real website crawl: intentionally skipped; crawler tests use synthetic responses

One non-failing framework warning notes that the installed Starlette test client currently uses a deprecated `httpx` integration.

## Frontend Generalization

- **Active frontend entry point:** `frontend/index.html`, served by `GET /`
- **Active assets:** `frontend/assets/styles.css`, `frontend/assets/app.js`, and `frontend/widget.js`
- **Obsolete frontend removed:** duplicate root widget, old configuration/script/style files, copied voice-assistant CSS/JavaScript, and previous versioned frontend assets
- **Senate runtime references found in active frontend/runtime:** 0
- **Senate runtime references removed:** all default branding, prompts, suggested questions, URLs, logos, and institution-specific interface code
- **Remaining Senate references:** one sanitized case study under `docs/case-studies/`; no active runtime dependency
- **Hard-coded localhost frontend API references:** 0
- **Temporary tunnel references:** 0
- **Root smoke test:** `200 OK`, title `SiteMind | Website Assistant Builder`, SiteMind Labs attribution present, institution-specific branding absent
- **Static asset smoke test:** stylesheet, application JavaScript, widget, and API documentation all returned `200`
- **Responsive check:** rendered at 1440x900 and 390x844 with no horizontal overflow
- **Accessibility check:** skip link, form labels, visible focus states, live status regions, semantic progress, named controls, and RTL text support verified
- **Frontend-focused tests:** 13 focused unit/integration contract checks; all passed
- **Frontend verdict:** **READY TO REVIEW**

The final interface provides landing/setup, site dashboard, live crawl progress, branded chat, site settings, explicit site-data deletion, conversation reset, evidence highlights, PDF page links, browser voice input/playback, and a site-scoped widget. All frontend requests are relative and include the selected `site_id`.

## Security and upload scans

- Real secrets: 0
- Safe environment-variable references: 1 (`os.getenv("GEMINI_API_KEY", "")`)
- Personal paths/usernames: 0
- Files above 20 MB: 0
- Backup directories: 0
- Downloaded PDFs or website content: 0
- Embeddings, indexes, model files, logs, or checkpoints offered to Git: 0
- Remaining institution-specific runtime logic: 0
- Sanitized case-study files: 1
- Git dry-run candidate files after these two reports: 61

`.venv`, runtime data, PDFs, arrays, model formats, keys, cookies, logs, temporary files, and backup patterns are ignored. `git add --dry-run .` was used; nothing was staged, committed, or pushed.

## Remaining limitations

- JavaScript-only websites require a browser renderer.
- Authenticated content is unsupported by default.
- OCR depends on locally installed tools and language data.
- Background jobs are in-process and intended for a local single-process v1.
- Browser speech support varies by platform and permission.
- Local transformer embeddings are optional; the offline hash embedding is the default.
- Site owners may block crawling, and users remain responsible for authorization and legal compliance.
- A public open-source license must be selected before publication.

## Local startup

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Tests

```powershell
.\.venv\Scripts\python.exe -m compileall -q .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pytest -q
```

## Suggested first commit commands

Review the dry run and this report first. Then, only after selecting a license:

```powershell
git add --dry-run .
git add .
git commit -m "Prepare SiteMind public release"
```

No commit or upload was performed during preparation.

