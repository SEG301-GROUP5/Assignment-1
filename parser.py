"""HTML parsing, URL normalization, extraction, and filtering helpers."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import PurePosixPath
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup


TRACKING_QUERY_KEYS = {
    "fbclid", "gclid", "mc_cid", "mc_eid", "_rsc",
}

# Tags stripped before extracting visible text: they repeat on every page
# (nav/footer/header/forms) and add noise rather than real content.
BOILERPLATE_TAGS = [
    "script", "style", "noscript", "template", "svg",
    "nav", "footer", "header", "aside", "form", "button",
]

# Content-quality thresholds used to decide what's worth storing.
MIN_CONTENT_LENGTH = 100     # shorter than this -> treated as a low-value page
MAX_CONTENT_LENGTH = 8000    # longer than this -> truncated before storing


def normalize_url(url: str) -> str:
    """Normalize a web URL to reduce duplicate crawling.

    Rules used here are intentionally conservative:
    - lowercase scheme + host
    - remove URL fragments (#...)
    - remove default ports (:80 for HTTP, :443 for HTTPS)
    - remove a trailing slash except for the root path
    - remove common tracking parameters such as utm_* and fbclid
    - keep all other query parameters because they may change page content
    """
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()

    if not scheme or not hostname:
        return url.strip()

    port = parsed.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None

    netloc = hostname if port is None else f"{hostname}:{port}"

    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    kept_query = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lower_key = key.lower()
        if lower_key.startswith("utm_") or lower_key in TRACKING_QUERY_KEYS:
            continue
        kept_query.append((key, value))

    query = urlencode(kept_query, doseq=True)
    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def domain_is_allowed(hostname: str, allowed_domains: list[str]) -> bool:
    """Allow exact root domains and their subdomains without false suffix matches."""
    host = hostname.lower().strip(".")
    for domain in allowed_domains:
        root = domain.lower().strip(".")
        if host == root or host.endswith("." + root):
            return True
    return False


def is_valid_url(url: str, allowed_domains: list[str], blocked_extensions: set[str]) -> tuple[bool, str]:
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        return False, "unsupported_protocol"

    if not parsed.hostname:
        return False, "missing_domain"

    if parsed.username or parsed.password:
        return False, "embedded_credentials"

    if not domain_is_allowed(parsed.hostname, allowed_domains):
        return False, "outside_allowed_domain"

    suffix = PurePosixPath(parsed.path.lower()).suffix
    if suffix in blocked_extensions:
        return False, "blocked_file_type"

    # /search pages on ocw.mit.edu render results client-side with
    # JavaScript; requests/BeautifulSoup only see the empty HTML shell
    # (0 chars of content), so they're rejected here instead of wasting a
    # MAX_PAGES request on a page we already know will be empty.
    normalized_path = parsed.path.rstrip("/")
    if normalized_path == "/search" and parsed.query:
        return False, "js_rendered_search_page"

    return True, "valid"


def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def is_low_value_content(content: str) -> bool:
    """A page whose visible text is too short to be useful (e.g. a login
    page, an empty listing, a redirect stub) is not worth storing."""
    return len(content.strip()) < MIN_CONTENT_LENGTH


def extract_page_information(
    url: str,
    soup: BeautifulSoup | None,
    depth: int,
    status_code: int,
    response_time: float,
) -> dict:
    parsed = urlparse(url)

    title = ""
    content = ""
    content_hash = None

    if soup is not None:
        if soup.title:
            title = soup.title.get_text(" ", strip=True)

        # Remove boilerplate elements so the extracted text is the actual
        # page content, not navigation/footer text repeated on every page.
        for tag in soup(BOILERPLATE_TAGS):
            tag.decompose()

        # Prefer a main content region if the page marks one; falls back to
        # the whole (already-stripped) document otherwise.
        main = soup.find("main") or soup.find("article") or soup
        content = main.get_text(separator=" ", strip=True)
        content = " ".join(content.split())  # collapse repeated whitespace

        if len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH]

        if content:
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    return {
        "url": url,
        "domain": parsed.netloc,
        "title": title,
        "content": content,
        "content_hash": content_hash,
        "depth": depth,
        "status_code": status_code,
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "response_time": response_time,
    }


def extract_links(current_url: str, soup: BeautifulSoup) -> list[str]:
    """Extract HTTP(S) links and convert relative links to absolute URLs."""
    result: list[str] = []
    seen: set[str] = set()

    for tag in soup.find_all("a", href=True):
        href = tag.get("href", "").strip()
        if not href:
            continue

        lower = href.lower()
        if lower.startswith(("mailto:", "javascript:", "tel:", "data:")):
            continue

        absolute = urljoin(current_url, href)
        normalized = normalize_url(absolute)
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue

        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)

    return result