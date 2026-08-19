#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError as exc:
    raise SystemExit("pypdf is required for page counting") from exc


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def command_version(command, version_args):
    result = subprocess.run([command, *version_args], capture_output=True, text=True, check=False)
    return (result.stdout or result.stderr).splitlines()[0].strip()


def available_tesseract_languages(tesseract):
    result = subprocess.run([tesseract, "--list-langs"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines()[1:] if line.strip()}


def normalize(text):
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines()).strip()


def main():
    parser = argparse.ArgumentParser(description="Create separate, source-hash-tracked OCR derivatives for a PDF.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--paper-id", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("literature/extracted"))
    parser.add_argument("--work-dir", type=Path, default=Path("literature/tmp/pdfs"))
    parser.add_argument("--languages", default="chi_sim+eng")
    parser.add_argument("--dpi", type=int, default=250)
    parser.add_argument("--psm", type=int, default=3)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    pdf = args.pdf.resolve()
    if not pdf.is_file() or pdf.suffix.casefold() != ".pdf":
        raise SystemExit(f"PDF not found: {pdf}")
    if not args.paper_id or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for character in args.paper_id):
        raise SystemExit("paper ID may contain only letters, digits, underscore, and hyphen")
    if not 72 <= args.dpi <= 600:
        raise SystemExit("DPI must be between 72 and 600")
    if not 0 <= args.psm <= 13:
        raise SystemExit("PSM must be between 0 and 13")

    pdftoppm = shutil.which("pdftoppm")
    tesseract = shutil.which("tesseract")
    missing_commands = [name for name, value in (("pdftoppm", pdftoppm), ("tesseract", tesseract)) if not value]
    if missing_commands:
        raise SystemExit("missing OCR dependency: " + ", ".join(missing_commands))

    requested_languages = {value for value in args.languages.split("+") if value}
    available_languages = available_tesseract_languages(tesseract)
    missing_languages = sorted(requested_languages - available_languages)
    if missing_languages:
        raise SystemExit(
            "missing Tesseract language pack(s): "
            + ", ".join(missing_languages)
            + "; install them or choose --languages from: "
            + ", ".join(sorted(available_languages))
        )

    source_hash = sha256_file(pdf)
    output_dir = args.output_dir.resolve()
    text_path = output_dir / f"{args.paper_id}.ocr.txt"
    pages_path = output_dir / f"{args.paper_id}.ocr.pages.jsonl"
    quality_path = output_dir / f"{args.paper_id}.ocr.quality.json"
    settings = {"languages": args.languages, "dpi": args.dpi, "psm": args.psm}

    if not args.force and text_path.exists() and pages_path.exists() and quality_path.exists():
        try:
            previous = json.loads(quality_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous = {}
        if previous.get("source_sha256") == source_hash and previous.get("settings") == settings:
            print(json.dumps({"status": "reused", "quality_report": str(quality_path)}, ensure_ascii=False))
            return 0

    reader = PdfReader(str(pdf), strict=False)
    if reader.is_encrypted and reader.decrypt("") == 0:
        raise SystemExit("encrypted PDF requires a password; do not bypass access controls")
    page_count = len(reader.pages)
    if page_count < 1:
        raise SystemExit("PDF has no pages")

    started_at = utc_now()
    page_records = []
    page_errors = []
    args.work_dir.resolve().mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"{args.paper_id}-", dir=args.work_dir.resolve()) as temporary:
        temporary_dir = Path(temporary)
        for page_number in range(1, page_count + 1):
            prefix = temporary_dir / f"page-{page_number:04d}"
            render = subprocess.run(
                [pdftoppm, "-f", str(page_number), "-l", str(page_number), "-r", str(args.dpi), "-png", "-singlefile", str(pdf), str(prefix)],
                capture_output=True,
                text=True,
                check=False,
            )
            image_path = prefix.with_suffix(".png")
            if render.returncode != 0 or not image_path.exists():
                message = normalize(render.stderr) or "pdftoppm produced no image"
                page_errors.append({"page": page_number, "stage": "render", "error": message})
                text = ""
            else:
                ocr = subprocess.run(
                    [tesseract, str(image_path), "stdout", "-l", args.languages, "--psm", str(args.psm)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if ocr.returncode != 0:
                    page_errors.append({"page": page_number, "stage": "ocr", "error": normalize(ocr.stderr)})
                    text = ""
                else:
                    text = normalize(ocr.stdout)
            page_records.append(
                {
                    "schema_version": 1,
                    "paper_id": args.paper_id,
                    "page_number": page_number,
                    "text": text,
                    "visible_char_count": len("".join(text.split())),
                }
            )

    visible_counts = [record["visible_char_count"] for record in page_records]
    pages_with_text = sum(value >= 30 for value in visible_counts)
    text_ratio = pages_with_text / page_count
    median_characters = statistics.median(visible_counts)
    status = "success" if text_ratio >= 0.9 and median_characters >= 100 and not page_errors else "poor_quality"
    issues = ["ocr_requires_visual_verification"]
    if text_ratio < 0.9:
        issues.append("ocr_sparse_pages")
    if median_characters < 100:
        issues.append("ocr_low_median_text")
    if page_errors:
        issues.append("ocr_page_errors")

    combined = "\n\n".join(
        f"===== PAGE {record['page_number']:04d} =====\n\n{record['text']}" for record in page_records
    ) + "\n"
    jsonl = "\n".join(json.dumps(record, ensure_ascii=False) for record in page_records) + "\n"
    report = {
        "schema_version": 1,
        "artifact_type": "ocr_fallback",
        "paper_id": args.paper_id,
        "source_file": str(pdf),
        "source_sha256": source_hash,
        "backend": command_version(tesseract, ["--version"]),
        "renderer": command_version(pdftoppm, ["-v"]),
        "status": status,
        "quality": "ocr_usable_with_visual_review" if status == "success" else "ocr_review_required",
        "settings": settings,
        "metrics": {
            "page_count": page_count,
            "pages_with_at_least_30_nonspace_chars": pages_with_text,
            "visible_char_count": sum(visible_counts),
            "median_nonspace_chars_per_page": median_characters,
            "sparse_page_ratio": round(1 - text_ratio, 6),
        },
        "issues": issues,
        "page_errors": page_errors,
        "started_at": started_at,
        "completed_at": utc_now(),
    }

    atomic_write(text_path, combined)
    atomic_write(pages_path, jsonl)
    atomic_write(quality_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": status, "quality_report": str(quality_path)}, ensure_ascii=False))
    return 0 if status == "success" else 2


if __name__ == "__main__":
    sys.exit(main())
