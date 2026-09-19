"""Async HTTP fetcher with SSRF-safe redirect handling and a response size limit.

Deliberately avoids browser automation and anti-bot bypass. Each redirect hop
re-validates the destination before it is followed.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

from app.core.config import get_settings
from app.services.url_security import UrlSecurityError, assert_safe_url, validate_scheme

USER_AGENT = "AIJobCopilot/0.1 (+https://github.com/Manu021108/AI-JOB-COPILOT)"


class HttpFetchError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class FetchResult:
    final_url: str
    content_type: str
    body: bytes


class HttpFetcher:
    def __init__(
        self,
        connect_timeout: float | None = None,
        request_timeout: float | None = None,
        max_size: int | None = None,
        max_redirects: int | None = None,
    ) -> None:
        settings = get_settings()
        self.connect_timeout = connect_timeout if connect_timeout is not None else settings.job_fetch_connect_timeout
        self.request_timeout = request_timeout if request_timeout is not None else settings.job_fetch_timeout
        self.max_size = max_size if max_size is not None else settings.job_fetch_max_size
        self.max_redirects = max_redirects if max_redirects is not None else settings.job_fetch_max_redirects

    async def fetch(self, url: str) -> FetchResult:
        validate_scheme(url)
        timeout = httpx.Timeout(self.request_timeout, connect=self.connect_timeout)
        current = url
        try:
            async with httpx.AsyncClient(follow_redirects=False, timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
                for hop in range(self.max_redirects + 1):
                    assert_safe_url(current)
                    try:
                        async with client.stream("GET", current) as response:
                            status = response.status_code
                            if status in (301, 302, 303, 307, 308) and response.headers.get("location"):
                                current = urljoin(current, response.headers["location"])
                                continue
                            if status != 200:
                                raise HttpFetchError("HTTP_ERROR", f"The URL returned HTTP {status}.")
                            content_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
                            body = await self._read(response)
                            if not _acceptable(content_type, body):
                                raise HttpFetchError(
                                    "UNSUPPORTED_CONTENT",
                                    "The URL did not return an HTML or plain-text page. Please paste the job description instead.",
                                )
                            return FetchResult(final_url=current, content_type=content_type, body=body)
                    except httpx.TimeoutException:
                        raise HttpFetchError("FETCH_TIMEOUT", "The job page took too long to respond. Please try again or paste the job description.")
                raise HttpFetchError("TOO_MANY_REDIRECTS", "The URL redirected too many times. Please paste the job description instead.")
        except httpx.TimeoutException:
            raise HttpFetchError("FETCH_TIMEOUT", "The job page took too long to respond. Please try again or paste the job description.")
        except httpx.TransportError as exc:
            raise HttpFetchError("UNREACHABLE", "The job page could not be reached. Please check the URL or paste the job description.") from exc

    async def _read(self, response) -> bytes:
        chunk_size = 65536
        body = b""
        async for chunk in response.aiter_bytes(chunk_size=chunk_size):
            body += chunk
            if len(body) > self.max_size:
                limit_mb = round(self.max_size / (1024 * 1024), 1)
                raise HttpFetchError("TOO_LARGE", f"The job page is larger than the {limit_mb} MB limit.")
        return body


def _acceptable(content_type: str, body: bytes) -> bool:
    if content_type in {"text/html", "application/xhtml+xml", "text/plain", "application/json"}:
        return True
    if not content_type:
        sample = body[:1024].lower()
        return b"<html" in sample or b"<!doctype" in sample
    return False


def is_linkedin_url(url: str) -> bool:
    hostname = (urlsplit(url).hostname or "").lower()
    return hostname == "linkedin.com" or hostname.endswith(".linkedin.com")