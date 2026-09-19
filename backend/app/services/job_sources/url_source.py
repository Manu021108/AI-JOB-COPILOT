"""URL job source: retrieve a public job page and extract its content.

Fetching is only attempted for permitted, technically accessible pages.
LinkedIn is explicitly rejected with an instruction to paste the description
instead. SSRF protection is applied before every fetch and every redirect hop.
"""
from __future__ import annotations

import asyncio
from urllib.parse import urlsplit

from app.services.job_page_parser import extract_text_from_html
from app.services.job_text_cleaner import clean_job_text
from app.services.job_sources.base import JobContent, JobSourceError
from app.services.job_sources.http_client import HttpFetcher, HttpFetchError, USER_AGENT, is_linkedin_url
from app.services.url_security import UrlSecurityError, assert_safe_url

MIN_JOB_TEXT_CHARS = 80


class UrlJobSource:
    def __init__(
        self,
        fetcher: HttpFetcher | None = None,
        validator=assert_safe_url,
        robots: "RobotsTxtPolicy | None" = None,
    ) -> None:
        self.fetcher = fetcher or HttpFetcher()
        self.validator = validator
        self.robots = robots if robots is not None else RobotsTxtPolicy(self.fetcher)

    async def fetch(self, payload: dict) -> JobContent:
        url = (payload.get("url") or "").strip()
        if not url:
            raise JobSourceError("VALIDATION_ERROR", "A job URL is required.")
        if is_linkedin_url(url):
            raise JobSourceError(
                "LINKEDIN_MANUAL_INPUT_REQUIRED",
                "For LinkedIn jobs, paste the job description or add the job manually.",
            )
        try:
            self.validator(url)
        except UrlSecurityError as exc:
            raise JobSourceError("URL_NOT_ALLOWED", str(exc)) from exc

        allowed = await self.robots.allows(url)
        if not allowed:
            raise JobSourceError(
                "ROBOTS_BLOCKED",
                "The website's robots.txt policy does not allow fetching this page. Please paste the job description instead.",
            )

        try:
            result = await self.fetcher.fetch(url)
        except HttpFetchError as exc:
            raise JobSourceError(exc.code, exc.message) from exc

        if result.content_type == "text/plain" or result.content_type == "application/json":
            page_text = result.body.decode("utf-8", errors="replace")
        else:
            page_text = extract_text_from_html(result.body)
        description = clean_job_text(page_text)

        if len(description) < MIN_JOB_TEXT_CHARS:
            raise JobSourceError(
                "EMPTY_URL_CONTENT",
                "No readable job content could be extracted from that page. Please paste the job description instead.",
            )

        return JobContent(
            source="URL",
            source_url=url,
            description=description,
            analyzed=True,
        )


class RobotsTxtPolicy:
    """Minimal robots.txt policy cache using the same safe fetcher.

    Fetching robots.txt happens through the SSRF-guarded HttpFetcher so no
    outbound request is ever made to an unvalidated host. Any failure is
    treated as "allowed" so a blocked robots.txt does not take the feature down.
    """

    def __init__(self, fetcher: HttpFetcher | None = None) -> None:
        self.fetcher = fetcher
        self._cache: dict[str, object] = {}
        self._lock = asyncio.Lock()

    async def allows(self, url: str) -> bool:
        try:
            parser = await self._load(url)
            return bool(parser.can_fetch(USER_AGENT, url))
        except Exception:
            return True

    async def _load(self, url: str):
        from urllib.robotparser import RobotFileParser

        parsed = urlsplit(url)
        key = f"{parsed.scheme}://{parsed.netloc}"
        async with self._lock:
            parser = self._cache.get(key)
            if parser is not None:
                return parser
            robots_url = f"{key}/robots.txt"
            rp = RobotFileParser()
            if self.fetcher is not None:
                try:
                    result = await self.fetcher.fetch(robots_url)
                    rp.parse(result.body.decode("utf-8", errors="replace").splitlines())
                except HttpFetchError:
                    rp.parse([])
            else:
                rp.parse([])
            self._cache[key] = rp
            return rp