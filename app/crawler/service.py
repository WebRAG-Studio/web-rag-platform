from __future__ import annotations

import hashlib
import re
import threading
import time
import urllib.error
import urllib.request
import urllib.robotparser
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup

from app.core.security import canonicalize_url, validate_public_url, validate_redirect
from app.core.settings import settings
from app.core.storage import SiteStore, atomic_write_json, read_json
from app.ingestion.documents import (
    extract_docx,
    extract_pdf,
    extract_plain_text,
    sha256_bytes,
    validate_pdf,
)
from app.retrieval.engine import build_index


class CrawlManager:
    def __init__(self, store: SiteStore) -> None:
        self.store = store
        self._threads: dict[str, threading.Thread] = {}
        self._stop: dict[str, threading.Event] = {}
        self._lock = threading.RLock()

    def start(self, site_id: str) -> None:
        with self._lock:
            if site_id in self._threads and self._threads[site_id].is_alive():
                return
            event = threading.Event()
            worker = threading.Thread(target=self._crawl, args=(site_id, event), daemon=True)
            self._stop[site_id] = event
            self._threads[site_id] = worker
            worker.start()

    def stop(self, site_id: str) -> None:
        self._stop.setdefault(site_id, threading.Event()).set()

    def _fetch(self, url: str, max_bytes: int) -> tuple[bytes, str, dict]:
        validate_public_url(url)
        request = urllib.request.Request(url, headers={"User-Agent": "SiteMind/0.1 (+self-hosted crawler)"})
        class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                safe_url = validate_redirect(req.full_url, newurl)
                return super().redirect_request(req, fp, code, msg, headers, safe_url)

        opener = urllib.request.build_opener(SafeRedirectHandler)
        last_error = None
        for attempt in range(3):
            try:
                with opener.open(request, timeout=20) as response:
                    final_url = response.geturl()
                    validate_public_url(final_url)
                    content = response.read(max_bytes + 1)
                    if len(content) > max_bytes:
                        raise ValueError("Response exceeded the configured size limit")
                    return content, final_url, dict(response.headers)
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                last_error = error
                if attempt < 2:
                    time.sleep(0.5 * (2 ** attempt))
        raise last_error or RuntimeError("Request failed")

    def _crawl(self, site_id: str, stop: threading.Event) -> None:
        site_path = self.store.site_path(site_id)
        config = self.store.config(site_id).model_dump()
        progress_path = site_path / "crawl_progress.json"
        pages_path = site_path / "pages.json"
        documents_path = site_path / "documents.json"
        documents_dir = site_path / "documents"
        progress = {
            "status": "running",
            "stage": "Validating website",
            "discovered": 1,
            "processed": 0,
            "successes": 0,
            "skipped": 0,
            "failed": 0,
            "percentage": 0,
            "current_url": config["website_url"],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": 0,
            "rate_per_second": 0,
            "eta_seconds": None,
        }
        started = time.monotonic()
        atomic_write_json(progress_path, progress)
        queue = deque([(config["website_url"], 0)])
        seen: set[str] = set()
        pages: list[dict] = read_json(pages_path, [])
        documents: list[dict] = read_json(documents_path, [])
        page_by_url = {item.get("url"): item for item in pages}
        doc_by_url: dict[str, dict] = {}
        for item in documents:
            url = item.get("url")
            if not url:
                continue
            base = {key: value for key, value in item.items() if key not in {
                "page", "text", "text_quality", "ocr_confidence", "extraction_method"
            }}
            document = doc_by_url.setdefault(url, {**base, "pages": []})
            document["pages"].append({
                key: item.get(key)
                for key in ("page", "text", "text_quality", "ocr_confidence", "extraction_method")
                if item.get(key) is not None
            })
        domain = urlsplit(config["website_url"]).hostname
        robot = urllib.robotparser.RobotFileParser(urljoin(config["website_url"], "/robots.txt"))
        progress["stage"] = "Reading robots.txt"
        atomic_write_json(progress_path, progress)
        if config.get("respect_robots_txt", True):
            try:
                robot.read()
            except Exception:
                pass

        while queue and len(seen) < config["max_pages"] and not stop.is_set():
            raw_url, depth = queue.popleft()
            url = canonicalize_url(raw_url)
            if url in seen or depth > config["max_depth"]:
                continue
            if re.search(r"/(?:login|logout|admin|cart|checkout|search|calendar|session)(?:/|$)", urlsplit(url).path, re.I):
                progress["skipped"] += 1
                continue
            if any(urlsplit(url).path.startswith(path) for path in config.get("excluded_paths", [])):
                progress["skipped"] += 1
                continue
            seen.add(url)
            progress["current_url"] = url
            try:
                if config.get("respect_robots_txt", True) and not robot.can_fetch("SiteMind", url):
                    progress["skipped"] += 1
                    continue
                progress["stage"] = "Crawling webpages"
                content, final_url, headers = self._fetch(url, settings.max_document_mb * 1024 * 1024)
                if urlsplit(final_url).hostname != domain:
                    raise PermissionError("Cross-domain redirects are not crawled")
                content_type = headers.get("Content-Type", "").lower()
                suffix = Path(urlsplit(final_url).path).suffix.lower()
                if ("pdf" in content_type or suffix == ".pdf") and config.get("include_pdf", True):
                    progress["stage"] = "Extracting text"
                    atomic_write_json(progress_path, progress)
                    validate_pdf(content, settings.max_document_mb * 1024 * 1024)
                    name = hashlib.sha256(final_url.encode()).hexdigest()[:16] + ".pdf"
                    destination = documents_dir / name
                    digest = sha256_bytes(content)
                    if not destination.exists() or sha256_bytes(destination.read_bytes()) != digest:
                        temporary = destination.with_suffix(".part")
                        temporary.write_bytes(content)
                        temporary.replace(destination)
                    page_records = extract_pdf(
                        destination,
                        enable_ocr=config.get("enable_ocr", True),
                        languages=config.get("languages", ["en"]),
                    )
                    if any(page.get("extraction_method") == "ocr" for page in page_records):
                        progress["stage"] = "Running OCR"
                    title = unquote(urlsplit(final_url).path.rsplit("/", 1)[-1]) or name
                    doc_by_url[final_url] = {
                        "type": "pdf",
                        "title": title,
                        "filename": name,
                        "url": final_url,
                        "sha256": digest,
                        "etag": headers.get("ETag"),
                        "last_modified": headers.get("Last-Modified"),
                        "pages": page_records,
                    }
                elif suffix == ".txt" and config.get("include_txt", True):
                    doc_by_url[final_url] = {
                        "type": "txt",
                        "title": unquote(Path(urlsplit(final_url).path).name),
                        "filename": unquote(Path(urlsplit(final_url).path).name),
                        "url": final_url,
                        "sha256": sha256_bytes(content),
                        "pages": [{"page": None, "text": extract_plain_text(content), "text_quality": 1.0}],
                    }
                elif suffix == ".docx" and config.get("include_docx", False):
                    doc_by_url[final_url] = {
                        "type": "docx",
                        "title": unquote(Path(urlsplit(final_url).path).name),
                        "filename": unquote(Path(urlsplit(final_url).path).name),
                        "url": final_url,
                        "sha256": sha256_bytes(content),
                        "pages": [{"page": None, "text": extract_docx(content), "text_quality": 1.0}],
                    }
                elif not config.get("include_html", True):
                    continue
                else:
                    soup = BeautifulSoup(content, "html.parser")
                    for element in soup(["script", "style", "nav", "footer", "noscript"]):
                        element.decompose()
                    title = soup.title.get_text(" ", strip=True) if soup.title else final_url
                    text = soup.get_text("\n", strip=True)
                    page_by_url[final_url] = {"type": "webpage", "title": title, "url": final_url, "text": text}
                    if depth < config["max_depth"]:
                        for link in soup.select("a[href]"):
                            candidate = canonicalize_url(urljoin(final_url, link.get("href", "")))
                            if urlsplit(candidate).hostname == domain and candidate not in seen:
                                queue.append((candidate, depth + 1))
                progress["processed"] += 1
                progress["successes"] += 1
            except Exception as error:
                progress["failed"] += 1
                progress.setdefault("errors", []).append({"url": url, "error": type(error).__name__})
                progress["errors"] = progress["errors"][-25:]
            progress["discovered"] = len(seen) + len(queue)
            elapsed = max(0.001, time.monotonic() - started)
            completed = progress["successes"] + progress["failed"] + progress["skipped"]
            total = max(1, min(config["max_pages"], progress["discovered"]))
            rate = completed / elapsed
            progress["percentage"] = round(
                min(99, completed / total * 100),
                1,
            )
            progress["elapsed_seconds"] = round(elapsed, 1)
            progress["rate_per_second"] = round(rate, 2)
            progress["eta_seconds"] = round(max(0, total - completed) / rate, 1) if rate else None
            progress["updated_at"] = datetime.now(timezone.utc).isoformat()
            atomic_write_json(progress_path, progress)
            atomic_write_json(pages_path, list(page_by_url.values()))
            flattened = []
            for document in doc_by_url.values():
                base = {key: value for key, value in document.items() if key != "pages"}
                for page in document.get("pages", []):
                    flattened.append({**base, **page})
            atomic_write_json(documents_path, flattened)
            time.sleep(0.1)

        progress["status"] = "stopped" if stop.is_set() else "indexing"
        progress["stage"] = "Stopped" if stop.is_set() else "Building index"
        atomic_write_json(progress_path, progress)
        if not stop.is_set():
            build_index(site_path)
            progress["status"] = "complete"
            progress["stage"] = "Ready"
            progress["percentage"] = 100
            progress["current_url"] = None
            progress["completed_at"] = datetime.now(timezone.utc).isoformat()
            progress["updated_at"] = progress["completed_at"]
            progress["eta_seconds"] = 0
            atomic_write_json(progress_path, progress)


crawl_manager: CrawlManager | None = None
