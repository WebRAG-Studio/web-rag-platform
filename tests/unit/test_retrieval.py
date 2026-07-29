from pathlib import Path

from app.core.storage import atomic_write_json
from app.retrieval.engine import build_index, citations, search


def make_site(path: Path):
    atomic_write_json(path / "pages.json", [{
        "type": "webpage",
        "title": "Acme Returns",
        "url": "https://example.com/returns",
        "text": "Customers may return unopened items within thirty days of delivery.",
    }])
    atomic_write_json(path / "documents.json", [{
        "type": "pdf",
        "title": "Safety Manual",
        "filename": "safety-manual.pdf",
        "url": "https://example.com/safety-manual.pdf",
        "page": 4,
        "text": "Disconnect the device from power before performing maintenance.",
        "text_quality": 1.0,
    }])
    build_index(path)


def test_exact_filename_restricts_results(tmp_path):
    make_site(tmp_path)
    result = search(tmp_path, "What does safety-manual.pdf say?", limit=5)
    assert result["exact_document"] is True
    assert {item["filename"] for item in result["results"]} == {"safety-manual.pdf"}


def test_hybrid_search_finds_relevant_page(tmp_path):
    make_site(tmp_path)
    result = search(tmp_path, "How long can customers return unopened items?")
    assert result["results"][0]["title"] == "Acme Returns"


def test_citations_are_deduplicated(tmp_path):
    make_site(tmp_path)
    result = search(tmp_path, "safety-manual.pdf", limit=5)
    sources = citations(result["results"])
    assert len({(source["url"], source.get("page")) for source in sources}) == len(sources)


def test_unknown_exact_filename_returns_no_neighbours(tmp_path):
    make_site(tmp_path)
    result = search(tmp_path, "Summarize missing-file.pdf")
    assert result["exact_document"] is False
    assert result["results"] == []


def test_exact_url_restricts_results(tmp_path):
    make_site(tmp_path)
    result = search(tmp_path, "Read https://example.com/safety-manual.pdf")
    assert result["exact_document"] is True
    assert {item["title"] for item in result["results"]} == {"Safety Manual"}


def test_exact_title_restricts_results(tmp_path):
    make_site(tmp_path)
    result = search(tmp_path, "Summarize the Safety Manual")
    assert result["exact_document"] is True
    assert {item["title"] for item in result["results"]} == {"Safety Manual"}


def test_two_site_indexes_do_not_mix(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    atomic_write_json(first / "pages.json", [{
        "title": "Alpha facts", "url": "https://alpha.test", "text": "The alpha access code is blue cedar."
    }])
    atomic_write_json(first / "documents.json", [])
    atomic_write_json(second / "pages.json", [{
        "title": "Beta facts", "url": "https://beta.test", "text": "The beta access code is silver cloud."
    }])
    atomic_write_json(second / "documents.json", [])
    build_index(first)
    build_index(second)
    first_result = search(first, "What is the alpha access code?")
    assert all("silver cloud" not in item["text"] for item in first_result["results"])
