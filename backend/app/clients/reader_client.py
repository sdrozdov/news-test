"""Reader-mode article extraction.

Most publishers block being embedded in an iframe (``X-Frame-Options`` /
``CSP: frame-ancestors``), so instead we fetch the article server-side and
extract its main content — like a browser's reader view — as ordered text and
image blocks. Extraction is best-effort: paywalled or bot-blocked pages fail
cleanly and the UI falls back to the summary plus a link out. Parsing runs in a
thread so it never blocks the event loop.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import re
from urllib.parse import urlsplit

import httpx

from app.config import Settings
from app.errors import AppError
from app.schemas.news import ArticleBlock, ExtractedArticle

logger = logging.getLogger(__name__)

_USER_AGENT = "Mozilla/5.0 (compatible; NewsAI-Reader/1.0)"
_MAX_CHARS = 3_000_000

# Trafilatura emits inline media/links as markdown; we turn images into image
# blocks and unwrap links to their text so nothing renders as raw markdown.
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\((https?://[^)\s]+)[^)]*\)")
_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def _guard_url(url: str) -> None:
    """Reject non-http(s) and obvious internal targets (basic SSRF guard)."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise AppError("Invalid article URL.", status_code=400, code="bad_url")
    host = parts.hostname
    if host == "localhost" or host.endswith(".local"):
        raise AppError("Refusing to fetch an internal URL.", status_code=400, code="bad_url")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return  # hostname (not a literal IP); DNS-based SSRF is out of scope here
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
        raise AppError("Refusing to fetch an internal URL.", status_code=400, code="bad_url")


def _to_blocks(text: str) -> list[ArticleBlock]:
    """Split extracted text into ordered ``text``/``image`` blocks."""
    blocks: list[ArticleBlock] = []
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        images = _MD_IMAGE.findall(line)
        prose = _MD_LINK.sub(r"\1", _MD_IMAGE.sub("", line)).strip()
        if prose:
            blocks.append(ArticleBlock(type="text", value=prose))
        for src in images:
            blocks.append(ArticleBlock(type="image", value=src))
    return blocks


class ArticleReader:
    """Fetches an article URL and extracts readable content as blocks."""

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._http = http_client or httpx.AsyncClient(
            timeout=12.0,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        )

    async def extract(self, url: str) -> ExtractedArticle:
        _guard_url(url)
        try:
            response = await self._http.get(url)
        except httpx.HTTPError:
            logger.info("Reader fetch failed for %s", url, exc_info=True)
            raise AppError(
                "Could not fetch the article.", status_code=502, code="reader_error"
            ) from None
        if response.status_code >= 400:
            raise AppError(
                f"The article could not be loaded (HTTP {response.status_code}).",
                status_code=502,
                code="reader_error",
            )

        html = response.text[:_MAX_CHARS]
        data = await asyncio.to_thread(_extract_sync, html, url)
        blocks = _to_blocks((data or {}).get("text") or "")
        if not data or not any(b.type == "text" for b in blocks):
            raise AppError(
                "Couldn't extract readable content (the article may be paywalled).",
                status_code=422,
                code="reader_empty",
            )
        return ExtractedArticle(
            url=url,
            title=data.get("title"),
            author=data.get("author"),
            image=data.get("image"),
            site_name=data.get("sitename") or data.get("hostname"),
            blocks=blocks,
        )

    async def aclose(self) -> None:
        await self._http.aclose()


def _extract_sync(html: str, url: str) -> dict | None:
    import trafilatura

    result = trafilatura.extract(
        html,
        url=url,
        output_format="json",
        with_metadata=True,
        include_comments=False,
        include_images=True,
        include_links=False,
        favor_precision=True,
    )
    if not result:
        return None
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return None
