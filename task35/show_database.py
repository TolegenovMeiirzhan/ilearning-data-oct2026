
from pathlib import Path
import sqlite3
from contextlib import closing

path = Path(__file__).resolve().parent / "results" / "books.sqlite"
with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
    print("PERSISTED DATABASE:", path)
    for name, sql in db.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"):
        print("\n", sql)
        print("ROW COUNT:", db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0])
    print("\nBOOKS: first 10 actual persisted rows")
    for row in db.execute("SELECT * FROM books ORDER BY rowid LIMIT 10"):
        print(row)
    print("\nALL SUMMARY ROWS: publication_year | book_count | average_price (USD)")
    for year, count, price in db.execute("SELECT * FROM summary ORDER BY publication_year"):
        print(f"{year} | {count:3} | {price}")
