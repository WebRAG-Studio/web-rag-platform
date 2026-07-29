from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit


class UnsafeUrlError(ValueError):
    """Raised when a URL is not safe for server-side fetching."""


BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "metadata",
    "169.254.169.254",
}

TRACKING_PARAMETERS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
}


def canonicalize_url(url: str, base: str | None = None) -> str:
    absolute = urljoin(base or "", url.strip())
    parsed = urlsplit(absolute)
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if not scheme or not hostname:
        return ""
    port = parsed.port
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    netloc = hostname if port is None or default_port else f"{hostname}:{port}"
    path = parsed.path or "/"
    while "//" in path:
        path = path.replace("//", "/")
    if path != "/":
        path = path.rstrip("/")
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMETERS and not key.lower().startswith("utm_")
    ]
    return urlunsplit((scheme, netloc, path, urlencode(sorted(query)), ""))


def _is_blocked_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


def resolve_host(hostname: str) -> set[str]:
    return {
        row[4][0]
        for row in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    }


def validate_public_url(
    url: str,
    resolver: Callable[[str], set[str]] = resolve_host,
) -> str:
    parsed = urlsplit(url.strip())
    if parsed.scheme.lower() not in {"http", "https"}:
        raise UnsafeUrlError("Only HTTP and HTTPS URLs are allowed.")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("Credentials embedded in URLs are not allowed.")
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if not hostname or hostname in BLOCKED_HOSTS:
        raise UnsafeUrlError("The target host is not public.")
    try:
        if _is_blocked_ip(hostname):
            raise UnsafeUrlError("Private, loopback, and link-local addresses are blocked.")
    except ValueError:
        pass
    try:
        addresses = resolver(hostname)
    except OSError as error:
        raise UnsafeUrlError("The target hostname could not be resolved.") from error
    if not addresses or any(_is_blocked_ip(address) for address in addresses):
        raise UnsafeUrlError("The target resolves to a blocked network address.")
    canonical = canonicalize_url(url)
    if not canonical:
        raise UnsafeUrlError("The URL is invalid.")
    return canonical


def validate_redirect(
    source_url: str,
    target_url: str,
    resolver: Callable[[str], set[str]] = resolve_host,
) -> str:
    return validate_public_url(urljoin(source_url, target_url), resolver=resolver)
