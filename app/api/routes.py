from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.security import UnsafeUrlError, canonicalize_url, validate_public_url
from app.core.conversation import conversations
from app.core.settings import settings
from app.core.storage import SiteStore, read_json
from app.crawler.service import CrawlManager
from app.generation.providers import generate_answer
from app.models.site import ChatRequest, ConversationReset, DeleteSiteRequest, SiteCreate, SiteUpdate
from app.retrieval.engine import citations, search


router = APIRouter(prefix="/api")
store = SiteStore(settings.data_root)
crawler = CrawlManager(store)


def _site_path(site_id: str) -> Path:
    try:
        path = store.site_path(site_id)
    except ValueError as error:
        raise HTTPException(404, "Site not found") from error
    if not (path / "config.json").exists():
        raise HTTPException(404, "Site not found")
    return path


@router.post("/sites", status_code=201)
def create_site(request: SiteCreate) -> dict:
    try:
        url = canonicalize_url(request.website_url)
        validate_public_url(url)
        if request.logo_url:
            validate_public_url(request.logo_url)
    except UnsafeUrlError as error:
        raise HTTPException(400, str(error)) from error
    config = store.create(request, url)
    crawler.start(config.site_id)
    return config.model_dump()


@router.get("/sites")
def list_sites() -> list[dict]:
    output = []
    for config in store.list_configs():
        progress = read_json(store.site_path(config.site_id) / "crawl_progress.json", {})
        output.append({**config.model_dump(), "progress": progress})
    return output


@router.get("/sites/{site_id}")
def get_site(site_id: str) -> dict:
    path = _site_path(site_id)
    return {
        "config": store.config(site_id).model_dump(),
        "progress": read_json(path / "crawl_progress.json", {}),
        "manifest": read_json(path / "index" / "manifest.json", {}),
    }


@router.patch("/sites/{site_id}")
def update_site(site_id: str, request: SiteUpdate) -> dict:
    _site_path(site_id)
    try:
        if request.logo_url:
            validate_public_url(request.logo_url)
    except UnsafeUrlError as error:
        raise HTTPException(400, str(error)) from error
    return store.update(site_id, request).model_dump()


@router.get("/sites/{site_id}/progress")
def get_progress(site_id: str) -> dict:
    path = _site_path(site_id)
    progress = dict(read_json(path / "crawl_progress.json", {}))
    pages = read_json(path / "pages.json", [])
    documents = read_json(path / "documents.json", [])
    manifest = read_json(path / "index" / "manifest.json", {})
    unique_documents = {item.get("url") for item in documents if item.get("url")}
    progress.update({
        "pages_discovered": len(pages),
        "documents_discovered": len(unique_documents),
        "documents_processed": len(unique_documents),
        "ocr_pages": sum(item.get("extraction_method") == "ocr" for item in documents),
        "chunks_indexed": int(manifest.get("chunk_count") or 0),
    })
    return progress


@router.get("/sites/{site_id}/documents")
def list_documents(site_id: str) -> list[dict]:
    path = _site_path(site_id)
    output = []
    seen = set()
    for item in read_json(path / "documents.json", []):
        key = (item.get("url"), item.get("filename"))
        if key in seen:
            continue
        seen.add(key)
        output.append({
            "title": item.get("title") or item.get("filename") or "Document",
            "url": item.get("url") or "",
            "type": item.get("type") or "document",
            "filename": item.get("filename"),
        })
    return output


@router.post("/sites/{site_id}/stop")
def stop_crawl(site_id: str) -> dict:
    _site_path(site_id)
    crawler.stop(site_id)
    return {"status": "stopping"}


@router.post("/sites/{site_id}/resume")
@router.post("/sites/{site_id}/recrawl")
def resume_crawl(site_id: str) -> dict:
    _site_path(site_id)
    crawler.start(site_id)
    return {"status": "queued"}


@router.delete("/sites/{site_id}")
def delete_site(site_id: str, request: DeleteSiteRequest) -> dict:
    _site_path(site_id)
    if request.confirm_site_id != site_id:
        raise HTTPException(400, "Confirmation does not match the site identifier")
    crawler.stop(site_id)
    store.delete(site_id)
    return {"deleted": True}


@router.post("/sites/{site_id}/chat")
def chat(site_id: str, request: ChatRequest) -> dict:
    path = _site_path(site_id)
    resolved = conversations.resolve(site_id, request.session_id, request.question)
    retrieval = search(path, resolved, limit=6)
    evidence = retrieval["results"]
    if not evidence:
        return {
            "answer": "I could not find enough reliable information in this website's indexed records.",
            "sources": [],
        }
    generated = generate_answer(request.question, evidence)
    conversations.remember(site_id, request.session_id, request.question)
    return {"answer": generated.answer, "sources": _sources(site_id, evidence)}


@router.post("/sites/{site_id}/chat_debug")
def chat_debug(site_id: str, request: ChatRequest) -> dict:
    path = _site_path(site_id)
    resolved = conversations.resolve(site_id, request.session_id, request.question)
    retrieval = search(path, resolved, limit=8)
    generated = generate_answer(request.question, retrieval["results"])
    return {
        "question": request.question,
        "resolved_question": resolved,
        "retrieval": retrieval,
        "answer": generated.answer,
        "provider": generated.provider,
        "fallback_used": generated.fallback_used,
        "provider_attempts": generated.attempts,
        "sources": _sources(site_id, retrieval["results"]),
    }


def _sources(site_id: str, evidence: list[dict]) -> list[dict]:
    sources = citations(evidence)
    by_key = {
        (item.get("url"), item.get("page")): item
        for item in evidence
    }
    for source in sources:
        item = by_key.get((source.get("url"), source.get("page")), {})
        if item.get("filename"):
            source["local_url"] = f"/api/sites/{site_id}/documents/{item['filename']}"
    return sources


@router.get("/sites/{site_id}/documents/{filename}")
def document_file(site_id: str, filename: str) -> FileResponse:
    path = _site_path(site_id)
    if Path(filename).name != filename:
        raise HTTPException(404, "Document not found")
    known = {
        item.get("filename")
        for item in read_json(path / "documents.json", [])
    }
    document = (path / "documents" / filename).resolve()
    if filename not in known or path.resolve() not in document.parents or not document.is_file():
        raise HTTPException(404, "Document not found")
    return FileResponse(document, media_type="application/pdf", filename=filename)


@router.get("/sites/{site_id}/documents/{filename}/preview")
def document_preview(site_id: str, filename: str) -> FileResponse:
    return document_file(site_id, filename)


@router.delete("/sites/{site_id}/conversation/{session_id}")
def reset_conversation(site_id: str, session_id: str) -> dict:
    _site_path(site_id)
    conversations.clear(site_id, session_id)
    return {"reset": True}


@router.post("/sites/{site_id}/conversation/reset")
def reset_conversation_post(site_id: str, request: ConversationReset) -> dict:
    _site_path(site_id)
    conversations.clear(site_id, request.session_id)
    return {"reset": True}
