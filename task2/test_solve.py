import hashlib
from pathlib import Path
import unittest

from solve import final_hash, normalize_email, read_records, sorting_key


class AlgorithmTests(unittest.TestCase):
    def test_sha3_256_empty_vector(self):
        self.assertEqual(
            hashlib.sha3_256(b"").hexdigest(),
            "a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a",
        )

    def test_course_product_example(self):
        self.assertEqual(
            sorting_key("63a6ba9e5de66b11ad6c6d3d1b39a5456f65f918fde6250565e365d89a5196c6"),
            71365623100112242680609229940949951316513259520000000000,
        )

    def test_zero_digits_contribute_one(self):
        self.assertEqual(sorting_key("0" * 64), 1)

    def test_f_digits_use_arbitrary_precision(self):
        self.assertEqual(sorting_key("f" * 64), 2 ** 256)

    def test_lowercase_email(self):
        self.assertEqual(normalize_email("Student.Name@EXAMPLE.COM"), "student.name@example.com")

    def test_empty_email_rejected(self):
        with self.assertRaises(ValueError):
            normalize_email("")

    def test_whitespace_email_rejected(self):
        with self.assertRaises(ValueError):
            normalize_email(" student@example.com")

    def test_exact_concatenation(self):
        records = [{"sha3_256": "0" * 64}, {"sha3_256": "f" * 64}]
        expected = hashlib.sha3_256(("0" * 64 + "f" * 64 + "student@example.com").encode()).hexdigest()
        self.assertEqual(final_hash(records, "STUDENT@EXAMPLE.COM"), expected)


class ActualArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = read_records(Path(__file__).with_name("task2.zip"))

    def test_all_256_files(self):
        self.assertEqual(len(self.rows), 256)
        self.assertEqual(len({row["file"] for row in self.rows}), 256)

    def test_lowercase_hex_hashes(self):
        for row in self.rows:
            self.assertRegex(row["sha3_256"], r"^[0-9a-f]{64}$")

    def test_strictly_ascending_products(self):
        self.assertTrue(all(a["product"] < b["product"] for a, b in zip(self.rows, self.rows[1:])))

    def test_16384_hash_characters(self):
        self.assertEqual(len("".join(row["sha3_256"] for row in self.rows)), 16384)

    def test_synthetic_email_case_does_not_change_hash(self):
        self.assertEqual(final_hash(self.rows, "student@example.com"), final_hash(self.rows, "STUDENT@EXAMPLE.COM"))

    def test_different_email_changes_answer(self):
        self.assertNotEqual(final_hash(self.rows, "student@example.com"), final_hash(self.rows, "another@example.com"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
