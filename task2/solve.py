

from __future__ import annotations

import argparse
import hashlib
import json
import math
import zipfile
from pathlib import Path


def sorting_key(digest: str) -> int:

    return math.prod(int(digit, 16) + 1 for digit in digest)


def normalize_email(email: str) -> str:
    if not email or email != email.strip() or any(c.isspace() for c in email):
        raise ValueError("Email must be nonempty and contain no whitespace.")
    return email.lower()


def read_records(archive_path: Path) -> list[dict]:

    with zipfile.ZipFile(archive_path) as archive:
        files = [entry for entry in archive.infolist() if not entry.is_dir()]
        if len(files) != 256:
            raise ValueError(f"Expected 256 files, found {len(files)}.")
        if len({entry.filename for entry in files}) != 256:
            raise ValueError("The ZIP contains duplicate file names.")
        records = []
        for entry in files:
            digest = hashlib.sha3_256(archive.read(entry)).hexdigest()
            records.append(
                {
                    "file": entry.filename,
                    "sha3_256": digest,
                    "product": sorting_key(digest),
                }
            )
    return sorted(records, key=lambda item: item["product"])


def final_hash(records: list[dict], email: str) -> str:
    text = "".join(record["sha3_256"] for record in records) + normalize_email(email)
    return hashlib.sha3_256(text.encode("utf-8")).hexdigest()


def save_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="Email used to register on the course")
    parser.add_argument(
        "--archive", type=Path, default=Path(__file__).with_name("task2.zip")
    )
    parser.add_argument("--audit", type=Path, help="Optionally save full calculation details as JSON")
    parser.add_argument("--submission", type=Path, help="Optionally save the Discord command as text")
    args = parser.parse_args()

    try:
        email = normalize_email(args.email)
        records = read_records(args.archive)
        answer = final_hash(records, email)
        if args.audit:
            audit = {
                "registration_email_lowercase": email,
                "archive_sha256": hashlib.sha256(args.archive.read_bytes()).hexdigest(),
                "file_count": len(records),
                "unique_sorting_keys": len({row["product"] for row in records}),
                "joined_hashes_length": sum(len(row["sha3_256"]) for row in records),
                "answer_sha3_256": answer,
                                                                                  
                "sorted_files": [{**row, "product": str(row["product"])} for row in records],
            }
            save_text(args.audit, json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
        if args.submission:
            save_text(args.submission, f"!task2 {email} {answer}\n")
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    print(answer)


if __name__ == "__main__":
    main()
