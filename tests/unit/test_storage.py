from pathlib import Path

import pytest

from app.core.storage import SiteStore
from app.models.site import SiteCreate


def request(name="Docs"):
    return SiteCreate(site_name=name, website_url="https://example.com")


def test_sites_are_isolated(tmp_path: Path):
    store = SiteStore(tmp_path)
    one = store.create(request("One"), "https://example.com")
    two = store.create(request("Two"), "https://example.org")
    assert store.site_path(one.site_id) != store.site_path(two.site_id)
    assert store.site_path(one.site_id).parent == tmp_path.resolve()


def test_path_traversal_is_rejected(tmp_path: Path):
    store = SiteStore(tmp_path)
    with pytest.raises(ValueError):
        store.site_path("../../outside")


def test_delete_requires_valid_site_path(tmp_path: Path):
    store = SiteStore(tmp_path)
    with pytest.raises(ValueError):
        store.delete("../bad")
