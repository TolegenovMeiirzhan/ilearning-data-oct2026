
from collections import Counter, defaultdict
import contextlib
import csv
from fractions import Fraction
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import main

BASE = Path(__file__).resolve().parent


def sample(identifier=1, price="$1.00", year=2020):
    return dict(id=identifier, title="Book", author="Author", genre="Fiction",
                publisher="Publisher", year=year, price=price)


class SolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix="test_", dir=BASE)
        cls.directory = Path(cls.scratch.name)
        cls.output = cls.directory / "actual"
        with contextlib.redirect_stdout(io.StringIO()):
            cls.report = main.build(BASE / "input" / "task1_d.json", cls.output)
        cls.books = json.loads((cls.output / "normalized_input.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def source(self, name, contents):
        path = self.directory / name
        path.write_text(contents, encoding="utf-8")
        return path

    def build_sample(self, books, name):
        path = self.source(name + ".json", json.dumps(books))
        output = self.directory / name
        with contextlib.redirect_stdout(io.StringIO()):
            main.build(path, output)
        with contextlib.closing(sqlite3.connect(output / "books.sqlite")) as db:
            return db.execute("SELECT * FROM summary ORDER BY publication_year").fetchall()

    def test_actual_source_counts_and_integrity(self):
        self.assertEqual(len(self.books), 5003)
        self.assertEqual(self.report["table_row_counts"], {"books": 5003, "summary": 49})
        self.assertEqual(self.report["currency_counts"], {"USD": 3465, "EUR": 1538})
        self.assertEqual(self.report["ids_above_signed_int64"], 5003)
        self.assertEqual(self.report["sqlite_integrity_check"], "ok")

    def test_every_source_field_and_exact_price_survives_import(self):
        with contextlib.closing(sqlite3.connect(self.output / "books.sqlite")) as db:
            actual = db.execute("SELECT * FROM books ORDER BY rowid").fetchall()
        for source, row in zip(self.books, actual, strict=True):
            expected_price = Fraction(source["price"][1:])
            if source["price"][0] == "€":
                expected_price *= Fraction(6, 5)
            self.assertEqual(row[:7], (
                str(source["id"]), source["title"], source["author"],
                source["genre"], source["publisher"], source["year"], source["price"],
            ))
            self.assertEqual(Fraction(row[-1], 1000), expected_price)

    def test_all_49_summary_rows_match_independent_fraction_recomputation(self):
        prices = defaultdict(list)
        for book in self.books:
            amount = Fraction(book["price"][1:])
            if book["price"].startswith("€"):
                amount *= Fraction(6, 5)
            prices[book["year"]].append(amount)
        expected = []
        for year, values in sorted(prices.items()):
            mean_cents = sum(values) * 100 / len(values)
            quotient, remainder = divmod(mean_cents.numerator, mean_cents.denominator)
            cents = quotient + int(remainder * 2 >= mean_cents.denominator)
            expected.append((year, len(values), f"{cents // 100}.{cents % 100:02}"))
        with contextlib.closing(sqlite3.connect(self.output / "books.sqlite")) as db:
            actual = db.execute("SELECT * FROM summary ORDER BY publication_year").fetchall()
        self.assertEqual(actual, expected)
        self.assertEqual(sum(row[1] for row in actual), 5003)

    def test_full_csv_exports_match_persisted_tables(self):
        with contextlib.closing(sqlite3.connect(self.output / "books.sqlite")) as db:
            for table, ordering in (("books", "rowid"), ("summary", "publication_year")):
                cursor = db.execute(f"SELECT * FROM {table} ORDER BY {ordering}")
                expected = [tuple(str(value) for value in row) for row in cursor]
                with (self.output / f"{table}.csv").open(encoding="utf-8", newline="") as stream:
                    reader = csv.reader(stream)
                    self.assertEqual(next(reader), [field[0] for field in cursor.description])
                    self.assertEqual([tuple(row) for row in reader], expected)

    def test_conversion_retains_fractional_cents(self):
        self.assertEqual(main.to_database_row(sample(price="€5.99"))[-1], 7188)
        self.assertEqual(main.to_database_row(sample(price="$87.25"))[-1], 87250)

    def test_average_rounds_half_up(self):
        self.assertEqual(self.build_sample([sample(1, "$0.01"), sample(2, "$0.02")], "half_up"),
                         [(2020, 2, "0.02")])

    def test_does_not_round_individual_converted_prices(self):
        self.assertEqual(self.build_sample([sample(1, "€0.04"), sample(2, "$0.00")], "no_early_round"),
                         [(2020, 2, "0.02")])

    def test_valid_json_and_ruby_keys_without_corrupting_strings(self):
        book = sample()
        book["title"] = 'Literal :year=> and quote " plus \\ slash'
        source = json.dumps([book], ensure_ascii=False)
        json_path = self.source("ordinary.json", source)
        self.assertEqual(main.read_records(json_path)[0], [book])
        ruby = '[{:id=>1, :title=>"Literal :year=> stays", :year=>2020}]'
        ruby_path = self.source("ruby.json", ruby)
        self.assertEqual(main.read_records(ruby_path)[0][0]["title"], "Literal :year=> stays")

    def test_code_is_never_evaluated(self):
        malicious = self.source("unsafe.json", '[{:id=>__import__("os").system("whoami")}]')
        with self.assertRaises(json.JSONDecodeError):
            main.read_records(malicious)

    def test_duplicate_fields_and_ids_are_rejected(self):
        path = self.source("duplicate_fields.json", '[{"id":1,"id":2}]')
        with self.assertRaisesRegex(ValueError, "Duplicate field"):
            main.read_records(path)
        with self.assertRaisesRegex(ValueError, "Duplicate book IDs"):
            self.build_sample([sample(), sample()], "duplicate_ids")

    def test_bad_prices_and_invalid_schema_are_rejected(self):
        for price in ("GBP 1.00", "$-1.00", "€1.234", "$NaN", "1.00", "$1e3"):
            with self.subTest(price=price), self.assertRaises(ValueError):
                main.to_database_row(sample(price=price))
        for field, value in (("id", True), ("year", "2020"), ("title", " ")):
            book = sample()
            book[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                main.to_database_row(book)

    def test_unusual_years_are_preserved(self):
        self.assertEqual(self.build_sample([sample(1, "$1.00", 1871), sample(2, "$2.00", 2026)], "years"),
                         [(1871, 1, "1.00"), (2026, 1, "2.00")])

    def test_rerun_is_idempotent_and_invalid_source_preserves_existing_database(self):
        before = (self.output / "summary.csv").read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            repeated = main.build(BASE / "input" / "task1_d.json", self.output)
        self.assertEqual(repeated, self.report)
        self.assertEqual((self.output / "summary.csv").read_bytes(), before)
        original_database = (self.output / "books.sqlite").read_bytes()
        invalid = self.source("bad_source.json", json.dumps([sample(price="bad")]))
        with self.assertRaises(ValueError):
            main.build(invalid, self.output)
        self.assertEqual((self.output / "books.sqlite").read_bytes(), original_database)


if __name__ == "__main__":
    unittest.main(verbosity=2)
