from unittest.mock import patch

from app.generation.providers import generate_answer


EVIDENCE = [{"title": "Returns", "page": 1, "text": "Returns are accepted within thirty days."}]


@patch("app.generation.providers.settings")
@patch("app.generation.providers._gemini")
def test_gemini_success(gemini, settings):
    settings.generation_provider = "auto"
    gemini.return_value = "Returns are accepted within thirty days."
    result = generate_answer("When can I return it?", EVIDENCE)
    assert result.provider == "gemini"
    assert not result.fallback_used


@patch("app.generation.providers.settings")
@patch("app.generation.providers._ollama")
@patch("app.generation.providers._gemini")
def test_gemini_failure_uses_ollama(gemini, ollama, settings):
    settings.generation_provider = "auto"
    gemini.side_effect = TimeoutError()
    ollama.return_value = "Thirty days."
    result = generate_answer("When?", EVIDENCE)
    assert result.provider == "ollama"
    assert len(result.attempts) == 2


@patch("app.generation.providers.settings")
@patch("app.generation.providers._ollama")
@patch("app.generation.providers._gemini")
def test_both_fail_use_safe_local_answer(gemini, ollama, settings):
    settings.generation_provider = "auto"
    gemini.side_effect = TimeoutError()
    ollama.side_effect = OSError()
    result = generate_answer("When?", EVIDENCE)
    assert result.provider == "local"
    assert result.fallback_used
    assert "thirty days" in result.answer.lower()
