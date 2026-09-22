# SEG301 - Assignment 1: Focused Web Crawler

## Thành viên thực hiện

| MSSV | Họ và tên |
|---|---|
| CE190248 | Nguyễn Việt Phương |

File `../GroupName.csv` cũng chỉ chứa thông tin của thành viên trên.

## 1. Chủ đề đã chọn

**Chủ đề:** Education

Đây là phiên bản crawler chỉ sử dụng **1 Seed URL** thuộc website Stanford Engineering và chỉ crawl trong phạm vi host `engineering.stanford.edu`.

> Lưu ý: đề bài gốc yêu cầu tối thiểu 2 domain cho bài nộp nhóm. Phiên bản này được xây dựng theo yêu cầu chỉ crawl 1 website/1 link khởi đầu. Nếu dùng làm toàn bộ bài nộp nhóm thì cần kiểm tra lại yêu cầu số domain của giảng viên.

## 2. Seed URL

```text
https://engineering.stanford.edu/students-academics/academics/online-learning
```

Chỉ URL trên được đưa vào URL Frontier ban đầu, vì vậy có đúng **1 URL ở Depth 0**.

## 3. Phạm vi crawl

Crawler sử dụng BFS để phát hiện các liên kết mới bắt đầu từ Seed URL, nhưng chỉ các URL thuộc host:

```text
engineering.stanford.edu
```

mới được phép đưa vào hàng đợi để tiếp tục crawl.

Các hyperlink HTTP/HTTPS trỏ ra ngoài host vẫn được lưu trong bảng `links` của SQLite để giữ lại cấu trúc liên kết, nhưng các trang bên ngoài sẽ không được tải xuống.

## 4. Cấu hình crawler

| Cấu hình | Giá trị |
|---|---:|
| Số Seed URL | 1 |
| Số host/domain được phép | 1 |
| Số trang tối đa | 1500 |
| Độ sâu tối đa | 4 |
| Request timeout | 15 giây |
| Crawl delay cơ bản | 1 giây |
| Số redirect tối đa | 5 |
| Kiểm tra robots.txt | Có |

Cấu hình 1500 trang và Depth 4 được dùng để crawler có thể thu thập nhiều dữ liệu hơn và có cơ hội đi qua Depth 1, Depth 2, Depth 3 và Depth 4 nếu website có đủ liên kết hợp lệ.

Crawler vẫn có giới hạn rõ ràng và sẽ dừng khi đạt `MAX_PAGES` hoặc URL Frontier không còn URL nào.

## 5. Chiến lược crawl

Crawler sử dụng **Breadth-First Search (BFS)** với `collections.deque`.

Mỗi phần tử trong Frontier có dạng:

```python
(url, depth)
```

Ý nghĩa của Depth:

```text
Depth 0 = Seed URL Stanford Online Learning
Depth 1 = Các trang được liên kết trực tiếp từ Seed URL
Depth 2 = Các trang được tìm thấy từ những trang Depth 1
Depth 3 = Các trang được tìm thấy từ những trang Depth 2
Depth 4 = Các trang được tìm thấy từ những trang Depth 3
```

Crawler tránh crawl trùng bằng:

- Chuẩn hóa URL;
- Tập `queued` để lưu URL đã có trong Frontier;
- Tập `visited` để lưu URL đã được xử lý/request.

## 6. Trích xuất và lọc URL

Với mỗi trang HTML, BeautifulSoup trích xuất tất cả hyperlink từ thẻ `<a href="...">`.

URL tương đối được chuyển thành URL tuyệt đối bằng `urljoin()`.

Trước khi một URL được thêm vào Frontier, URL đó phải thỏa các điều kiện:

1. Sử dụng giao thức HTTP hoặc HTTPS;
2. Thuộc `engineering.stanford.edu`;
3. Không phải tài nguyên bị chặn như ảnh, CSS, JavaScript, ZIP, PDF, tài liệu Office, audio hoặc video;
4. Không vượt quá `MAX_DEPTH`;
5. Chưa nằm trong `queued` hoặc `visited`;
6. Được phép crawl theo `robots.txt`.

Các query parameter dùng cho tracking như `utm_*`, `fbclid`, `gclid`, `_rsc` được loại bỏ khi chuẩn hóa URL. Các query parameter khác vẫn được giữ lại vì chúng có thể làm thay đổi nội dung trang.

## 7. Xử lý HTTP và Redirect

Crawler sử dụng `requests.Session` và không giả định rằng mọi request đều trả về HTTP 200.

Các mã redirect `301`, `302`, `303`, `307`, `308` được xử lý thủ công. Trước khi đi theo URL redirect, crawler kiểm tra:

- Host có nằm trong phạm vi cho phép hay không;
- URL có phải loại file bị chặn hay không;
- Có được `robots.txt` cho phép hay không;
- Có xảy ra redirect loop hay không;
- Có vượt quá giới hạn redirect hay không.

Các redirect trung gian được thống kê riêng và không làm mất quota `MAX_PAGES`. Chỉ response cuối cùng không còn redirect mới được tính là một trang đã crawl.

Các lỗi mạng như timeout hoặc connection error được bắt bằng exception để crawler không bị dừng toàn bộ.

## 8. Thu thập dữ liệu đầy đủ

Với mỗi trang HTML hợp lệ, crawler lưu vào SQLite:

- URL cuối cùng;
- Domain;
- Tiêu đề trang;
- Toàn bộ phần text hiển thị của trang, không cắt ngắn;
- Crawl depth;
- HTTP status code cuối cùng;
- Thời điểm crawl;
- Response time.

Các thành phần không phải nội dung hiển thị như `script`, `style`, `noscript`, `template`, `svg` được loại bỏ trước khi trích xuất text.

Toàn bộ hyperlink HTTP/HTTPS được tìm thấy đều được lưu vào bảng `links`, kể cả hyperlink ra ngoài website. Tuy nhiên chỉ URL thuộc Stanford Engineering mới được tiếp tục crawl.

### Tối ưu SQLite

Phiên bản này được tối ưu cho số lượng trang và link lớn:

- Các link của một trang được ghi bằng `executemany()`;
- Chỉ commit một lần cho mỗi trang đã crawl thay vì commit từng hyperlink;
- Bật WAL journal mode và `synchronous=NORMAL`;
- Tạo index cho domain, depth, status của bảng `pages` và source/target của bảng `links`.

Nhờ đó file `crawler.db` vẫn hoạt động ổn định khi lưu hàng nghìn liên kết.

## 9. Thiết kế cơ sở dữ liệu

File cơ sở dữ liệu:

```text
data/crawler.db
```

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

Unique index `(source_url, target_url)` giúp tránh lưu trùng cùng một cạnh liên kết.

## 10. Thống kê kết quả crawl

Sau khi crawler chạy xong, chương trình tự động tạo file:

```text
data/crawl_summary.txt
```

và tự động chèn cùng bộ thống kê thực tế vào README này.

### Kết quả crawl cuối cùng (tự động cập nhật)

<!-- AUTO_CRAWL_RESULTS_START -->

```text
Chạy `python main.py` hoặc `run.bat` một lần để tạo thống kê crawl thực tế.
```

<!-- AUTO_CRAWL_RESULTS_END -->

Các số liệu trên được tạo từ lần crawl thật, không ghi cứng trong code.

## 11. Cấu trúc project

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

## 12. Cách chạy chương trình

Trên Windows, có thể double-click:

```text
run.bat
```

hoặc mở CMD/PowerShell trong thư mục `Assignment1` và chạy:

```bash
python -m pip install -r requirements.txt
python main.py
```

Do cấu hình `MAX_PAGES = 1500` và crawler có delay giữa các request để tránh gửi request quá nhanh đến server, thời gian chạy đầy đủ có thể khá lâu. Đây là hành vi bình thường.

## 13. Kiểm tra trước khi nộp

1. Chạy crawler cho đến khi xuất hiện phần `CRAWLING SUMMARY`.
2. Kiểm tra `data/crawler.db` có dữ liệu trong hai bảng `pages` và `links`.
3. Kiểm tra `data/crawl_summary.txt` chứa thống kê mới nhất.
4. Kiểm tra phần kết quả trong README đã được tự động cập nhật sau khi chạy.
5. Xóa thư mục `__pycache__` nếu có trước khi nén bài.
6. Kiểm tra lại tên thư mục/ZIP theo đúng yêu cầu nộp bài của giảng viên.
