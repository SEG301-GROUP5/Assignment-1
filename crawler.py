"""Complete focused web crawler for the SEG301 assignment."""
from __future__ import annotations

import time
from collections import Counter
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

import config
from database import CrawlerDatabase
from parser import (
    extract_links,
    extract_page_information,
    is_valid_url,
    normalize_url,
    parse_html,
)
from url_frontier import URLFrontier


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
            }
        )

        self.robots_cache: dict[str, RobotFileParser] = {}
        self.robots_delay_cache: dict[str, float] = {}
        self.last_request_at: dict[str, float] = {}

        self.discovered_urls: set[str] = set()
        self.pages_crawled = 0
        self.request_attempts = 0
        self.failed_requests = 0
        self.skipped_urls = 0
        self.skip_reasons: Counter[str] = Counter()
        self.status_counts: Counter[int] = Counter()
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

        try:
            response = self.session.get(robots_url, timeout=config.REQUEST_TIMEOUT)
            if response.status_code == 200:
                rp.parse(response.text.splitlines())
            elif response.status_code in {401, 403}:
                # Conservative interpretation: explicit access denial means no crawling.
                rp.parse(["User-agent: *", "Disallow: /"])
            elif response.status_code == 404:
                # No robots file found -> no robots restrictions discovered.
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
        rp = self._get_robots(url)
        return rp.can_fetch(config.USER_AGENT, url)

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
                time.sleep(remaining)

    def _mark_request_time(self, url: str) -> None:
        self.last_request_at[self._base_url(url)] = time.monotonic()

    def _skip(self, reason: str) -> None:
        self.skipped_urls += 1
        self.skip_reasons[reason] += 1

    def _print_configuration(self) -> None:
        print("=" * 46)
        print(" FOCUSED WEB CRAWLER")
        print("=" * 46)
        print(f"Topic          : {config.TOPIC}")
        print(f"Seed URLs      : {len(config.SEED_URLS)}")
        for i, seed in enumerate(config.SEED_URLS, start=1):
            print(f"  {i}. {seed}")
        print("Allowed Domains:")
        for domain in config.ALLOWED_DOMAINS:
            print(f"  - {domain}")
        print(f"Maximum Depth  : {config.MAX_DEPTH}")
        print(f"Maximum Pages  : {config.MAX_PAGES}")
        print(f"Request Timeout: {config.REQUEST_TIMEOUT} seconds")
        print(f"Base Crawl Delay: {config.CRAWL_DELAY} second(s)")
        print(f"Respect robots.txt: {config.RESPECT_ROBOTS_TXT}")
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

                if not self._robots_allows(url):
                    self.frontier.mark_visited(url)
                    self._skip("robots_disallowed")
                    print(f"[SKIP robots.txt] {url}")
                    continue

                # Mark before requesting so a failure cannot cause repeated re-queuing.
                self.frontier.mark_visited(url)
                self._respect_delay(url)

                self.request_attempts += 1
                started = time.perf_counter()
                try:
                    response = self.session.get(
                        url,
                        timeout=config.REQUEST_TIMEOUT,
                        allow_redirects=True,
                    )
                    elapsed = time.perf_counter() - started
                    self._mark_request_time(url)
                except requests.RequestException as exc:
                    self._mark_request_time(url)
                    self.failed_requests += 1
                    print(f"[FAILED] Depth {depth} | {url} | {exc}")
                    continue

                # One completed HTTP response counts as a crawled page, matching the
                # assignment's summary where status-code counts contribute to total pages.
                self.pages_crawled += 1
                self.status_counts[response.status_code] += 1
                self.depth_counts[depth] += 1

                final_url = normalize_url(response.url)
                content_type = response.headers.get("Content-Type", "").lower()
                soup = None
                extracted_links: list[str] = []

                if response.status_code == 200 and "html" in content_type:
                    soup = parse_html(response.text)
                    extracted_links = extract_links(final_url, soup)
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

                # Store the link graph and decide which links enter the frontier.
                accepted = 0
                if soup is not None:
                    for target in extracted_links:
                        self.discovered_urls.add(target)
                        self.db.save_link(final_url, target)

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

                        # Check robots before enqueueing so disallowed pages never enter the queue.
                        if not self._robots_allows(target):
                            self._skip("robots_disallowed")
                            continue

                        if self.frontier.add(target, new_depth):
                            accepted += 1
                        else:
                            self._skip("duplicate")

                title = record["title"] or "(no title)"
                print("-" * 46)
                print(f"[Crawl #{self.pages_crawled:03d}]")
                print(f"Depth : {depth}")
                print(f"URL   : {final_url}")
                print(f"Status: {response.status_code}")
                print(f"Title : {title[:120]}")
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
            "request_attempts": self.request_attempts,
            "unique_urls_discovered": len(self.discovered_urls),
            "skipped_urls": self.skipped_urls,
            "failed_requests": self.failed_requests,
            "maximum_depth": config.MAX_DEPTH,
            "depth_counts": dict(sorted(self.depth_counts.items())),
            "status_counts": dict(sorted(self.status_counts.items())),
            "skip_reasons": dict(self.skip_reasons.most_common()),
            "frontier_remaining": len(self.frontier),
        }

        print("\n" + "=" * 46)
        print(" CRAWLING SUMMARY")
        print("=" * 46)
        print(f"Topic                  : {result['topic']}")
        print(f"Seed URLs              : {result['seed_urls']}")
        print(f"Pages Crawled          : {result['pages_crawled']}")
        print(f"Unique URLs Discovered : {result['unique_urls_discovered']}")
        print(f"Skipped URLs           : {result['skipped_urls']}")
        print(f"Failed Requests        : {result['failed_requests']}")
        print(f"Maximum Depth          : {result['maximum_depth']}")
        for depth, count in result["depth_counts"].items():
            print(f"Depth {depth:<2}                : {count}")
        for status, count in result["status_counts"].items():
            print(f"HTTP {status:<3}               : {count}")
        print(f"Frontier Remaining     : {result['frontier_remaining']}")
        print("=" * 46)

        return result
