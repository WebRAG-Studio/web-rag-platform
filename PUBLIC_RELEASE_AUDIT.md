# Public release audit

## Scope

This audit covers only the clean `web-rag-platform` repository. No original deployment directory or private dataset was modified.

## Removed categories

- Institution-specific RAG routing, prompts, structured lookup, crawler, and acceptance scripts
- Duplicate and superseded root test suites
- Historical repair utilities, internal audit reports, and generated audit output
- Old frontend, widget, and versioned voice assets
- Deployment-specific compatibility wrappers

The repository contained no downloaded data directory, PDFs, embeddings, vector indexes, model weights, logs, checkpoints, backup directories, or committed virtual environment.

## Generalization

- Replaced institution-specific runtime behavior with a validated `SiteConfig`
- Added isolated `data/sites/<site-id>` workspaces
- Scoped crawl, index, chat, exact-document retrieval, and conversation memory by site
- Added configurable Gemini, Ollama, embedding, OCR, crawl, and storage settings
- Preserved the former domain only as a sanitized architectural case study

## Safety

- Public HTTP(S)-only URL validation and DNS/IP checks
- Private, loopback, link-local, metadata, credential-bearing, and non-HTTP targets blocked
- Redirect targets revalidated before following
- Same-domain, page, depth, size, path, robots, timeout, retry, and deduplication controls
- Atomic state and document writes
- Exact document requests return no semantic substitute
- Provider-generated citations are not accepted

## Validation

- Python compile check: passed
- Standard-library smoke test: 1 passed
- Pytest synthetic suite: 43 passed
- Live local FastAPI health, homepage, and voice-status smoke test: passed
- Node.js syntax check: skipped because Node.js was unavailable
- External crawling: intentionally not performed

