# SiteMind

**Turn websites into intelligent, source-grounded assistants.**

SiteMind is a self-hosted RAG platform developed by **WebRAG Studio**. Add a public website, crawl its pages and documents into an isolated local index, and ask questions with citations built from verified source metadata.

Repository description: **Turn public websites and documents into multilingual, citation-grounded AI assistants with crawling, OCR, semantic search, voice support and live indexing progress.**

## What it does

- Per-site onboarding, crawl limits, robots.txt support, stop/resume, and progress
- HTML and PDF ingestion with optional OCR for low-text pages
- Exact document lookup plus lexical and semantic retrieval
- Source-grounded answers through Gemini, Ollama, or a safe local fallback
- Isolated storage and indexes for every website
- Responsive dashboard and browser voice capability
- SSRF protection, redirect validation, input limits, and safe deletion confirmation

## Quick start

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

SiteMind does not crawl anything until you add a site through the UI or API.

## Architecture overview

The FastAPI control plane creates an isolated workspace for each site. A conservative background crawler discovers same-domain content, the ingestion layer extracts page-level text, and retrieval combines exact, lexical, and vector matching. The generation layer receives only selected evidence; citations are assembled separately from local metadata.

## Screenshots

> Screenshot placeholder: website onboarding

> Screenshot placeholder: crawl progress dashboard

> Screenshot placeholder: cited chat answer

## System requirements

- Python 3.11 or newer
- Approximately 1 GB of free disk space plus room for sites you choose to index
- Network access to the public site being crawled
- Optional: Tesseract for OCR, Ollama for local generation, or a Gemini API key

Large sites and OCR workloads require more memory, CPU time, and storage.

## Configuration

Environment variables are documented in [.env.example](.env.example). Gemini is optional. Ollama is local and optional. If neither provider is available, SiteMind returns a conservative extractive answer or an insufficiency message.

Local transformer embeddings are opt-in with `ENABLE_LOCAL_EMBEDDINGS=true`. The default deterministic embedding keeps the demo offline and avoids unannounced model downloads.

## Data layout

Runtime data is ignored by Git and stored under:

```text
data/sites/<site-id>/
  config.json
  pages.json
  documents.json
  documents/
  index/
  state/
```

No site can read another site's index through the API.

## Development

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

See [Architecture](docs/architecture.md), [Setup](docs/setup.md), [Deployment](docs/deployment.md), and [Contributing](CONTRIBUTING.md).

## Create and monitor an assistant

Open the SiteMind dashboard and choose **Create Website Assistant**. Provide the website name, public URL, assistant name, crawl mode, page limit, content types, languages, optional logo, and accent color. The request returns immediately while a local background job crawls and indexes content.

Use the site's **Progress** view or `GET /api/sites/<site-id>/progress` to monitor the current stage, completed and discovered counts, elapsed time, rate, ETA, skipped items, and failures. Percentage is shown only when the backend has a genuine discovered total.

Open **Chat** when content is indexed. Citations show verified titles, PDF pages, supporting highlights, and local document links. **Settings** changes local branding and languages. **Delete Site Data** requires typing the exact site ID before the isolated workspace is removed.

The command-line equivalent is:

```powershell
.\.venv\Scripts\python.exe scripts\crawl_site.py "Documentation" https://docs.example.org --max-pages 100
```

Use stop, resume, and recrawl controls carefully. Recrawls reuse the same isolated site workspace.

## Exact-document retrieval

Questions containing an exact PDF URL or filename are restricted to that document. If the document is absent, SiteMind returns no semantically similar substitute. Page citations and local document links are derived from verified index metadata.

## Embedding the widget

After creating a site, add the widget to a page served from the same origin:

```html
<script src="/widget.js" data-site-id="your-site-id"></script>
```

The widget validates `site_id`, loads that site's assistant name and accent color, and sends relative, site-scoped chat and reset requests. For cross-origin hosting, configure a deliberate CORS allowlist and authentication before deployment.

## Repository structure

```text
app/        API, crawler, ingestion, retrieval, generation, voice, security
frontend/   setup dashboard, chat UI, embeddable widget
scripts/    crawl, index, and audit commands
tests/      synthetic unit and integration tests
docs/       architecture, setup, deployment, and case study
```

## Limitations and security

- JavaScript-only pages may require a browser renderer, which is not included.
- Authentication-protected content is not supported by default.
- OCR quality varies by scan and installed language data.
- Website owners may block crawling or impose terms that prohibit reuse.
- In-process crawl jobs are intended for a local v1 deployment.
- High-stakes answers must be verified against original sources.

See [Security](SECURITY.md) and [Deployment](docs/deployment.md) before exposing SiteMind beyond a trusted local network.

## Roadmap

- Durable background queue and multi-worker deployments
- Browser rendering for approved JavaScript applications
- Pluggable rerankers and vector stores
- Richer multilingual speech adapters
- Authentication and role-based site access

## Acknowledgements

SiteMind builds on FastAPI, Beautiful Soup, NumPy, pypdf, and the wider open-source Python ecosystem. Contributors are acknowledged through the repository history and contribution guidelines.

## Responsible crawling

Only crawl sites you are authorized to access. Keep robots.txt enabled, use conservative limits, and review a site's terms and applicable law. SiteMind blocks private and local network targets to reduce SSRF risk.

## License

SiteMind is licensed under the [MIT License](LICENSE).
## Independent-project disclaimer

SiteMind is an independent open-source/portfolio project. It is not affiliated with, endorsed by, or operated by any website or institution used in examples. Users are responsible for having permission to crawl, store, index and reuse website content and for complying with applicable terms, robots policies, copyright rules and laws.


