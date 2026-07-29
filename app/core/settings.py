from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    project_root: Path
    data_root: Path
    generation_provider: str
    gemini_api_key: str
    gemini_model: str
    ollama_base_url: str
    ollama_model: str
    embedding_model: str
    reranker_model: str
    default_max_pages: int
    max_document_mb: int
    request_timeout: float
    enable_ocr: bool
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        project_root = Path(__file__).resolve().parents[2]
        configured_data = Path(os.getenv("DATA_DIR", "data/sites"))
        if not configured_data.is_absolute():
            configured_data = project_root / configured_data
        return cls(
            project_root=project_root,
            data_root=configured_data.resolve(),
            generation_provider=os.getenv("GENERATION_PROVIDER", "auto").strip().lower(),
            gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite").strip(),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b").strip(),
            embedding_model=os.getenv(
                "EMBEDDING_MODEL",
                "sentence-transformers/all-MiniLM-L6-v2",
            ).strip(),
            reranker_model=os.getenv("RERANKER_MODEL", "").strip(),
            default_max_pages=max(1, int(os.getenv("MAX_PAGES", "100"))),
            max_document_mb=max(1, int(os.getenv("MAX_DOCUMENT_MB", "25"))),
            request_timeout=max(5.0, float(os.getenv("REQUEST_TIMEOUT", "30"))),
            enable_ocr=_bool("ENABLE_OCR", True),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )


settings = Settings.from_env()
