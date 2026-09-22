# SEG301 Assignment 1 - Focused Web Crawler

| CE190248 | Nguyễn Việt Phương |

The submission also includes `../GroupName.csv` with the same five members.

## 1. Selected topic

**Topic:** Education

**This is the requested one-link variant.** It starts from exactly one Stanford Engineering seed page and crawls only the `engineering.stanford.edu` host.

> Important for the final group submission: the original assignment requires at least 2 domains. Therefore this one-link package is suitable as a single-site/member crawl or test variant. If it is submitted as the entire group assignment by itself, another allowed Education domain must be added to satisfy that requirement.

## 2. Seed URL

```text
https://engineering.stanford.edu/students-academics/academics/online-learning
```

Only this URL is inserted into the initial URL Frontier, so there is exactly **1 depth-0 seed**.

## 3. Crawl scope

The crawler follows links discovered from the seed using BFS, but only URLs on:

```text
engineering.stanford.edu
```

are allowed to enter the crawl frontier.

HTTP(S) hyperlinks pointing outside this host are still saved to the SQLite `links` table so the outgoing-link graph is preserved, but those external pages are not downloaded.

## 4. Crawling configuration

| Setting | Value |
|---|---:|
| Seed URLs | 1 |
| Allowed domains/hosts | 1 |
| Maximum pages | 1500 |
| Maximum depth | 4 |
| Request timeout | 15 seconds |
| Base crawl delay | 1 second |
| Maximum redirects | 5 |
| robots.txt | Enabled |

This configuration is intentionally larger than the earlier 100-page test so the crawler can progress through depth 1, depth 2, depth 3 and depth 4 when enough in-scope links exist.

The crawler remains bounded: it stops when `MAX_PAGES` is reached or the URL Frontier becomes empty.

## 5. Crawling strategy

The crawler uses **Breadth-First Search (BFS)** with `collections.deque`.

Each frontier item is:

```python
(url, depth)
```

Depth meaning:

```text
Depth 0 = the single Stanford Online Learning seed
Depth 1 = pages linked directly from the seed
Depth 2 = pages linked from depth-1 pages
Depth 3 = pages linked from depth-2 pages
Depth 4 = pages linked from depth-3 pages
```

Duplicate requests are prevented with:
- URL normalization;
- a `queued` set for URLs already waiting in the frontier;
- a `visited` set for URLs already processed/requested.

## 6. URL extraction and filtering

For every parsed HTML page, BeautifulSoup extracts every `<a href="...">` HTTP(S) hyperlink.

Relative links are converted to absolute URLs with `urljoin()`.

Before a URL is queued for crawling, it must:
1. use HTTP or HTTPS;
2. belong to `engineering.stanford.edu`;
3. not be a blocked non-HTML resource such as image, CSS, JavaScript, ZIP, PDF, Office document, audio or video;
4. be at or below `MAX_DEPTH`;
5. not already be queued/visited;
6. be allowed by `robots.txt`.

Common tracking query parameters such as `utm_*`, `fbclid`, `gclid` and `_rsc` are removed during URL normalization. Other query parameters are preserved because they may change page content.

## 7. HTTP and redirect handling

The crawler uses `requests.Session` and does not assume every request returns HTTP 200.

Redirects (301/302/303/307/308) are followed manually. Before following each redirect target, the crawler verifies:
- allowed host;
- blocked file type;
- `robots.txt` permission;
- redirect loop prevention;
- redirect limit.

Redirect hops are tracked separately and do not consume the `MAX_PAGES` budget. The final non-redirect response is counted as the crawled page.

Network errors such as timeouts and connection errors are caught without stopping the entire crawl.

## 8. Full-data extraction

For every successful HTML page the database stores:
- final URL;
- domain;
- complete page title;
- complete visible text content (not truncated);
- BFS depth;
- final HTTP status code;
- crawl timestamp;
- response time.

Non-visible elements such as `script`, `style`, `noscript`, `template` and `svg` are removed before text extraction.

All extracted HTTP(S) outgoing hyperlinks are stored in the `links` table, including external hyperlinks. Only in-scope Stanford Engineering URLs are crawled.

### SQLite performance optimization

This one-link full-data version is optimized for a much larger run:
- link rows from one page are inserted with `executemany()`;
- SQLite commits once per crawled page instead of once per hyperlink;
- WAL journal mode and `synchronous=NORMAL` are enabled;
- indexes are created for page domain/depth/status and link source/target.

This keeps `crawler.db` responsive even when thousands of links are stored.

## 9. Database design

Database file:

```text
data/crawler.db
```

### `pages`

```sql
CREATE TABLE pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE,
    domain TEXT,
    title TEXT,
    content TEXT,
    depth INTEGER,
    status_code INTEGER,
    crawled_at TEXT,
    response_time REAL
);
```

### `links`

```sql
CREATE TABLE links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_url TEXT,
    target_url TEXT
);
```

A unique `(source_url, target_url)` index prevents duplicate edges.

## 10. Crawling statistics

After the run finishes, the crawler automatically generates the summary in:

```text
data/crawl_summary.txt
```

and inserts the same real statistics into this README.

### Final crawl result (auto-updated)

<!-- AUTO_CRAWL_RESULTS_START -->

```text
Run `python main.py` once to generate the final crawling statistics.
```

<!-- AUTO_CRAWL_RESULTS_END -->

The statistics are generated from the real run, not hard-coded.

## 11. Project structure

```text
GroupX_Assignement1/
├── GroupName.csv
└── Assignment1/
    ├── main.py
    ├── crawler.py
    ├── url_frontier.py
    ├── parser.py
    ├── database.py
    ├── config.py
    ├── requirements.txt
    ├── README.md
    ├── run.bat
    └── data/
        ├── crawler.db
        └── crawl_summary.txt
```

## 12. How to run

On Windows, double-click:

```text
run.bat
```

or run:

```bash
python -m pip install -r requirements.txt
python main.py
```

Because `MAX_PAGES = 1500` and the crawler politely waits between requests, a full run can take a significant amount of time. This is expected.

## 13. Before submission

1. Run the crawler until the `CRAWLING SUMMARY` appears.
2. Verify `data/crawler.db` contains `pages` and `links` data.
3. Verify `data/crawl_summary.txt` contains the latest statistics.
4. Verify this README has been auto-updated with the same statistics.
5. Remove any `__pycache__` folder before zipping.
6. If this is used as the complete group assignment, merge/add a second permitted Education domain because the assignment itself requires at least 2 domains.
