import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
JAVASCRIPT = (ROOT / "frontend" / "assets" / "app.js").read_text(encoding="utf-8")
STYLES = (ROOT / "frontend" / "assets" / "styles.css").read_text(encoding="utf-8")
WIDGET = (ROOT / "frontend" / "widget.js").read_text(encoding="utf-8")
ACTIVE_FRONTEND = "\n".join((HTML, JAVASCRIPT, STYLES, WIDGET))


def test_root_markup_has_sitemind_branding_and_attribution():
    assert "<title>SiteMind | Website Assistant Builder</title>" in HTML
    assert "SiteMind Labs" in HTML
    assert "Turn websites into intelligent, source-grounded assistants." in HTML


def test_active_frontend_has_no_institution_specific_branding():
    forbidden = (
        "senate.gov.pk",
        "Senate of Pakistan",
        "Senate Assistant",
        "HOUSE OF THE FEDERATION",
        "Resolution No.",
    )
    assert not any(value.lower() in ACTIVE_FRONTEND.lower() for value in forbidden)


def test_active_javascript_has_no_tunnel_or_localhost_api():
    assert "trycloudflare.com" not in JAVASCRIPT
    assert "trycloudflare.com" not in WIDGET
    assert not re.search(r"https?://(?:127\.0\.0\.1|localhost):\d+", JAVASCRIPT)
    assert not re.search(r"https?://(?:127\.0\.0\.1|localhost):\d+", WIDGET)


def test_frontend_uses_relative_site_scoped_api_paths():
    assert 'api("/api/sites")' in JAVASCRIPT
    assert "/api/sites/${encodeURIComponent(state.active)}/chat" in JAVASCRIPT
    assert "/api/sites/${encodeURIComponent(state.active)}/progress" in JAVASCRIPT
    assert "/api/sites/${encodeURIComponent(state.active)}/conversation/reset" in JAVASCRIPT


def test_onboarding_fields_and_crawl_controls_are_present():
    for name in (
        "site_name",
        "website_url",
        "assistant_name",
        "crawl_mode",
        "max_pages",
        "include_html",
        "include_pdf",
        "enable_ocr",
        "languages",
        "logo_url",
        "accent_color",
    ):
        assert f'name="{name}"' in HTML
    assert "Create Website Assistant" in HTML


def test_generic_welcome_and_suggestions_are_present():
    assert "Hello! Ask me about the information available on this website" in JAVASCRIPT
    assert "What information is available on this website?" in JAVASCRIPT
    assert "Which documents are indexed?" in JAVASCRIPT


def test_dashboard_and_progress_are_site_scoped():
    assert "site.site_id" in JAVASCRIPT
    assert 'data-view="progress"' in JAVASCRIPT
    assert "pages_discovered" in JAVASCRIPT
    assert "documents_processed" in JAVASCRIPT
    assert "chunks_indexed" in JAVASCRIPT
    assert "eta_seconds" in JAVASCRIPT
    assert "setInterval(refreshProgress, 2000)" in JAVASCRIPT


def test_voice_rtl_sources_and_highlights_remain():
    assert "SpeechRecognition" in JAVASCRIPT
    assert "speechSynthesis" in JAVASCRIPT
    assert r"\u0600-\u06ff" in JAVASCRIPT
    assert "source.local_url || source.url" in JAVASCRIPT
    assert "source.highlight" in JAVASCRIPT
    assert '[dir="rtl"]' in STYLES


def test_untrusted_dynamic_values_are_escaped():
    assert "function escapeHtml" in JAVASCRIPT
    assert "${escapeHtml(site.site_name)}" in JAVASCRIPT
    assert "${escapeHtml(source.title)}" in JAVASCRIPT
    assert "output.textContent = result.answer" in WIDGET


def test_widget_requires_site_id_and_uses_site_scoped_routes():
    assert "validSiteId" in WIDGET
    assert "requires a valid site-id" in WIDGET
    assert "/api/sites/${encodeURIComponent(siteId)}/chat" in WIDGET
    assert "/api/sites/${encodeURIComponent(siteId)}/conversation/reset" in WIDGET
    assert "source.page" in WIDGET


def test_no_obsolete_versioned_assets_are_referenced():
    assert not re.search(r"voice-assistant-v[2-9]|script-v[2-9]|styles-v[2-9]", ACTIVE_FRONTEND, re.I)


def test_voice_status_is_json_safe():
    from app.voice.router import voice_status

    result = voice_status()
    assert result["available"] is True
    assert isinstance(result["message"], str)
