import threading
from pathlib import Path

from app.core.storage import SiteStore, read_json
from app.crawler.service import CrawlManager
from app.models.site import SiteCreate


class SyntheticCrawler(CrawlManager):
    def _fetch(self, url: str, max_bytes: int):
        pages = {
            "https://example.com/": b"<html><head><title>Home</title></head><body><main>Welcome to the documentation.</main><a href='/guide'>Guide</a></body></html>",
            "https://example.com/guide": b"<html><head><title>Guide</title></head><body><main>The product warranty lasts two years from the verified purchase date for registered customers.</main></body></html>",
        }
        return pages[url], url, {"Content-Type": "text/html"}


def test_synthetic_crawl_builds_isolated_index(tmp_path: Path):
    store = SiteStore(tmp_path)
    config = store.create(
        SiteCreate(
            site_name="Example",
            website_url="https://example.com/",
            max_pages=5,
            max_depth=2,
            respect_robots_txt=False,
        ),
        "https://example.com/",
    )
    manager = SyntheticCrawler(store)
    manager._crawl(config.site_id, threading.Event())
    site = store.site_path(config.site_id)
    progress = read_json(site / "crawl_progress.json", {})
    chunks = read_json(site / "index" / "chunks.json", [])
    assert progress["status"] == "complete"
    assert progress["percentage"] == 100
    assert {chunk["title"] for chunk in chunks} == {"Home", "Guide"}
