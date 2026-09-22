SEG301 Assignment 1 - Focused Web Crawler
==========================================

## Thông tin cá nhân

| MSSV | Họ tên |
|---|---|
| CE201234 | Phạm Quỳnh Hương |

## 1. Chủ đề đã chọn

**Topic:** Education

**Domain phụ trách:** Stanford University - `stanford.edu`

**Seed URL:**

```
https://www.stanford.edu/academics/everyone
```

## 2. Cấu hình crawl

Cấu hình lấy từ `config.py`:

| Thiết lập | Giá trị |
|---|---|
| Seed URLs | 1 |
| Allowed domain | 1 (`stanford.edu`, cho phép mọi subdomain) |
| Maximum pages | 100 |
| Maximum depth | 3 |
| Request timeout | 10 giây |
| Base crawl delay | 1 giây |
| Maximum redirects | 5 |
| robots.txt | Bật (`RESPECT_ROBOTS_TXT = True`, `ROBOTS_FAIL_CLOSED = True`) |
| Reset database mỗi lần chạy | Bật (`RESET_DATABASE_ON_START = True`) |

Crawler sẽ đợi lâu hơn mức cấu hình nếu robots.txt của site yêu cầu `Crawl-delay` lớn hơn (thực tế gặp: `facts.stanford.edu` yêu cầu delay ~30 giây).

`stanford.edu` là domain gốc chấp nhận mọi subdomain — thực tế lần crawl gần nhất đã thu thập được dữ liệu từ **44 subdomain khác nhau** (`www.`, `facts.`, `alumni.`, `library.`, `online.`, `engineering.`, `law.`, `ed.`, v.v.), cho thấy hệ thống website của Stanford phân tán nội dung ra rất nhiều subdomain độc lập.

## 3. Chiến lược crawl (BFS)

Dùng Breadth-First Search: `URLFrontier` giữ hàng đợi FIFO, mỗi phần tử là `(url, depth)`. Seed bắt đầu ở depth 0, link tìm thấy từ trang depth *n* được đưa vào hàng đợi ở depth *n+1*, cho tới khi chạm `MAX_DEPTH` hoặc `MAX_PAGES`.

Hai tập hợp chống trùng URL:
- `queued`: URL đang chờ trong frontier
- `visited`: URL đã crawl hoặc đã thử

> *Ghi chú:* phần chi tiết triển khai `URLFrontier`/`FocusedCrawler` nằm trong `crawler.py` và `url_frontier.py` — nếu code của nhóm có thêm cơ chế ưu tiên (priority) hay khác biệt so với BFS thuần, bạn nên chỉnh lại đoạn này cho khớp.

## 4. Quy tắc lọc URL

Một URL chỉ được chấp nhận khi:

- Scheme là `http` hoặc `https`
- Thuộc domain `stanford.edu` (kể cả subdomain)
- Không phải file bị chặn theo `BLOCKED_EXTENSIONS` trong `config.py` (ảnh, CSS, JS, archive, PDF, Office, audio, video, XML/RSS...)
- Độ sâu không vượt `MAX_DEPTH`
- Chưa từng `visited` hoặc đang chờ trong frontier
- `robots.txt` cho phép user-agent của crawler truy cập (thực tế gặp: nhiều bài viết trên `news.stanford.edu` bị chặn bởi robots.txt, ví dụ các trang `/stories/2026/...`, và bị bỏ qua với lý do `robots_disallowed`)

> *Ghi chú:* mục này tui viết dựa trên `config.py` + log console quan sát được (`[SKIP robots_disallowed]`). Nếu `parser.py` có thêm quy tắc chuẩn hoá URL (`normalize_url`) hoặc lọc thêm loại trang nào khác (ví dụ trang search render JS như bên domain MIT), bạn bổ sung/sửa lại đoạn này cho đúng code thật.

## 5. Kiểm soát chất lượng dữ liệu (data quality control)

Dựa trên dữ liệu thực tế trong `crawler.db` sau lần crawl cuối:

- Tổng số dòng trong bảng `pages`: **99** (mọi trạng thái, kể cả lỗi HTTP)
- Số trang có nội dung (`content` không rỗng): **90**
- Trang có status lỗi/không phải HTML (202, 403, 503) vẫn được lưu vào `pages` với `content` rỗng — đúng yêu cầu đề bài là phải ghi nhận đầy đủ các status code gặp phải trong lúc crawl, không riêng gì trang thành công.
- **Không thấy giới hạn cắt độ dài content**: nội dung dài nhất đo được là **30,995 ký tự**, vượt xa ngưỡng 8000 ký tự — khác với cách làm cắt bớt nội dung ở một số domain khác trong nhóm. Nếu `crawler.py` của bạn có chủ đích không giới hạn độ dài, ghi rõ lý do ở đây; nếu đây là thiếu sót, cân nhắc bổ sung.
- **Không thấy bộ lọc trang "ít giá trị"**: có 3 trang được lưu với nội dung rất ngắn (3, 8 và 21 ký tự — ví dụ `pai.stanford.edu/`, `stanfordwho.stanford.edu/`) dù nội dung gần như rỗng. Nếu đề bài yêu cầu loại các trang dưới một ngưỡng ký tự nhất định (như domain MIT trong nhóm áp dụng ngưỡng 100 ký tự), bạn nên kiểm tra lại `crawler.py`/`parser.py` xem có bước lọc này chưa.
- **Chống trùng nội dung**: không phát hiện nhóm nội dung trùng nào trong dữ liệu đã lưu (0 nhóm trùng theo so khớp nội dung chính xác). *(Lưu ý: schema bảng `pages` của domain này không có cột `content_hash` như domain MIT trong nhóm — nếu đề bài yêu cầu chống trùng bằng hash, cần bổ sung cột này và logic kiểm tra hash trước khi lưu.)*

## 6. Xử lý HTTP và lỗi

Trong lần crawl gần nhất, crawler gặp và xử lý các status code:

- HTTP 200 (thành công): 91 trang
- HTTP 202 (Accepted, thường là trang được render động — ví dụ toàn bộ `online.stanford.edu/...`): 7 trang
- HTTP 403 (Forbidden — ví dụ `shop.stanford.edu`): 1 trang
- HTTP 503 (Service Unavailable — ví dụ `events.stanford.edu`): 1 trang
- Redirect: 8 lượt (5 hop HTTP 301, 1 hop HTTP 302, 2 hop HTTP 307), giới hạn tối đa 5 redirect/URL theo `MAX_REDIRECTS`
- Failed Requests (lỗi mạng/timeout): 0

Với response HTTP 200 dạng HTML, crawler trích xuất: URL, domain, title, nội dung text, depth, status code, thời điểm crawl, response time. Với response lỗi hoặc không phải HTML, chỉ metadata được lưu, `content` để rỗng.

## 7. Thiết kế database

Bảng `pages` (theo schema thực tế trong `crawler.db`):

```sql
CREATE TABLE pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT,
    domain TEXT,
    title TEXT,
    content TEXT,
    depth INTEGER,
    status_code INTEGER,
    crawled_at TEXT,
    response_time REAL
);
```

Bảng `links`:

```sql
CREATE TABLE links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_url TEXT,
    target_url TEXT
);
```

> *Ghi chú:* schema này không có cột `content_hash`/index chống trùng như domain khác trong nhóm — xem lại mục 5 phía trên.

## 8. Thống kê crawl

Thống kê tính từ lần chạy thật, ghi ra `data/crawl_summary.txt`:

```text
==============================================
 CRAWLING SUMMARY
==============================================
Topic                  : Education
Seed URLs              : 1
Pages Crawled          : 100
HTML Pages Stored      : 91
Unique URLs Discovered : 2803
Skipped URLs           : 4429
Failed Requests        : 0
Redirects Followed     : 8
Maximum Depth          : 3
Depth 0                 : 1
Depth 1                 : 82
Depth 2                 : 17
Depth 3                 : 0
HTTP 200               : 91
HTTP 202               : 7
HTTP 403               : 1
HTTP 503               : 1
Redirect HTTP 301      : 5 hop(s)
Redirect HTTP 302      : 1 hop(s)
Redirect HTTP 307      : 2 hop(s)
Links Extracted        : 6844
Links Queued           : 2488
Visible Text Stored    : 678,709 chars
Frontier Remaining     : 2316
==============================================
```

Đối chiếu với `crawler.db`:

- Tổng số trang lưu trong DB: 99 (99/100 trang crawl có bản ghi trong `pages`)
- Số trang có nội dung thực: 90
- Độ dài content trung bình (trang có nội dung): ~7,519 ký tự
- Độ dài content nhỏ nhất: 3 ký tự (`pai.stanford.edu/`, HTTP 200 nhưng nội dung gần như rỗng — xem mục 5)
- Độ dài content lớn nhất: 30,995 ký tự (`www.stanford.edu/about/history`)
- Số nhóm nội dung trùng: 0
- Số dòng trong bảng `links`: 6,794
- Số subdomain khác nhau đã crawl được: 44

Crawl dừng do chạm `MAX_PAGES = 100`, không phải do frontier rỗng — Frontier Remaining: 2316 cho thấy vẫn còn rất nhiều URL hợp lệ chưa kịp crawl.

`facts.stanford.edu` yêu cầu `Crawl-delay` khoảng 30 giây trong robots.txt, khiến crawler phải đợi lâu hơn hẳn phần lớn subdomain khác (mặc định 1 giây) mỗi khi truy cập domain này.

## 9. Cấu trúc project

```
Assignment1/
├── main.py
├── crawler.py
├── url_frontier.py
├── parser.py
├── database.py
├── config.py
├── requirements.txt
├── README.md
├── run.bat
├── analyze_quality.py
└── data/
    ├── crawler.db
    └── crawl_summary.txt
```

## 10. Cách chạy

```
python -m pip install -r requirements.txt
python main.py
```

Chạy lệnh từ trong thư mục `Assignment1`.

Kiểm tra chất lượng dữ liệu sau khi crawl:

```
python analyze_quality.py data/crawler.db
```
