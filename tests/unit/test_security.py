from unittest.mock import patch

import pytest

from app.core.security import UnsafeUrlError, canonicalize_url, validate_public_url, validate_redirect


def test_canonical_url_removes_tracking_and_fragment():
    assert canonicalize_url("HTTPS://Example.COM:443/a/?utm_source=x&b=2#part") == "https://example.com/a?b=2"


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/admin",
    "http://localhost/test",
    "http://169.254.169.254/latest/meta-data",
    "file:///etc/passwd",
    "https://user:pass@example.com",
])
def test_unsafe_urls_are_rejected(url):
    with pytest.raises(UnsafeUrlError):
        validate_public_url(url)


@patch("app.core.security.socket.getaddrinfo")
def test_dns_resolving_to_private_address_is_rejected(getaddrinfo):
    getaddrinfo.return_value = [(2, 1, 6, "", ("10.0.0.4", 443))]
    with pytest.raises(UnsafeUrlError):
        validate_public_url("https://example.test")


def test_redirect_to_private_target_is_rejected():
    with pytest.raises(UnsafeUrlError):
        validate_redirect("https://example.com", "http://127.0.0.1/secret")
