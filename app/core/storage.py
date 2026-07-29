from __future__ import annotations

import json
import os
import re
import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from app.models.site import SiteConfig, SiteCreate, SiteUpdate


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug[:42] or "site").strip("-")


def atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def read_json(path: Path, default: object) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return default


class SiteStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def site_path(self, site_id: str) -> Path:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,63}", site_id):
            raise ValueError("Invalid site identifier.")
        path = (self.root / site_id).resolve()
        if self.root not in path.parents:
            raise ValueError("Site path escapes the configured data root.")
        return path

    def create(self, request: SiteCreate, canonical_url: str) -> SiteConfig:
        with self._lock:
            site_id = f"{slugify(request.site_name)}-{uuid.uuid4().hex[:8]}"
            path = self.site_path(site_id)
            path.mkdir(parents=True)
            for child in ("documents", "state", "index"):
                (path / child).mkdir()
            now = utc_now()
            hostname = (urlsplit(canonical_url).hostname or "").lower()
            config = SiteConfig(
                **request.model_dump(exclude={"website_url"}),
                website_url=canonical_url,
                site_id=site_id,
                allowed_domains=[hostname],
                created_at=now,
                updated_at=now,
            )
            atomic_write_json(path / "config.json", config.model_dump())
            atomic_write_json(path / "pages.json", [])
            atomic_write_json(path / "documents.json", [])
            atomic_write_json(path / "index" / "chunks.json", [])
            atomic_write_json(path / "crawl_progress.json", {
                "status": "queued",
                "stage": "Queued",
                "completed": 0,
                "total": None,
                "percentage": None,
                "failures": 0,
                "started_at": None,
                "updated_at": now,
            })
            return config

    def config(self, site_id: str) -> SiteConfig:
        payload = read_json(self.site_path(site_id) / "config.json", None)
        if not isinstance(payload, dict):
            raise FileNotFoundError(site_id)
        return SiteConfig.model_validate(payload)

    def list_configs(self) -> list[SiteConfig]:
        output = []
        for path in sorted(self.root.glob("*/config.json")):
            try:
                output.append(SiteConfig.model_validate(read_json(path, {})))
            except (ValueError, TypeError):
                continue
        return output

    def delete(self, site_id: str) -> None:
        with self._lock:
            path = self.site_path(site_id)
            if path.exists():
                shutil.rmtree(path)

    def update(self, site_id: str, request: SiteUpdate) -> SiteConfig:
        with self._lock:
            current = self.config(site_id)
            payload = current.model_dump()
            payload.update(request.model_dump())
            payload["updated_at"] = utc_now()
            updated = SiteConfig.model_validate(payload)
            atomic_write_json(self.site_path(site_id) / "config.json", updated.model_dump())
            return updated
