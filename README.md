# SEG301 Assignment 1 - Focused Web Crawler

## Thông tin cá nhân

| MSSV | Họ tên |
|---|---|
| CE200605 | Bùi Hữu Lộc |

## 1. Chủ đề đã chọn

**Topic:** Education

**Domain phụ trách:** MIT OpenCourseWare (`ocw.mit.edu`)

**Seed URL (1 seed):**

```text
https://ocw.mit.edu/courses/
```

Crawler chỉ bắt đầu từ trang danh mục khoá học của MIT OpenCourseWare và chỉ crawl trong domain `ocw.mit.edu`.

## 2. Cấu hình crawl

Cấu hình lấy từ `config.py`:

| Thiết lập | Giá trị |
|---|---:|
| Seed URLs | 1 |
| Allowed domains | 1 (`ocw.mit.edu`) |
| Maximum pages | 30 |
| Maximum depth | 2 |
| Request timeout | 10 giây |
| Base crawl delay | 1 giây |
| robots.txt | Bật |

Crawler sẽ đợi lâu hơn nếu `robots.txt` của site yêu cầu `Crawl-delay` lớn hơn mức cấu hình. Điều này theo đúng nguyên tắc crawl-politeness của bài giảng SEG301: `Request -> Wait -> Request`.

## 3. Chiến lược crawl (BFS)

Crawler dùng **Breadth-First Search (BFS)**. `URLFrontier` cài đặt bằng `collections.deque` làm hàng đợi FIFO. Mỗi phần tử trong frontier là `(url, depth)`.

Seed bắt đầu ở depth `0`. Link tìm thấy từ trang depth 0 vào hàng đợi ở depth `1`, cứ thế cho tới khi chạm `MAX_DEPTH`.

Hai set chống trùng:
- `queued`: URL đang chờ trong frontier
- `visited`: URL đã crawl/đã thử

Luồng xử lý theo đúng pipeline của đề bài: Seed URLs -> URL Frontier -> Crawl -> Store Document -> Extract Links -> Filter -> Frontier -> Repeat.

## 4. Quy tắc lọc URL

Link thô được chuyển thành URL tuyệt đối bằng `urljoin()`, sau đó chuẩn hoá (`normalize_url`) trước khi lọc.

Một URL chỉ được chấp nhận vào frontier khi:
1. Scheme là `http` hoặc `https`.
2. Thuộc domain `ocw.mit.edu`.
3. Không phải file bị chặn (ảnh, CSS, JS, archive, PDF, Office, audio, video...).
4. Độ sâu không vượt quá `MAX_DEPTH`.
5. Chưa từng `visited` hoặc đang chờ trong frontier.
6. `robots.txt` cho phép user-agent của crawler truy cập.

`normalize_url()` thực hiện chuẩn hoá bảo thủ (conservative):
- lowercase scheme và hostname;
- bỏ fragment (`#section`);
- bỏ cổng mặc định của HTTP/HTTPS;
- bỏ dấu `/` cuối trừ path gốc;
- bỏ các query tracking phổ biến (`utm_*`, `fbclid`, `gclid`, `_rsc`);
- giữ nguyên các query khác vì có thể làm thay đổi nội dung trang.

## 5. Xử lý HTTP và lỗi

Trang được tải bằng `requests.Session`, không giả định luôn trả về HTTP 200. Crawler xử lý và ghi nhận các response HTTP hoàn chỉnh như 200, 403, 404, 500. Lỗi mạng (timeout, connection error) được bắt bằng `requests.RequestException`, tính vào số request thất bại, và **không làm dừng toàn bộ crawl**.

Với response HTTP 200 dạng HTML, BeautifulSoup trích xuất:
- URL
- Domain
- Page title
- Nội dung text hiển thị
- Crawl depth
- HTTP status code
- Thời điểm crawl
- Response time

Các thẻ `script`, `style`, `noscript`, `template`, `svg` bị loại bỏ trước khi lấy text.

## 6. Thiết kế database

Database: `data/crawler_Loc.db`.

### Bảng `pages`

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

### Bảng `links`

```sql
CREATE TABLE links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_url TEXT,
    target_url TEXT
);
```

Index unique trên `(source_url, target_url)` tránh lưu trùng cùng một quan hệ link nhiều lần.

## 7. Kết quả crawl (chạy thật ngày gần nhất)

Thống kê được tính tự động từ lần chạy thật, ghi ra `data/crawl_summary_loc.txt`:

```text
==============================================
 CRAWLING SUMMARY
==============================================
Topic                  : Education
Seed URLs              : 1
Pages Crawled          : 30
Unique URLs Discovered : 391
Skipped URLs           : 537
Failed Requests        : 0
Maximum Depth          : 2
Depth 0                : 1
Depth 1                : 3
Depth 2                : 26
HTTP 200               : 30
Frontier Remaining     : 118
==============================================
```

Crawl dừng do chạm **MAX_PAGES = 30**, không phải do frontier rỗng — `Frontier Remaining: 118` cho thấy vẫn còn rất nhiều URL hợp lệ chưa kịp crawl. Đây là một trong hai điều kiện dừng hợp lệ theo đề bài (`MAX_PAGES is reached`). Toàn bộ 30 trang crawl được đều trả về HTTP 200, không có request thất bại nào.

## 8. Cấu trúc project

```text
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
└── data/
    ├── crawler_Loc.db
    └── crawl_summary_loc.txt
```

## 9. Cách chạy

### Windows - dễ nhất

Double-click:

```text
run.bat
```

### Command line

```bash
python -m pip install -r requirements.txt
python main.py
```

