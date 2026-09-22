# SEG301 Assignment 1 — Focused Web Crawler (Member H)

## Thành viên

| MSSV | Họ tên | Phụ trách |
|---|---|---|
| CE200567 | Nguyễn Thanh Phương | Seed `https://ocw.mit.edu/search/` |

**Nhóm:** gồm 5 thành viên — danh sách đầy đủ xem ở `../GroupName.csv`.

## 1. Chủ đề đã chọn

**Topic:** Education

**Domain phụ trách:** MIT OpenCourseWare — `ocw.mit.edu`

**Seed URL (2/5 seed của cả nhóm):**

```text
https://ocw.mit.edu/search/
Seed này khác 4 seed còn lại của nhóm — tập trung vào trang tìm kiếm của
MIT OpenCourseWare, nhằm khảo sát nhánh "search interface" của hệ thống
giáo dục mở MIT. Khác với các seed dạng trang chủ/danh mục, seed /search/
tạo ra một đồ thị link đặc trưng: phần lớn URL sinh ra là các truy vấn
tìm kiếm (?q=, ?t=, ?l=) và các trang course detail được phát hiện
từ các truy vấn đó.

2. Cấu hình crawl
Lấy từ config.py:

Thiết lập	Giá trị
Seed URLs	1
Allowed domain	1 (ocw.mit.edu, gồm subdomain)
Maximum pages	150
Maximum depth	3 (bắt đầu từ depth 1)
Request timeout	10 giây
Base crawl delay	1 giây
Maximum redirects	5
robots.txt	Bật
Reset DB khi khởi động	Tắt
DB path	data/crawler_h.db
Crawler sẽ đợi lâu hơn nếu robots.txt của MIT OCW yêu cầu Crawl-delay
lớn hơn 1 giây. Trong lần chạy thực tế, delay quan sát được dao động
0.2 – 1.0 giây tuỳ trang, do crawler luôn lấy giá trị lớn hơn giữa
CRAWL_DELAY cấu hình và Crawl-delay trong robots.txt.

3. Chiến lược crawl (BFS)
Dùng Breadth-First Search, URLFrontier cài bằng collections.deque (FIFO).

Mỗi phần tử frontier là tuple (url, depth).

Seed /search/ được đẩy vào frontier ở depth 1 (không dùng depth 0).

Link tìm thấy từ trang depth 1 → depth 2.

Link từ depth 2 → depth 3, chạm MAX_DEPTH = 3.

Hai set chống trùng:

queued: URL đang chờ trong frontier.

visited: URL đã crawl hoặc đã thử crawl.

Đặc trưng của seed /search/: trang search chỉ có ~6 link tĩnh. Khi crawl,
crawler phát hiện trang chủ (/) trong số đó — và trang chủ có 172 link,
trong đó có rất nhiều URL /search/?q=... (truy vấn theo tên giáo sư) và
/search/?t=... (truy vấn theo chủ đề). Vì rule lọc mới cho phép các URL
này đi qua, frontier nhanh chóng chứa hàng trăm URL depth 3.

4. Quy tắc lọc URL
Link thô được urljoin() về URL tuyệt đối, sau đó chuẩn hoá tiếp bằng
normalize_url().

Một URL chỉ được chấp nhận khi:

Scheme là http hoặc https.

Thuộc ocw.mit.edu (kể cả subdomain).

Không phải file bị chặn (ảnh, CSS, JS, archive, PDF, Office, audio, video...).

Không phải trang search có query phân trang / sắp xếp / view —
cụ thể là URL khớp mẫu /search + có một trong các query page, p,
sort, view, format. Đây là các truy vấn render bằng JS phía client,
requests + BeautifulSoup chỉ nhận được HTML rỗng. Các query khác
(?q=, ?t=, ?l=) vẫn được phép đi qua — vì trong lần khảo sát
thực tế, các trang search của MIT OCW vẫn chứa link course hữu ích
trong HTML tĩnh.

Depth không vượt MAX_DEPTH = 3.

Chưa visited và chưa queued.

robots.txt cho phép user-agent crawl.

normalize_url() thực hiện:

lowercase scheme + hostname;

bỏ fragment #...;

bỏ port mặc định (80/443);

giữ nguyên trailing slash (quan trọng vì MIT OCW canonicalize
/about → /about/ bằng HTTP 301, nếu strip slash sẽ tạo redirect giả);

bỏ query tracking (utm_*, fbclid, _rsc, ...);

giữ các query khác vì có thể ảnh hưởng nội dung trang.

5. Kiểm soát chất lượng dữ liệu
Áp dụng cho các trang tải thành công dạng HTML (HTTP 200 + Content-Type là HTML):

Loại bỏ boilerplate: xoá script, style, noscript, template, svg
trước khi lấy visible text.

Giới hạn độ dài lưu DB: content bị cắt tối đa 8000 ký tự để tránh
phình DB bởi các trang listing dài (ví dụ trang chủ có tới 457,255 chars
text thô — nếu không cắt sẽ chiếm dung lượng lớn vô ích).

Trang lỗi HTTP (403/404/500): vẫn được lưu vào pages với content = "",
vì đề bài yêu cầu ghi nhận đầy đủ HTTP status gặp phải. Trong lần chạy này
không gặp trang lỗi nào (100% HTTP 200).

Trang không phải HTML: chỉ lưu metadata, content rỗng.

6. Xử lý HTTP và lỗi
Dùng requests.Session với User-Agent riêng và timeout.

Không giả định HTTP 200 — ghi nhận và lưu cả 200, 403, 404, 500.

Redirect (301/302/303/307/308) được xử lý an toàn, từng hop một:
mỗi target được normalize, kiểm tra domain + file-type + robots trước khi follow.

Redirect hop không tính vào MAX_PAGES — chỉ trang cuối cùng dạng
non-redirect mới tính là "crawled page". Cách này tránh việc các URL redirect-heavy
chiếm mất ngân sách page.

Lỗi mạng (timeout, connection error) bắt bằng requests.RequestException,
cộng vào failed_requests, không dừng toàn bộ crawler.

Với HTTP 200 dạng HTML, BeautifulSoup trích xuất:
url, domain, title, content (đã lọc boilerplate), depth, status_code,
crawled_at, response_time.

Console output trên Windows được ép về UTF-8 để tránh crash khi một số trang OCW
có tiêu đề chứa ký tự ngoài bảng mã mặc định cp1252 của terminal (ví dụ
tiêu đề İleri Çalışmalar từ trang /stories/ileri-.../).

7. Thiết kế database
DB: data/crawler_h.db

sql
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

CREATE TABLE links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_url TEXT,
    target_url TEXT
);

CREATE UNIQUE INDEX idx_links_unique ON links(source_url, target_url);
pages — mỗi URL đã crawl = 1 row, chứa metadata + visible text.

links — cạnh có hướng source_url → target_url, index UNIQUE chống trùng
cùng một quan hệ link bị lưu nhiều lần.

8. Thống kê crawl (chạy thật)
text
==============================================
 CRAWLING SUMMARY
==============================================
Topic                  : Education
Seed URLs              : 1
Pages Crawled          : 146
HTML Pages Stored      : 146
Unique URLs Discovered : 1007
Skipped URLs           : 2901
Failed Requests        : 0
Redirects Followed     : 4
Maximum Depth          : 3
Depth 1                 : 1
Depth 2                 : 2
Depth 3                 : 143
HTTP 200               : 146
Redirect HTTP 301      : 4 hop(s)
Links Extracted        : 3046
Links Queued           : 145
Visible Text Stored    : 1,371,676 chars
Frontier Remaining     : 0
==============================================
Nhận xét về phân bố depth
Phân bố Depth 1: 1, Depth 2: 2, Depth 3: 143 là đặc trưng của seed search,
không phải lỗi cấu hình:

Depth 1 chỉ có 1 URL — chính là seed /search/.

Depth 2 có 2 URL — trang chủ / và một trang phụ được seed trỏ tới.

Depth 3 có 143 URL — phần lớn là các trang course detail và truy vấn
tìm kiếm được phát hiện từ trang chủ.

Nguyên nhân: seed /search/ chỉ sinh ~6 link, nhưng trong đó có trang chủ /,
và trang chủ sinh tới 172 link — hầu hết nằm ở depth 3. Vì MAX_DEPTH = 3,
crawler không mở rộng thêm từ depth 3 nữa. Sau khi crawl hết các URL depth 3
trong frontier, crawler dừng với Frontier Remaining = 0.

Crawl dừng do frontier rỗng — một trong hai điều kiện dừng hợp lệ của đề bài
(điều kiện còn lại là chạm MAX_PAGES, đã gần chạm khi MAX_PAGES = 150).

Nhận xét về skip reasons
Skipped URLs = 2901 đến từ 3 nhóm chính:

duplicate — MIT OCW có cấu trúc điều hướng lặp lại cao (menu, breadcrumb,
footer trỏ tới cùng vài chục URL cốt lõi từ hàng trăm trang khác nhau).

outside_allowed_domain — link trỏ ra ngoài ocw.mit.edu (ví dụ
mit.edu, openlearning.mit.edu, mạng xã hội, ...).

blocked_file_type — link tới PDF, ảnh, video bài giảng, file ZIP...

So sánh với rule cũ
Lần đầu chạy với rule chặn tất cả URL /search/?q=..., kết quả:

Pages Crawled: 63, dừng sớm vì frontier cạn.

Depth 3: 60.

Sau khi nới rule (chỉ chặn page/sort/view/format), kết quả tăng vọt:

Pages Crawled: 146 (hơn 2.3×).

Visible Text Stored: 1.37M chars (hơn 2.16×).

→ Chứng tỏ các URL /search/?q=... có chứa link course hữu ích trong
HTML tĩnh, và việc chặn toàn bộ chúng là quá nghiêm ngặt.

9. Cấu trúc project
text
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
    ├── crawler_h.db
    └── crawl_summary.txt
10. Cách chạy
bash
python -m pip install -r requirements.txt
python main.py
Chạy lệnh từ trong thư mục Assignment1.

11. Ghi chú về Git workflow
Nhánh crawl/h chứa commit cá nhân của thành viên H.
Sau khi merge vào main, config.py sẽ được gộp với 4 seed còn lại
thành danh sách 5 seed hoàn chỉnh (xem README nhóm ở nhánh main).

MAX_PAGES cũng sẽ được thống nhất lại ở nhánh main (ví dụ 100 để
tiết kiệm thời gian chạy tổng thể cho cả nhóm), trong khi nhánh crawl/h
đã chạy với MAX_PAGES = 150 để thu được bộ dữ liệu đầy đủ nhất có thể
trong phạm vi seed /search/.