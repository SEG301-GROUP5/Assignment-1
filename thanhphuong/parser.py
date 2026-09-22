"""HTML parsing, URL normalization, extraction, and filtering helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import PurePosixPath
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup


TRACKING_QUERY_KEYS = {
    "fbclid", "gclid", "mc_cid", "mc_eid", "_rsc",
}


def normalize_url(url: str) -> str:
    """Normalize a web URL without breaking server canonical redirects.

    Important: trailing slashes are PRESERVED. Some sites (including common
    framework-driven sites) canonicalize ``/search`` to ``/search/``. Removing
    that slash before every request can create an artificial redirect loop and
    prevent the crawler from ever reaching the final HTML page.

    Rules:
    - lowercase scheme + hostname
    - remove URL fragments (#...)
    - remove default ports (:80 for HTTP, :443 for HTTPS)
    - preserve the server path, including a meaningful trailing slash
    - remove common tracking query parameters such as utm_* and fbclid
    - keep other query parameters because they may change page content
    """
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()

    if not scheme or not hostname:
        return url.strip()

    try:
        port = parsed.port
    except ValueError:
        return url.strip()

    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None

    netloc = hostname if port is None else f"{hostname}:{port}"
    path = parsed.path or "/"

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

    # Chỉ chặn các URL /search/ có query PHÂN TRANG hoặc SẮP XẾP — đây là
    # những trang chắc chắn render bằng JS phía client (không có HTML thật).
    # Query tìm kiếm thực (?q=, ?t=, ?l=) VẪN ĐƯỢC PHÉP crawl, vì trang
    # search của MIT OCW có chứa các link course hữu ích trong HTML tĩnh.
    path_clean = parsed.path.rstrip("/")
    if path_clean.endswith("/search") and parsed.query:
        skip_keys = {"page", "p", "sort", "view", "format"}
        query_keys = {k.lower() for k, _ in parse_qsl(parsed.query)}
        if query_keys & skip_keys:
            return False, "js_rendered_search_page"

    return True, "valid"


def looks_like_html(content_type: str, body: str) -> bool:
    """Return True when a 200 response can reasonably be parsed as HTML."""
    ctype = (content_type or "").lower()
    if "text/html" in ctype or "application/xhtml+xml" in ctype:
        return True
    if ctype and not ctype.startswith("text/"):
        return False

    sample = (body or "").lstrip()[:500].lower()
    return sample.startswith("<!doctype html") or "<html" in sample


def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


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
    if soup is not None:
        if soup.title:
            title = soup.title.get_text(" ", strip=True)

        # Remove non-visible elements while retaining the complete visible text.
        for tag in soup(["script", "style", "noscript", "template", "svg"]):
            tag.decompose()
        content = soup.get_text(separator=" ", strip=True)

    return {
        "url": url,
        "domain": parsed.netloc,
        "title": title,
        "content": content,
        "depth": depth,
        "status_code": status_code,
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "response_time": response_time,
    }


def extract_links(current_url: str, soup: BeautifulSoup) -> list[str]:
    """Extract HTTP(S) links and convert relative links to absolute URLs.

    Lưu ý: KHÔNG lọc /search?... tại đây — để is_valid_url() quyết định
    khi URL được pop khỏi frontier, nhờ đó các query tìm kiếm có kết quả
    (q=, t=, l=) vẫn có cơ hội được crawl để lấy link course.
    """
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