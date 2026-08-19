#!/usr/bin/env python3

import argparse
import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


FIELDS = [
    "paper_id",
    "batch",
    "stage",
    "status",
    "reason",
    "evidence",
    "required_action",
    "updated_at",
]


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_rows(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"unexpected blocker CSV fields: {reader.fieldnames}")
        return list(reader)


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description="Idempotently record or resolve a paper-distillation blocker.")
    parser.add_argument(
        "--metadata-file",
        type=Path,
        default=Path("literature/metadata/distillation_blockers.csv"),
    )
    parser.add_argument("--paper-id", required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument(
        "--stage",
        required=True,
        choices=["provenance", "extraction", "ocr", "reading", "distillation", "validation", "metadata"],
    )
    parser.add_argument("--status", required=True, choices=["blocked", "resolved"])
    parser.add_argument("--reason", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--required-action", required=True)
    args = parser.parse_args()

    if not args.paper_id.startswith("cumcm_"):
        raise SystemExit("paper ID must start with cumcm_")

    path = args.metadata_file.resolve()
    try:
        rows = load_rows(path)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    record = {
        "paper_id": args.paper_id,
        "batch": args.batch,
        "stage": args.stage,
        "status": args.status,
        "reason": args.reason,
        "evidence": args.evidence,
        "required_action": args.required_action,
        "updated_at": utc_now(),
    }
    key = (args.paper_id, args.stage)
    replaced = False
    for index, row in enumerate(rows):
        if (row["paper_id"], row["stage"]) == key:
            rows[index] = record
            replaced = True
            break
    if not replaced:
        rows.append(record)
    rows.sort(key=lambda row: (row["batch"], row["paper_id"], row["stage"]))
    write_rows(path, rows)
    print(f"{args.status}: {args.paper_id} stage={args.stage} file={path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
