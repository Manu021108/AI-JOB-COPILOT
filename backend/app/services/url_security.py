"""SSRF protection for outbound URL fetching.

Job URLs are untrusted input. Before fetching anything we validate the scheme,
reject obviously-dangerous hostnames, and - for normal hostnames - resolve the
addresses and reject any that map to private/loopback/link-local/reserved space.
Redirect destinations are validated again before they are followed.
"""
import ipaddress
import socket
from typing import Callable
from urllib.parse import urlsplit

ALLOWED_SCHEMES = {"http", "https"}
_FORBIDDEN_HOSTNAMES = {"localhost", "localhost.localdomain"}


class UrlSecurityError(Exception):
    """Raised when a URL or host fails SSRF validation."""


def validate_scheme(url: str) -> str:
    parsed = urlsplit(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise UrlSecurityError(f"Only http:// and https:// URLs are supported.")
    return scheme


def _resolve(hostname: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UrlSecurityError("The URL host could not be resolved.") from exc
    addresses: list[str] = []
    for info in infos:
        address = info[4][0]
        address = address.split("%", 1)[0]
        if address not in addresses:
            addresses.append(address)
    return addresses


def _is_unsafe(hostname: str) -> bool:
    base = hostname.lower().rstrip(".").lstrip("[")
    if base in _FORBIDDEN_HOSTNAMES:
        return True
    if base.endswith(".local") or base.endswith(".internal") or base == "local":
        return True
    return False


def _ip_is_unsafe(ip_string: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_string)
    except ValueError:
        ip = None
    if ip is None:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def assert_safe_url(url: str, resolve: Callable[[str], list[str]] | None = None) -> None:
    """Validate that a URL is safe to fetch. Raises UrlSecurityError otherwise."""
    validate_scheme(url)
    hostname = urlsplit(url).hostname
    if not hostname:
        raise UrlSecurityError("The URL has no host.")
    if _is_unsafe(hostname):
        raise UrlSecurityError("Internal or local hosts are not allowed.")
    resolver = resolve or _resolve
    if _is_ip_literal(hostname):
        if _ip_is_unsafe(hostname.strip("[]")):
            raise UrlSecurityError("Private, loopback and link-local addresses are not allowed.")
        return
    addresses = resolver(hostname)
    if not addresses:
        raise UrlSecurityError("The URL host could not be resolved.")
    if any(_ip_is_unsafe(address) for address in addresses):
        raise UrlSecurityError("Private, loopback and link-local addresses are not allowed.")


def _is_ip_literal(hostname: str) -> bool:
    candidate = hostname.strip("[]")
    try:
        ipaddress.ip_address(candidate)
        return True
    except ValueError:
        return False