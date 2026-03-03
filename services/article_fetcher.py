# services/article_fetcher.py
# Fetches full article text from a URL for email content grounding
# Strips HTML tags and extracts readable body text
# Used by compose_field_note to populate ContentAsset.article_body

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Max chars to keep from fetched article (avoid stuffing prompts)
MAX_ARTICLE_CHARS = 8000

# Timeout for fetching articles
FETCH_TIMEOUT_SECONDS = 15

# Tags whose content should be stripped entirely (not just the tag)
STRIP_CONTENT_TAGS = [
    "script", "style", "nav", "header", "footer",
    "aside", "noscript", "iframe", "form",
]


async def fetch_article_text(url: str) -> str | None:
    # Fetch a URL and extract readable text content
    # Returns plain text or None if fetch fails
    #
    # Strips HTML tags, scripts, styles, nav elements.
    # Truncates to MAX_ARTICLE_CHARS to keep prompt size manageable.

    if not url or url.startswith("https://example.com"):
        logger.debug(f"Skipping fetch for non-real URL: {url}")
        return None

    try:
        async with httpx.AsyncClient(
            timeout=FETCH_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={
                "User-Agent": "JourneyOS-ContentFetcher/1.0",
                "Accept": "text/html,application/xhtml+xml",
            },
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            logger.info(
                f"Non-HTML content type, skipping: {content_type}",
                extra={"url": url},
            )
            return None

        html = response.text
        text = _html_to_text(html)

        if not text or len(text.strip()) < 100:
            logger.warning(
                "Fetched article has very little text content",
                extra={"url": url, "text_length": len(text.strip())},
            )
            return None

        # Truncate to keep prompt size reasonable
        if len(text) > MAX_ARTICLE_CHARS:
            text = text[:MAX_ARTICLE_CHARS] + "\n\n[Article truncated]"

        logger.info(
            "Article content fetched",
            extra={
                "url": url,
                "text_length": len(text),
                "truncated": len(text) >= MAX_ARTICLE_CHARS,
            },
        )

        return text

    except httpx.HTTPStatusError as e:
        logger.warning(
            f"HTTP error fetching article: {e.response.status_code}",
            extra={"url": url},
        )
        return None
    except httpx.RequestError as e:
        logger.warning(
            f"Request error fetching article: {e}",
            extra={"url": url},
        )
        return None
    except Exception as e:
        logger.warning(
            f"Unexpected error fetching article: {e}",
            extra={"url": url},
        )
        return None


def _html_to_text(html: str) -> str:
    # Convert HTML to readable plain text
    # Strips tags, scripts, styles, and collapses whitespace

    text = html

    # Remove content of tags we don't want at all
    for tag in STRIP_CONTENT_TAGS:
        text = re.sub(
            rf"<{tag}[^>]*>.*?</{tag}>",
            " ",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )

    # Replace block-level tags with newlines for readability
    block_tags = ["p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
                  "li", "tr", "br", "blockquote", "section", "article"]
    for tag in block_tags:
        text = re.sub(rf"</?{tag}[^>]*>", "\n", text, flags=re.IGNORECASE)

    # Replace list items with bullet-like formatting
    text = re.sub(r"<li[^>]*>", "\n- ", text, flags=re.IGNORECASE)

    # Strip all remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Decode common HTML entities
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    text = text.replace("&nbsp;", " ")
    text = text.replace("&mdash;", "—")
    text = text.replace("&ndash;", "–")
    text = text.replace("&rsquo;", "'")
    text = text.replace("&lsquo;", "'")
    text = text.replace("&rdquo;", "\u201d")
    text = text.replace("&ldquo;", "\u201c")

    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    return text.strip()
