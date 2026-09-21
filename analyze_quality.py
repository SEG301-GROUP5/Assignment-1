"""analyze_quality.py — đo chất lượng dữ liệu trong crawler.db"""
import sqlite3
import statistics
import sys

def analyze(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    total = cur.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    print(f"Tổng số trang lưu trong DB : {total}")

    lengths = [
        len(row[0]) for row in cur.execute(
            "SELECT content FROM pages WHERE content IS NOT NULL"
        ).fetchall()
    ]
    if lengths:
        print(f"Độ dài content trung bình : {statistics.mean(lengths):.0f} ký tự")
        print(f"Độ dài content nhỏ nhất   : {min(lengths)}")
        print(f"Độ dài content lớn nhất   : {max(lengths)}")
        empty = sum(1 for l in lengths if l < 50)
        print(f"Trang gần như rỗng (<50 ký tự): {empty} ({empty/total*100:.1f}%)")

    dup_hash = cur.execute(
        """
        SELECT content_hash, COUNT(*) c FROM pages
        WHERE content_hash IS NOT NULL
        GROUP BY content_hash HAVING c > 1
        """
    ).fetchall()
    print(f"Nhóm nội dung trùng còn sót  : {len(dup_hash)} nhóm")

    print("\nPhân bố theo depth:")
    for depth, count in cur.execute(
        "SELECT depth, COUNT(*) FROM pages GROUP BY depth ORDER BY depth"
    ).fetchall():
        print(f"  Depth {depth}: {count}")

    print("\nPhân bố status code:")
    for status, count in cur.execute(
        "SELECT status_code, COUNT(*) FROM pages GROUP BY status_code ORDER BY status_code"
    ).fetchall():
        print(f"  HTTP {status}: {count}")

    conn.close()


if __name__ == "__main__":
    analyze(sys.argv[1] if len(sys.argv) > 1 else "data/crawler_ngan.db")