"""Complete focused web crawler for the SEG301 assignment."""
from __future__ import annotations

import time
from collections import Counter
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests

import config
from database import CrawlerDatabase
from parser import (
    extract_links,
    extract_page_information,
    is_valid_url,
    looks_like_html,
    normalize_url,
    parse_html,
)
from url_frontier import URLFrontier


REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}


class FocusedCrawler:
    def __init__(self) -> None:
        self.frontier = URLFrontier()
        self.db = CrawlerDatabase(
            config.DATABASE_PATH,
            reset=config.RESET_DATABASE_ON_START,
        )

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": config.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.8",
            }
        )

        self.robots_cache: dict[str, RobotFileParser] = {}
        self.robots_delay_cache: dict[str, float] = {}
        self.last_request_at: dict[str, float] = {}

        self.discovered_urls: set[str] = set()
        self.pages_crawled = 0
        self.html_pages_stored = 0
        self.request_attempts = 0
        self.failed_requests = 0
        self.skipped_urls = 0
        self.redirects_followed = 0
        self.total_links_extracted = 0
        self.total_links_queued = 0
        self.total_content_chars = 0

        self.skip_reasons: Counter[str] = Counter()
        self.status_counts: Counter[int] = Counter()
        self.redirect_status_counts: Counter[int] = Counter()
        self.depth_counts: Counter[int] = Counter()

        for seed in config.SEED_URLS:
            normalized = normalize_url(seed)
            self.discovered_urls.add(normalized)
            self.frontier.add(normalized, 0)

    def _base_url(self, url: str) -> str:
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}"

    def _get_robots(self, url: str) -> RobotFileParser:
        base = self._base_url(url)
        if base in self.robots_cache:
            return self.robots_cache[base]

        robots_url = base + "/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)

        print(f"[ROBOTS] Checking {robots_url} ...", flush=True)
        try:
            response = self.session.get(robots_url, timeout=config.REQUEST_TIMEOUT)
            if response.status_code == 200:
                rp.parse(response.text.splitlines())
            elif response.status_code in {401, 403}:
                rp.parse(["User-agent: *", "Disallow: /"])
            elif response.status_code == 404:
                rp.parse(["User-agent: *", "Disallow:"])
            elif 500 <= response.status_code < 600 and config.ROBOTS_FAIL_CLOSED:
                rp.parse(["User-agent: *", "Disallow: /"])
            else:
                rp.parse(["User-agent: *", "Disallow:"])
        except requests.RequestException:
            if config.ROBOTS_FAIL_CLOSED:
                rp.parse(["User-agent: *", "Disallow: /"])
            else:
                rp.parse(["User-agent: *", "Disallow:"])

        delay = rp.crawl_delay(config.USER_AGENT)
        if delay is None:
            delay = rp.crawl_delay("*")
        self.robots_delay_cache[base] = float(delay or 0.0)
        self.robots_cache[base] = rp
        return rp

    def _robots_allows(self, url: str) -> bool:
        if not config.RESPECT_ROBOTS_TXT:
            return True
        return self._get_robots(url).can_fetch(config.USER_AGENT, url)

    def _effective_delay(self, url: str) -> float:
        base = self._base_url(url)
        robots_delay = self.robots_delay_cache.get(base, 0.0)
        return max(float(config.CRAWL_DELAY), robots_delay)

    def _respect_delay(self, url: str) -> None:
        base = self._base_url(url)
        delay = self._effective_delay(url)
        previous = self.last_request_at.get(base)
        if previous is not None:
            remaining = delay - (time.monotonic() - previous)
            if remaining > 0:
                print(f"[WAIT] Polite crawl delay: {remaining:.1f}s for {base}", flush=True)
                time.sleep(remaining)

    def _mark_request_time(self, url: str) -> None:
        self.last_request_at[self._base_url(url)] = time.monotonic()

    def _skip(self, reason: str) -> None:
        self.skipped_urls += 1
        self.skip_reasons[reason] += 1

    def _fetch_with_safe_redirects(
        self, start_url: str
    ) -> tuple[requests.Response | None, str, float, str | None]:
        """Fetch to the final in-scope response, following safe redirects.

        Redirect responses are transport steps, not crawled pages. They are tracked
        separately and do not consume MAX_PAGES. This lets the crawler collect the
        final HTML document instead of filling the page budget with HTTP 301 entries.
        """
        current_url = normalize_url(start_url)
        redirect_seen = {current_url}
        total_elapsed = 0.0

        for hop in range(config.MAX_REDIRECTS + 1):
            valid, reason = is_valid_url(
                current_url, config.ALLOWED_DOMAINS, config.BLOCKED_EXTENSIONS
            )
            if not valid:
                return None, current_url, total_elapsed, reason

            if not self._robots_allows(current_url):
                return None, current_url, total_elapsed, "robots_disallowed"

            self._respect_delay(current_url)
            self.request_attempts += 1
            print(f"[REQUEST] {current_url}", flush=True)

            started = time.perf_counter()
            try:
                response = self.session.get(
                    current_url,
                    timeout=config.REQUEST_TIMEOUT,
                    allow_redirects=False,
                )
            except requests.RequestException as exc:
                self._mark_request_time(current_url)
                self.failed_requests += 1
                print(f"[FAILED] {current_url} | {exc}", flush=True)
                return None, current_url, total_elapsed, "request_failed"

            total_elapsed += time.perf_counter() - started
            self._mark_request_time(current_url)

            # Any URL actually requested in a redirect chain should not later be
            # requested again if it was also sitting in the BFS queue.
            self.frontier.mark_visited(current_url)

            if response.status_code not in REDIRECT_STATUS_CODES:
                return response, current_url, total_elapsed, None

            self.redirect_status_counts[response.status_code] += 1
            location = response.headers.get("Location")
            if not location:
                return None, current_url, total_elapsed, "redirect_missing_location"

            next_url = normalize_url(urljoin(current_url, location))
            self.discovered_urls.add(next_url)
            print(f"[REDIRECT {response.status_code}] {current_url} -> {next_url}", flush=True)

            valid, reason = is_valid_url(
                next_url, config.ALLOWED_DOMAINS, config.BLOCKED_EXTENSIONS
            )
            if not valid:
                return None, next_url, total_elapsed, f"redirect_{reason}"

            if next_url in redirect_seen:
                return None, next_url, total_elapsed, "redirect_loop"

            if hop >= config.MAX_REDIRECTS:
                return None, next_url, total_elapsed, "too_many_redirects"

            # Check the target before following it. _get_robots() is cached per host.
            if not self._robots_allows(next_url):
                return None, next_url, total_elapsed, "redirect_robots_disallowed"

            self.redirects_followed += 1
            redirect_seen.add(next_url)
            current_url = next_url

        return None, current_url, total_elapsed, "too_many_redirects"

    def _print_configuration(self) -> None:
        print("=" * 46)
        print(" FOCUSED WEB CRAWLER")
        print("=" * 46)
        print(f"Topic           : {config.TOPIC}")
        print(f"Seed URLs       : {len(config.SEED_URLS)}")
        for i, seed in enumerate(config.SEED_URLS, start=1):
            print(f"  {i}. {seed}")
        print("Allowed Domains:")
        for domain in config.ALLOWED_DOMAINS:
            print(f"  - {domain}")
        print(f"Maximum Depth   : {config.MAX_DEPTH}")
        print(f"Maximum Pages   : {config.MAX_PAGES}")
        print(f"Request Timeout : {config.REQUEST_TIMEOUT} seconds")
        print(f"Base Crawl Delay: {config.CRAWL_DELAY} second(s)")
        print(f"Respect robots.txt: {config.RESPECT_ROBOTS_TXT}")
        print(f"Maximum Redirects: {config.MAX_REDIRECTS}")
        print("=" * 46)

    def run(self) -> dict:
        self._print_configuration()

        try:
            while self.frontier and self.pages_crawled < config.MAX_PAGES:
                item = self.frontier.pop()
                if item is None:
                    break
                url, depth = item

                if url in self.frontier.visited:
                    self._skip("already_visited")
                    continue

                if depth > config.MAX_DEPTH:
                    self.frontier.mark_visited(url)
                    self._skip("max_depth")
                    continue

                valid, reason = is_valid_url(
                    url, config.ALLOWED_DOMAINS, config.BLOCKED_EXTENSIONS
                )
                if not valid:
                    self.frontier.mark_visited(url)
                    self._skip(reason)
                    continue

                print(f"[NEXT] Depth {depth} | {url}", flush=True)
                self.frontier.mark_visited(url)

                response, final_url, elapsed, fetch_issue = self._fetch_with_safe_redirects(url)
                if response is None:
                    if fetch_issue and fetch_issue != "request_failed":
                        self._skip(fetch_issue)
                        print(f"[SKIP {fetch_issue}] {final_url}", flush=True)
                    continue

                # Only the final non-redirect response counts as a crawled page.
                self.pages_crawled += 1
                self.status_counts[response.status_code] += 1
                self.depth_counts[depth] += 1
                self.discovered_urls.add(final_url)
                self.frontier.mark_visited(final_url)

                content_type = response.headers.get("Content-Type", "")
                soup = None
                extracted_links: list[str] = []

                if response.status_code == 200 and looks_like_html(content_type, response.text):
                    soup = parse_html(response.text)
                    # Extract links BEFORE extract_page_information(), because the latter
                    # removes non-visible tags from the BeautifulSoup tree.
                    extracted_links = extract_links(final_url, soup)
                    self.total_links_extracted += len(extracted_links)
                elif response.status_code == 200:
                    self._skip("non_html_response")

                record = extract_page_information(
                    url=final_url,
                    soup=soup,
                    depth=depth,
                    status_code=response.status_code,
                    response_time=elapsed,
                )
                self.db.save_page(record)

                if soup is not None:
                    self.html_pages_stored += 1
                    self.total_content_chars += len(record["content"])
                    # Batch-store the complete outgoing-link set in one SQLite operation.
                    # This is much faster for a large full-data crawl than committing
                    # one link at a time.
                    self.db.save_links(final_url, extracted_links)

                accepted = 0
                if soup is not None:
                    for target in extracted_links:
                        # Every HTTP(S) hyperlink is kept in the links table so the DB
                        # preserves the page's outgoing-link graph, even when a target
                        # is outside the focused crawl scope.
                        self.discovered_urls.add(target)

                        valid, reason = is_valid_url(
                            target, config.ALLOWED_DOMAINS, config.BLOCKED_EXTENSIONS
                        )
                        if not valid:
                            self._skip(reason)
                            continue

                        new_depth = depth + 1
                        if new_depth > config.MAX_DEPTH:
                            self._skip("max_depth")
                            continue

                        if self.frontier.add(target, new_depth):
                            accepted += 1
                            self.total_links_queued += 1
                        else:
                            self._skip("duplicate")

                # One commit per crawled page keeps the database durable while avoiding
                # thousands of tiny commits during large crawls.
                self.db.commit()

                title = record["title"] or "(no title)"
                print("-" * 46)
                print(f"[Crawl #{self.pages_crawled:03d}]")
                print(f"Depth : {depth}")
                print(f"URL   : {final_url}")
                print(f"Status: {response.status_code}")
                print(f"Title : {title[:120]}")
                print(f"Content: {len(record['content']):,} chars")
                print(f"Links : {len(extracted_links)} extracted / {accepted} queued")
                print(f"Time  : {elapsed:.2f} sec")
                print(f"Frontier waiting: {len(self.frontier)}")

            return self.summary()
        finally:
            self.db.close()

    def summary(self) -> dict:
        result = {
            "topic": config.TOPIC,
            "seed_urls": len(config.SEED_URLS),
            "pages_crawled": self.pages_crawled,
            "html_pages_stored": self.html_pages_stored,
            "request_attempts": self.request_attempts,
            "redirects_followed": self.redirects_followed,
            "unique_urls_discovered": len(self.discovered_urls),
            "skipped_urls": self.skipped_urls,
            "failed_requests": self.failed_requests,
            "maximum_depth": config.MAX_DEPTH,
            "depth_counts": dict(sorted(self.depth_counts.items())),
            "status_counts": dict(sorted(self.status_counts.items())),
            "redirect_status_counts": dict(sorted(self.redirect_status_counts.items())),
            "skip_reasons": dict(self.skip_reasons.most_common()),
            "frontier_remaining": len(self.frontier),
            "total_links_extracted": self.total_links_extracted,
            "total_links_queued": self.total_links_queued,
            "total_content_chars": self.total_content_chars,
        }

        print("\n" + "=" * 46)
        print(" CRAWLING SUMMARY")
        print("=" * 46)
        print(f"Topic                  : {result['topic']}")
        print(f"Seed URLs              : {result['seed_urls']}")
        print(f"Pages Crawled          : {result['pages_crawled']}")
        print(f"HTML Pages Stored      : {result['html_pages_stored']}")
        print(f"Unique URLs Discovered : {result['unique_urls_discovered']}")
        print(f"Skipped URLs           : {result['skipped_urls']}")
        print(f"Failed Requests        : {result['failed_requests']}")
        print(f"Redirects Followed     : {result['redirects_followed']}")
        print(f"Maximum Depth          : {result['maximum_depth']}")
        for depth in range(result["maximum_depth"] + 1):
            print(f"Depth {depth:<2}                : {result['depth_counts'].get(depth, 0)}")
        for status, count in result["status_counts"].items():
            print(f"HTTP {status:<3}               : {count}")
        for status, count in result["redirect_status_counts"].items():
            print(f"Redirect HTTP {status:<3}      : {count} hop(s)")
        print(f"Links Extracted        : {result['total_links_extracted']}")
        print(f"Links Queued           : {result['total_links_queued']}")
        print(f"Visible Text Stored    : {result['total_content_chars']:,} chars")
        print(f"Frontier Remaining     : {result['frontier_remaining']}")
        print("=" * 46)

        return result
