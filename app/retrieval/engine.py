from __future__ import annotations

import hashlib
import json
import math
import re
import threading
from pathlib import Path
from urllib.parse import unquote, urlsplit

import numpy as np

from app.core.settings import settings
from app.core.storage import atomic_write_json, read_json


NOT_FOUND = "I could not find enough reliable information in this website's indexed records."
_cache_lock = threading.RLock()
_index_cache: dict[str, tuple[float, list[dict], np.ndarray]] = {}
_model = None


def normalize_title(value: str) -> str:
    value = unquote(str(value or "")).lower()
    value = re.sub(r"https?://\S+", " ", value)
    value = value.replace("_", " ").replace("-", " ")
    value = re.sub(r"\.(pdf|txt|docx|html?)\b", " ", value)
    value = re.sub(r"[^a-z0-9\u0600-\u06ff]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9\u0600-\u06ff]{2,}", normalize_title(value))


class Embedder:
    def __init__(self) -> None:
        self.name = "sitemind-hash-embedding-v1"
        self.dimension = 384
        self._transformer = None
        if str(__import__("os").getenv("ENABLE_LOCAL_EMBEDDINGS", "")).lower() in {
            "1", "true", "yes", "on"
        }:
            try:
                from sentence_transformers import SentenceTransformer

                self._transformer = SentenceTransformer(
                    settings.embedding_model,
                    local_files_only=True,
                )
                self.name = settings.embedding_model
                self.dimension = int(self._transformer.get_sentence_embedding_dimension())
            except Exception:
                self._transformer = None

    def encode(self, values: list[str]) -> np.ndarray:
        if self._transformer is not None:
            return self._transformer.encode(
                values,
                convert_to_numpy=True,
                normalize_embeddings=True,
            ).astype(np.float32)
        matrix = np.zeros((len(values), self.dimension), dtype=np.float32)
        for row, value in enumerate(values):
            for token in _tokens(value):
                digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
                number = int.from_bytes(digest, "little")
                index = number % self.dimension
                matrix[row, index] += -1.0 if number & 1 else 1.0
            norm = float(np.linalg.norm(matrix[row]))
            if norm:
                matrix[row] /= norm
        return matrix


def get_embedder() -> Embedder:
    global _model
    if _model is None:
        with _cache_lock:
            if _model is None:
                _model = Embedder()
    return _model


def _paragraph_chunks(text: str, size: int = 1100, overlap: int = 160) -> list[str]:
    paragraphs = [
        re.sub(r"\s+", " ", paragraph).strip()
        for paragraph in re.split(r"\n\s*\n", text or "")
        if paragraph.strip()
    ]
    chunks = []
    buffer = ""
    for paragraph in paragraphs:
        if len(buffer) + len(paragraph) + 1 <= size:
            buffer = f"{buffer}\n{paragraph}".strip()
            continue
        if buffer:
            chunks.append(buffer)
        if len(paragraph) <= size:
            buffer = paragraph
            continue
        start = 0
        while start < len(paragraph):
            piece = paragraph[start:start + size].strip()
            if piece:
                chunks.append(piece)
            start += max(1, size - overlap)
        buffer = ""
    if buffer:
        chunks.append(buffer)
    return [chunk for chunk in chunks if len(chunk) >= 40]


def build_index(site_path: Path) -> dict:
    pages = read_json(site_path / "pages.json", [])
    documents = read_json(site_path / "documents.json", [])
    chunks: list[dict] = []
    for record in list(pages) + list(documents):
        text = str(record.get("text") or "").strip()
        if not text:
            continue
        for index, chunk_text in enumerate(_paragraph_chunks(text)):
            identity = "|".join((
                str(record.get("url") or ""),
                str(record.get("page") or ""),
                str(index),
                chunk_text,
            ))
            chunks.append({
                "chunk_id": hashlib.sha256(identity.encode("utf-8")).hexdigest(),
                "text": chunk_text,
                "title": record.get("title") or record.get("filename") or "Untitled",
                "url": record.get("url") or "",
                "type": record.get("type") or "webpage",
                "page": record.get("page"),
                "filename": record.get("filename"),
                "document_id": record.get("document_id"),
                "chunk_index": index,
                "text_quality": record.get("text_quality", 1.0),
                "ocr_confidence": record.get("ocr_confidence"),
            })
    embedder = get_embedder()
    vectors = embedder.encode([
        f"{chunk['title']} {chunk['text']}" for chunk in chunks
    ]) if chunks else np.zeros((0, embedder.dimension), dtype=np.float32)
    index_path = site_path / "index"
    index_path.mkdir(parents=True, exist_ok=True)
    atomic_write_json(index_path / "chunks.json", chunks)
    temporary = index_path / ".vectors.tmp.npy"
    np.save(temporary, vectors)
    temporary.replace(index_path / "vectors.npy")
    atomic_write_json(index_path / "manifest.json", {
        "embedding_model": embedder.name,
        "dimension": embedder.dimension,
        "chunk_count": len(chunks),
    })
    with _cache_lock:
        _index_cache.pop(str(site_path.resolve()), None)
    return {"chunks": len(chunks), "embedding_model": embedder.name}


def _load(site_path: Path) -> tuple[list[dict], np.ndarray]:
    chunks_path = site_path / "index" / "chunks.json"
    vectors_path = site_path / "index" / "vectors.npy"
    stamp = max(
        chunks_path.stat().st_mtime if chunks_path.exists() else 0,
        vectors_path.stat().st_mtime if vectors_path.exists() else 0,
    )
    key = str(site_path.resolve())
    with _cache_lock:
        cached = _index_cache.get(key)
        if cached and cached[0] == stamp:
            return cached[1], cached[2]
    chunks = read_json(chunks_path, [])
    vectors = (
        np.load(vectors_path, mmap_mode="r")
        if vectors_path.exists()
        else np.zeros((0, get_embedder().dimension), dtype=np.float32)
    )
    if len(chunks) != len(vectors):
        raise RuntimeError("The site's chunks and vectors are out of sync.")
    with _cache_lock:
        _index_cache[key] = (stamp, chunks, vectors)
    return chunks, vectors


def _exact_reference(question: str) -> str | None:
    url = re.search(r"https?://[^\s<>\"]+", question, flags=re.I)
    if url:
        path = unquote(urlsplit(url.group(0).rstrip(".,?")).path)
        if re.search(r"\.(pdf|txt|docx)$", path, flags=re.I):
            return url.group(0).rstrip(".,?")
    filename = re.search(r"([\w().-]+\.(?:pdf|txt|docx))\b", question, flags=re.I)
    if not filename:
        filename = re.search(
            r"""["']([^"']{1,180}\.(?:pdf|txt|docx))["']""",
            question,
            flags=re.I,
        )
    return filename.group(1).strip() if filename else None


def search(site_path: Path, question: str, limit: int = 6) -> dict:
    chunks, vectors = _load(site_path)
    exact = _exact_reference(question)
    if not exact:
        normalized_question = normalize_title(question)
        titles = {}
        for chunk in chunks:
            title = normalize_title(chunk.get("title", ""))
            if len(_tokens(title)) >= 2:
                titles.setdefault(title, chunk.get("title"))
        title_match = max(
            (title for title in titles if title and title in normalized_question),
            key=len,
            default=None,
        )
        if title_match:
            matched = [chunk for chunk in chunks if normalize_title(chunk.get("title", "")) == title_match]
            matched.sort(key=lambda item: (int(item.get("page") or 0), item.get("chunk_index", 0)))
            return {
                "results": [dict(item, score=1.0) for item in matched[:limit]],
                "exact_document": True,
                "exact_reference": titles[title_match],
            }
    if exact:
        reference_name = unquote(urlsplit(exact).path).rsplit("/", 1)[-1] if "://" in exact else exact
        normalized = normalize_title(reference_name)
        matched = [
            chunk for chunk in chunks
            if normalized and normalized in {
                normalize_title(chunk.get("filename", "")),
                normalize_title(unquote(urlsplit(chunk.get("url", "")).path).rsplit("/", 1)[-1]),
            }
        ]
        if not matched:
            return {"results": [], "exact_document": False, "exact_reference": exact}
        matched.sort(key=lambda item: (int(item.get("page") or 0), item.get("chunk_index", 0)))
        return {
            "results": [dict(item, score=1.0) for item in matched[:limit]],
            "exact_document": True,
            "exact_reference": exact,
        }
    if not chunks:
        return {"results": [], "exact_document": False, "exact_reference": None}
    query_vector = get_embedder().encode([question])[0]
    semantic = np.asarray(vectors @ query_vector, dtype=np.float32)
    query_tokens = set(_tokens(question))
    scored = []
    for index, chunk in enumerate(chunks):
        body_tokens = set(_tokens(f"{chunk.get('title', '')} {chunk.get('text', '')}"))
        lexical = len(query_tokens & body_tokens) / max(1, len(query_tokens))
        quality = float(chunk.get("text_quality") or 0.5)
        ocr_confidence = chunk.get("ocr_confidence")
        if ocr_confidence is not None and float(ocr_confidence) < 45:
            quality *= 0.55
        score = float(semantic[index]) * 0.58 + lexical * 0.36 + min(1.0, quality) * 0.06
        scored.append((score, index))
    output = []
    seen = set()
    for score, index in sorted(scored, reverse=True):
        if score < 0.12:
            continue
        chunk = dict(chunks[index], score=round(score, 4))
        key = (chunk.get("url"), chunk.get("page"), chunk.get("chunk_index"))
        if key in seen:
            continue
        seen.add(key)
        output.append(chunk)
        if len(output) >= limit:
            break
    return {"results": output, "exact_document": False, "exact_reference": None}


def citations(results: list[dict], limit: int = 3) -> list[dict]:
    output = []
    seen = set()
    for result in results:
        key = (result.get("url"), result.get("page"))
        if key in seen:
            continue
        seen.add(key)
        source = {
            "title": result.get("title") or "Source",
            "url": result.get("url") or "",
            "type": result.get("type") or "webpage",
        }
        if result.get("page") is not None:
            source["page"] = result["page"]
        source["highlight"] = result.get("text", "")[:280].strip()
        output.append(source)
        if len(output) >= limit:
            break
    return output
