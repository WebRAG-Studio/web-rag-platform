from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import app.api.routes as routes
from app.core.storage import SiteStore
from app.main import app


def test_health_and_site_lifecycle(tmp_path: Path):
    original_store = routes.store
    original_crawler = routes.crawler
    routes.store = SiteStore(tmp_path)

    class QuietCrawler:
        def start(self, site_id):
            return None

        def stop(self, site_id):
            return None

    routes.crawler = QuietCrawler()
    try:
        client = TestClient(app)
        assert client.get("/health").status_code == 200
        with patch("app.api.routes.validate_public_url", return_value=None):
            created = client.post("/api/sites", json={
                "site_name": "Example Docs",
                "website_url": "https://example.com/docs",
                "max_pages": 10,
            })
        assert created.status_code == 201
        site_id = created.json()["site_id"]
        assert client.get(f"/api/sites/{site_id}").status_code == 200
        progress = client.get(f"/api/sites/{site_id}/progress")
        assert progress.status_code == 200
        assert "pages_discovered" in progress.json()
        updated = client.patch(f"/api/sites/{site_id}", json={
            "assistant_name": "Example Guide",
            "languages": ["en", "ur"],
            "logo_url": None,
            "accent_color": "#125e5a",
        })
        assert updated.status_code == 200
        assert updated.json()["assistant_name"] == "Example Guide"
        assert client.get(f"/api/sites/{site_id}/documents").status_code == 200
        reset = client.post(
            f"/api/sites/{site_id}/conversation/reset",
            json={"session_id": "browser-session"},
        )
        assert reset.json() == {"reset": True}
        assert client.get("/api/sites").json()[0]["site_id"] == site_id
        wrong = client.request("DELETE", f"/api/sites/{site_id}", json={"confirm_site_id": "wrong"})
        assert wrong.status_code == 400
        deleted = client.request("DELETE", f"/api/sites/{site_id}", json={"confirm_site_id": site_id})
        assert deleted.json() == {"deleted": True}
    finally:
        routes.store = original_store
        routes.crawler = original_crawler


def test_root_and_all_active_static_assets_are_available():
    client = TestClient(app)
    root = client.get("/")
    assert root.status_code == 200
    assert "SiteMind Labs" in root.text
    assert "Senate of Pakistan" not in root.text
    assert "senate.gov.pk" not in root.text.lower()
    for path in ("/assets/styles.css", "/assets/app.js", "/widget.js"):
        response = client.get(path)
        assert response.status_code == 200, path


def test_normal_chat_never_exposes_debug_metadata(tmp_path: Path):
    original_store = routes.store
    routes.store = SiteStore(tmp_path)
    try:
        config = routes.store.create(
            routes.SiteCreate(site_name="Docs", website_url="https://example.com"),
            "https://example.com",
        )
        client = TestClient(app)
        response = client.post(
            f"/api/sites/{config.site_id}/chat",
            json={"question": "What is the policy?", "session_id": "one"},
        )
        assert set(response.json()) == {"answer", "sources"}
    finally:
        routes.store = original_store
