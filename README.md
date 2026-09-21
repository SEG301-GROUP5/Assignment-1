=======
# SEG301 Assignment 1 - Focused Web Crawler

## Thông tin cá nhân

| MSSV | Họ tên |
|---|---|
| CE200153 | Nguyễn Thị Thảo Ngân |

## 1. Chủ đề đã chọn

**Topic:** Education

**Domain phụ trách:** MIT OpenCourseWare - `ocw.mit.edu`

**Seed URL (1/5 seed của cả nhóm):**

```text
https://ocw.mit.edu/
```

## 2. Cấu hình crawl

Cấu hình lấy từ `config.py`:

| Thiết lập | Giá trị |
|---|---:|
| Seed URLs | 1 |
| Allowed domain | 1 (`ocw.mit.edu`) |
| Maximum pages | 100 |
| Maximum depth | 3 |
| Request timeout | 10 giây |
| Base crawl delay | 1 giây |
| robots.txt | Bật |

Crawler sẽ đợi lâu hơn nếu `robots.txt` của site yêu cầu `Crawl-delay` lớn hơn mức cấu hình.

## 3. Chiến lược crawl (BFS)

Dùng **Breadth-First Search**, `URLFrontier` cài bằng `collections.deque` làm hàng đợi FIFO. Mỗi phần tử trong frontier là `(url, depth)`.

Seed bắt đầu ở depth `0`. Link tìm thấy từ trang depth 0 vào hàng đợi ở depth `1`, cứ thế cho tới khi chạm `MAX_DEPTH`.

Hai set chống trùng:
- `queued`: URL đang chờ trong frontier
- `visited`: URL đã crawl/đã thử

## 4. Quy tắc lọc URL

Link thô được chuẩn hoá về URL tuyệt đối bằng `urljoin()`, sau đó chuẩn hoá tiếp (`normalize_url`) trước khi lọc.

Một URL chỉ được chấp nhận khi:
1. Scheme là `http` hoặc `https`
2. Thuộc domain `ocw.mit.edu` (kể cả subdomain)
3. Không phải file bị chặn (ảnh, CSS, JS, archive, PDF, Office, audio, video...)
4. **Không phải trang kết quả tìm kiếm `/search?...`** — trang này render bằng JavaScript phía client, `requests`/`BeautifulSoup` chỉ nhận được HTML rỗng, nên bị chặn ngay từ bước lọc URL thay vì phí 1 request rồi mới phát hiện rỗng
5. Độ sâu không vượt `MAX_DEPTH`
6. Chưa từng `visited` hoặc đang chờ trong frontier
7. `robots.txt` cho phép user-agent của crawler truy cập

`normalize_url()` chuẩn hoá: lowercase scheme/host, bỏ fragment `#...`, bỏ port mặc định, bỏ trailing slash (trừ path gốc), bỏ query tracking (`utm_*`, `fbclid`, `_rsc`...), giữ nguyên các query khác vì có thể ảnh hưởng nội dung trang.

## 5. Kiểm soát chất lượng dữ liệu (data quality control)

Bên cạnh lọc URL, crawler còn lọc **nội dung** trước khi lưu vào database. Các bước này chỉ áp dụng cho trang **tải thành công dạng HTML** (`soup is not None`, tức HTTP 200 + Content-Type là HTML):

**a) Loại bỏ boilerplate:** trước khi lấy text, các thẻ `nav`, `footer`, `header`, `aside`, `form`, `button`, `script`, `style`, `noscript`, `template`, `svg` bị loại khỏi HTML. Ưu tiên lấy text trong `<main>`/`<article>` nếu trang có khai báo, thay vì lấy toàn bộ `<body>` (vốn lẫn menu/footer lặp lại ở mọi trang).

**b) Loại trang ít giá trị:** nếu nội dung sau khi làm sạch còn dưới 100 ký tự, trang bị coi là không có giá trị (trang login, trang rỗng, trang redirect...) và không lưu vào `pages` (vẫn tính vào `pages_crawled` và vẫn trích link để tiếp tục BFS). Bộ lọc này **chỉ áp dụng cho trang tải thành công (HTTP 200, HTML)** — trang trả về lỗi HTTP (403/404/500) vẫn được lưu vào `pages` với `content` rỗng, vì đề bài yêu cầu ghi nhận đầy đủ các status code gặp phải trong quá trình crawl (Task 3 - crawler phải xử lý và không giả định luôn HTTP 200), không riêng gì trang tải thành công.

**c) Chống trùng nội dung:** mỗi trang được hash bằng SHA-256 (`content_hash`). Nếu hash đã tồn tại trong DB (2 URL khác nhau nhưng cùng nội dung), trang sau bị bỏ qua khi lưu.

**d) Giới hạn độ dài:** nội dung lưu vào DB bị cắt tối đa 8000 ký tự để tránh phình database với các trang liệt kê quá dài.

### Kết quả đo được (chạy thật ngày crawl gần nhất)

```text
==============================================
 CRAWLING SUMMARY
==============================================
Topic                  : Education
Seed URLs              : 1
Pages Crawled          : 100
Unique URLs Discovered : 1184
Skipped URLs           : 5969
Failed Requests        : 0
Maximum Depth          : 3
Depth 0                : 1
Depth 1                : 62
Depth 2                : 37
HTTP 200               : 99
HTTP 403               : 1

Skip reasons breakdown:
  duplicate               : 3555
  outside_allowed_domain  : 1605
  js_rendered_search_page : 770
  blocked_file_type       : 24
  duplicate_content       : 14
  low_content             : 1
Frontier Remaining     : 609
==============================================

Tổng số trang lưu trong DB      : 85
Độ dài content trung bình       : 4120 ký tự
Độ dài content nhỏ nhất         : 0 ký tự (trang HTTP 403, không đi qua bộ lọc content - xem mục 5b)
Độ dài content lớn nhất         : 8000 ký tự (đạt ngưỡng cắt)
Trang gần như rỗng (<50 ký tự)  : 1 (1.2%) - chính là trang HTTP 403 nói trên
Nhóm nội dung trùng còn sót     : 0 nhóm

Phân bố theo depth (chỉ trang đã lưu vào pages):
  Depth 0: 1
  Depth 1: 61
  Depth 2: 23

Phân bố status code (chỉ trang đã lưu vào pages):
  HTTP 200: 84
  HTTP 403: 1
```

Crawl dừng do chạm **MAX_PAGES = 100**, không phải do frontier rỗng — `Frontier Remaining: 609` cho thấy vẫn còn rất nhiều URL hợp lệ chưa kịp crawl. Đây là 1 trong 2 điều kiện dừng hợp lệ theo đề bài (`MAX_PAGES is reached`).

`js_rendered_search_page: 770` cho thấy phần lớn lượng skip đến từ việc chặn sớm các URL `/search?...` — nếu không có bước lọc này, 770 request đó sẽ tiêu tốn ngân sách `MAX_PAGES`, khiến crawler chỉ tải được các trang search rỗng thay vì các trang course có nội dung thật.

`duplicate: 3555` phản ánh cấu trúc điều hướng lặp lại nhiều của `ocw.mit.edu` (menu, breadcrumb... trỏ tới cùng vài chục URL cốt lõi từ hàng trăm trang khác nhau).

## 6. Xử lý HTTP và lỗi

Tải trang bằng `requests.Session`, có `User-Agent` riêng và timeout. Không giả định luôn trả về HTTP 200 — crawler ghi nhận và xử lý cả 200, 403, 404, 500 (kết quả thực tế gặp: 99 trang 200, 1 trang 403). Lỗi mạng (timeout, connection error) được bắt bằng `requests.RequestException`, tính vào `failed_requests`, và **không làm dừng toàn bộ chương trình** (lần chạy này: 0 lỗi mạng).

Với response HTTP 200 dạng HTML, BeautifulSoup trích xuất: URL, domain, title, nội dung text (đã lọc boilerplate), depth, status code, thời điểm crawl, response time, và content hash. Với response lỗi (403/404/500) hoặc không phải HTML, chỉ metadata (URL, status code, depth...) được lưu, `content` để rỗng.

Console output trên Windows được ép về UTF-8 (`sys.stdout.reconfigure`) vì một số trang OCW có tiêu đề chứa ký tự ngoài bảng mã mặc định `cp1252` của terminal (ví dụ tiếng Thổ Nhĩ Kỳ), nếu không xử lý sẽ làm crash chương trình giữa chừng khi `print()` tiêu đề.

## 7. Thiết kế database

### Bảng `pages`

```sql
CREATE TABLE pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE,
    domain TEXT,
    title TEXT,
    content TEXT,
    content_hash TEXT,
    depth INTEGER,
    status_code INTEGER,
    crawled_at TEXT,
    response_time REAL
);
CREATE INDEX idx_pages_content_hash ON pages(content_hash);
```

`content_hash` dùng để phát hiện 2 URL khác nhau nhưng cùng nội dung (xem mục 5c).

### Bảng `links`

```sql
CREATE TABLE links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_url TEXT,
    target_url TEXT
);
CREATE UNIQUE INDEX idx_links_unique ON links(source_url, target_url);
```

Index unique tránh lưu trùng cùng 1 quan hệ link nhiều lần.

## 8. Thống kê crawl

Thống kê tính từ lần chạy thật, ghi ra `data/crawl_summary_ngan.txt`, gồm: số trang crawl, số URL duy nhất phát hiện, số URL bị skip (kèm breakdown theo từng lý do), số request thất bại, phân bố theo depth, phân bố theo HTTP status, số URL còn lại trong frontier. Số liệu tính tự động từ các Counter trong lúc chạy, không hard-code.

## 9. Cấu trúc project

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
├── analyze_quality.py
└── data/
    ├── crawler_ngan.db
    └── crawl_summary_ngan.txt
```

## 10. Cách chạy

```bash
python -m pip install -r requirements.txt
python main.py
```

Chạy lệnh từ trong thư mục `Assignment1`.

Kiểm tra chất lượng dữ liệu sau khi crawl:

```bash
python analyze_quality.py data/crawler_ngan.db
```
>>>>>>> db640f6 (Ngan - Initial commit)
