
import argparse
from collections import Counter
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sqlite3

BASE = Path(__file__).resolve().parent
FIELDS = {"id", "title", "author", "genre", "publisher", "year", "price"}
PRICE = re.compile(r"([$€])(\d+(?:\.\d{1,2})?)\Z")
RATES = {"$": Decimal("1"), "€": Decimal("1.2")}
CURRENCIES = {"$": "USD", "€": "EUR"}
                                                                               
RUBY_KEYS = re.compile(r'"(?:\\.|[^"\\])*"|:([A-Za-z_]\w*)\s*=>')


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate field: {key}")
        result[key] = value
    return result


def read_records(path):

    source = Path(path).read_text(encoding="utf-8-sig")
    try:
        records = json.loads(source, object_pairs_hook=reject_duplicate_keys)
        source_format = "JSON"
    except json.JSONDecodeError:
        normalized = RUBY_KEYS.sub(
            lambda match: json.dumps(match[1]) + ":" if match[1] else match[0],
            source,
        )
        records = json.loads(normalized, object_pairs_hook=reject_duplicate_keys)
        source_format = "Ruby hash notation (normalized safely to JSON)"
    if not isinstance(records, list) or not records:
        raise ValueError("Expected a nonempty array of books")
    return records, source_format


def to_database_row(book):
    if not isinstance(book, dict) or set(book) != FIELDS:
        raise ValueError("Every book must contain exactly the seven source fields")
    if type(book["id"]) is not int or book["id"] < 0:
        raise ValueError("id must be a nonnegative integer")
    if type(book["year"]) is not int:
        raise ValueError("year must be an integer")
    for name in ("title", "author", "genre", "publisher", "price"):
        if not isinstance(book[name], str) or not book[name].strip():
            raise ValueError(f"{name} must be a nonempty string")
    match = PRICE.fullmatch(book["price"])
    if not match:
        raise ValueError(f"Invalid or unsupported price: {book['price']!r}")
    symbol, amount = match.groups()
                                                                        
    mills = Decimal(amount) * RATES[symbol] * 1000
    if mills != mills.to_integral_value() or mills > 2**63 - 1:
        raise ValueError("Converted price cannot be stored exactly as USD mills")
    return (
        str(book["id"]), book["title"], book["author"], book["genre"],
        book["publisher"], book["year"], book["price"],
        CURRENCIES[symbol], int(mills),
    )


def export_csv(connection, query, path):
    cursor = connection.execute(query)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(column[0] for column in cursor.description)
        writer.writerows(cursor)


def build(input_path, output_dir):
    input_path, output_dir = Path(input_path), Path(output_dir)
    records, source_format = read_records(input_path)
    rows = [to_database_row(book) for book in records]
    if len({row[0] for row in rows}) != len(rows):
        raise ValueError("Duplicate book IDs; no records were silently discarded")
                                                                               
    if sum(row[-1] for row in rows) + 5 * len(rows) > 2**63 - 1:
        raise ValueError("Dataset is too large for exact SQLite INTEGER aggregation")
    output_dir.mkdir(parents=True, exist_ok=True)
    database = output_dir / "books.sqlite"
    temporary = output_dir / "books.building.sqlite"
    temporary.unlink(missing_ok=True)
    connection = sqlite3.connect(temporary)
    try:
        connection.executescript((BASE / "schema.sql").read_text(encoding="utf-8"))
        connection.executemany("INSERT INTO books VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
        connection.executescript((BASE / "summary.sql").read_text(encoding="utf-8"))
        connection.commit()
        summary = connection.execute("SELECT * FROM summary ORDER BY publication_year").fetchall()
        counts = {
            "books": connection.execute("SELECT COUNT(*) FROM books").fetchone()[0],
            "summary": connection.execute("SELECT COUNT(*) FROM summary").fetchone()[0],
        }
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if counts["books"] != len(records) or sum(row[1] for row in summary) != len(records):
            raise RuntimeError("Row counts do not reconcile")
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")
        export_csv(connection, "SELECT * FROM books ORDER BY rowid", output_dir / "books.csv")
        export_csv(connection, "SELECT * FROM summary ORDER BY publication_year", output_dir / "summary.csv")
    finally:
        connection.close()
    temporary.replace(database)
    (output_dir / "normalized_input.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = {
        "source_file": input_path.name,
        "source_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "source_format": source_format,
        "source_record_count": len(records),
        "table_row_counts": counts,
        "currency_counts": dict(Counter(row[-2] for row in rows)),
        "publication_year_min": min(row[5] for row in rows),
        "publication_year_max": max(row[5] for row in rows),
        "ids_above_signed_int64": sum(book["id"] > 2**63 - 1 for book in records),
        "duplicate_ids": 0,
        "rejected_records": 0,
        "usd_total_mills": sum(row[-1] for row in rows),
        "exchange_rate": "1 EUR = 1.2 USD",
        "rounding": "ROUND_HALF_UP to cents after calculating the yearly mean",
        "sqlite_integrity_check": integrity,
    }
    (output_dir / "validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"books: {counts['books']} rows; summary: {counts['summary']} rows")
    print("publication_year | book_count | average_price (USD)")
    for year, count, average in summary:
        print(f"{year:16} | {count:10} | {average:>19}")
    print(f"SQLite integrity_check: {integrity}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=BASE / "input" / "task1_d.json")
    parser.add_argument("--output", type=Path, default=BASE / "results")
    args = parser.parse_args()
    build(args.input, args.output)
