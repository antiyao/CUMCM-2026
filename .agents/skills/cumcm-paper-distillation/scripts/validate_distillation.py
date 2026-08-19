#!/usr/bin/env python3

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


H2_SECTIONS = [
    "## 1. Problem Archetype",
    "## 2. Problem Decomposition",
    "## 3. Data Processing",
    "## 4. Models Used",
    "## 5. Model Pipeline",
    "## 6. Model Improvements",
    "## 7. Parameter Estimation and Optimization",
    "## 8. Validation",
    "## 9. Sensitivity and Robustness",
    "## 10. Visualization Strategy",
    "## 11. Writing Structure",
    "## 12. Strengths",
    "## 13. Weaknesses",
    "## 14. Reusable Techniques",
    "## 15. Competition Takeaways",
    "## 16. Traceability",
]
CALIBRATION_IDS = {
    "cumcm_9ac848b6825e",
    "cumcm_3c2a8301acac",
    "cumcm_6deaa40c4a2d",
    "cumcm_12ec8230e264",
    "cumcm_d8ff740a46d8",
}
PLACEHOLDER = re.compile(
    r"\b(?:TODO|TBD|PLACEHOLDER)\b|(?:^|:\s)<[^>\n]+>\s*$|\|\s*<[^>\n]+>\s*\|",
    re.IGNORECASE | re.MULTILINE,
)

V11_BLOCKS = {
    "### Model Decision Ledger": [
        "Candidate model",
        "Selected / rejected",
        "Purpose",
        "Author-stated reason",
        "Comparison evidence",
        "Missing comparison",
        "Distiller assessment",
    ],
    "### Parameter and Assumption Ledger": [
        "Symbol / parameter",
        "Meaning",
        "Unit",
        "Source",
        "Value or range",
        "Source type",
        "Estimation or setting method",
        "Sensitivity tested?",
        "Notes",
    ],
    "### Validation Evidence Table": [
        "Validation target",
        "Evidence type",
        "Data independence",
        "Metric",
        "Repetitions",
        "Result",
        "Failure case",
        "Limitation",
        "Justified conclusion boundary",
    ],
    "### Sensitivity / Robustness Table": [
        "Parameter or perturbation",
        "Baseline",
        "Variation range",
        "Sampling method",
        "Output metric",
        "Result",
        "Conclusion changed?",
        "Interpretation",
    ],
    "### Reproduction Audit": [
        "Audit item",
        "Finding",
        "Evidence / review scope",
        "Reproducibility blocker or limitation",
    ],
    "### Numerical Sanity Checks": [
        "Check",
        "Source claim",
        "Independent check",
        "Result",
        "Source page / object",
        "Notes",
    ],
}

TRACE_HEADER = [
    "Claim",
    "Claim type",
    "Source page",
    "Source section",
    "Source object",
    "Transformation",
    "Review scope",
    "Notes",
]

METADATA_FIELDS = [
    "Distillation schema",
    "Paper ID",
    "Year",
    "Problem",
    "Award",
    "Provenance tier",
    "Source file",
    "Source URL",
    "Verification source",
    "Pages",
    "SHA-256",
    "Extraction method",
    "Extraction quality",
    "Page convention",
    "Visually checked pages",
    "Unresolved extraction ambiguities",
    "Supplemental artifacts",
]

NEGATIVE_PATTERNS = re.compile(
    r"未发现|未见|没有(?:进行|提供|报告|给出|使用|展示)|not found|does not|did not|no independent|no rolling|no validation",
    re.IGNORECASE,
)


def split_table_row(line):
    if not line.lstrip().startswith("|"):
        return None
    cells = re.split(r"(?<!\\)\|", line.strip())
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return [cell.strip().replace(r"\|", "|") for cell in cells]


def section_lines(lines, heading):
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        return []
    level = len(heading) - len(heading.lstrip("#"))
    end = len(lines)
    for i in range(start + 1, len(lines)):
        match = re.match(r"^(#{1,%d})\s" % level, lines[i])
        if match:
            end = i
            break
    return lines[start + 1 : end]


def table_after_heading(lines, heading):
    block = section_lines(lines, heading)
    for index, line in enumerate(block):
        header = split_table_row(line)
        if not header:
            continue
        if index + 1 >= len(block):
            return header, []
        separator = split_table_row(block[index + 1])
        if not separator or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator):
            continue
        rows = []
        for row_line in block[index + 2 :]:
            row = split_table_row(row_line)
            if row is None:
                if row_line.strip():
                    break
                if rows:
                    break
                continue
            rows.append(row)
        return header, rows
    return None, []


def metadata_value(text, field):
    match = re.search(rf"^- {re.escape(field)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(path, schema, repo_root):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    errors = []
    warnings = []

    if not lines or not lines[0].startswith("# Paper:"):
        errors.append("missing '# Paper:' title")
    for heading in H2_SECTIONS:
        if heading not in text:
            errors.append(f"missing required section: {heading}")
    if PLACEHOLDER.search(text):
        errors.append("unresolved TODO/template placeholder")

    actual_h2 = [line for line in lines if re.match(r"^## (?:[1-9]|1[0-6])\. ", line)]
    if actual_h2 != H2_SECTIONS:
        errors.append("16 numbered H2 section names are missing, changed, duplicated, or out of order")

    if schema == "1.0-calibration":
        if path.stem not in CALIBRATION_IDS:
            errors.append("1.0-calibration is restricted to the five approved Batch 1 paper IDs")
        return errors, warnings, {"trace_rows": None, "schema": schema}

    if not re.search(r"^- Distillation schema:\s*1\.1\s*$", text, re.MULTILINE):
        errors.append("Metadata must declare 'Distillation schema: 1.1'")
    for field in METADATA_FIELDS:
        if not re.search(rf"^- {re.escape(field)}:\s*\S", text, re.MULTILINE):
            errors.append(f"missing or empty Metadata field: {field}")

    metadata = {field: metadata_value(text, field) for field in METADATA_FIELDS}
    source_hash = (metadata.get("SHA-256") or "").strip("`")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", source_hash):
        errors.append("Metadata SHA-256 must be exactly 64 hexadecimal characters")
    provenance = metadata.get("Provenance tier") or ""
    if not re.match(r"^(?:V|E|O\*|O|L)(?:\s|;|:|（|\(|$)", provenance):
        errors.append("Metadata Provenance tier must begin with V, E, O, O*, or L")
    visual_pages = (metadata.get("Visually checked pages") or "").strip().casefold()
    if visual_pages in {"", "none", "n/a", "not reported", "unknown"}:
        errors.append("Metadata must identify concrete visually checked pages/objects")

    source_value = (metadata.get("Source file") or "").strip("`")
    if source_value:
        source_path = Path(source_value)
        if not source_path.is_absolute():
            if source_path.parts[:2] == ("literature", "raw_papers"):
                source_path = repo_root / source_path
            elif source_path.parts[:1] == ("raw_papers",):
                source_path = repo_root / "literature" / source_path
            else:
                source_path = repo_root / "literature" / "raw_papers" / source_path
        if source_path.is_file() and re.fullmatch(r"[0-9a-fA-F]{64}", source_hash):
            if sha256_file(source_path).casefold() != source_hash.casefold():
                errors.append("Metadata SHA-256 does not match the current source PDF")
        elif not source_path.is_file():
            warnings.append(f"source file could not be resolved for hash verification: {source_path}")

    for heading, expected_header in V11_BLOCKS.items():
        if heading not in text:
            errors.append(f"missing v1.1 block: {heading}")
            continue
        header, rows = table_after_heading(lines, heading)
        if header != expected_header:
            errors.append(f"{heading} table header does not match v1.1")
        if heading in {"### Parameter and Assumption Ledger", "### Reproduction Audit", "### Numerical Sanity Checks"} and not rows:
            errors.append(f"{heading} requires at least one evidence row")

    trace_header, trace_rows = table_after_heading(lines, "## 16. Traceability")
    if trace_header != TRACE_HEADER:
        errors.append("Traceability table header does not match v1.1")
    if not trace_rows:
        errors.append("Traceability requires at least one claim row")
    elif len(trace_rows) < 5:
        warnings.append(f"Traceability has only {len(trace_rows)} rows; confirm all major claims are covered")

    allowed_claim_types = {"explicit", "interpretation", "criticism"}
    allowed_transformations = {
        "direct transcription",
        "notation normalization",
        "derived interpretation",
        "independent calculation",
    }
    for row_number, row in enumerate(trace_rows, start=1):
        if len(row) != len(TRACE_HEADER):
            warnings.append(f"Traceability row {row_number}: unescaped pipe or wrong cell count; semantic checks skipped")
            continue
        record = dict(zip(TRACE_HEADER, row))
        if record["Claim type"] not in allowed_claim_types:
            errors.append(f"Traceability row {row_number}: invalid claim type '{record['Claim type']}'")
        if record["Transformation"] not in allowed_transformations:
            errors.append(f"Traceability row {row_number}: invalid transformation '{record['Transformation']}'")
        negative_wording = bool(NEGATIVE_PATTERNS.search(record["Claim"]))
        is_absence_review = record["Source object"] == "none found" or (
            negative_wording and record["Claim type"] == "criticism"
        )
        if is_absence_review:
            if record["Claim type"] != "criticism":
                errors.append(f"Traceability row {row_number}: negative claim must use criticism")
            if record["Source object"] != "none found":
                errors.append(f"Traceability row {row_number}: negative claim must use source object 'none found'")
            if record["Review scope"].strip().casefold() in {"", "n/a", "unknown", "not reported"}:
                errors.append(f"Traceability row {row_number}: negative claim needs a concrete review scope")
            if record["Source page"].strip().casefold() in {"", "n/a", "unknown"}:
                errors.append(f"Traceability row {row_number}: negative claim needs the reviewed page range")

    parameter_header, parameter_rows = table_after_heading(lines, "### Parameter and Assumption Ledger")
    if parameter_header:
        allowed_source_types = {
            "problem-provided",
            "data-estimated",
            "literature-derived",
            "author-assumed",
            "algorithm hyperparameter",
        }
        source_type_index = parameter_header.index("Source type")
        for row_number, row in enumerate(parameter_rows, start=1):
            if len(row) != len(parameter_header):
                continue
            if row[source_type_index] not in allowed_source_types:
                errors.append(
                    f"Parameter row {row_number}: invalid source type '{row[source_type_index]}'"
                )

    validation_header, validation_rows = table_after_heading(lines, "### Validation Evidence Table")
    if validation_header:
        for row_number, row in enumerate(validation_rows, start=1):
            if len(row) != len(validation_header):
                continue
            evidence = row[1]
            if evidence and not re.match(r"^L[1-5]\b", evidence) and evidence.casefold() not in {
                "not reported",
                "not assessable",
            }:
                warnings.append(f"Validation row {row_number}: evidence type should start with L1-L5 or state not reported/not assessable")

    reproduction_header, reproduction_rows = table_after_heading(lines, "### Reproduction Audit")
    if reproduction_header:
        present = {row[0] for row in reproduction_rows if len(row) == len(reproduction_header)}
        required = {
            "Data availability",
            "Code availability",
            "Dependency / environment information",
            "Random seed",
            "Hard-coded constants",
            "Formula-to-code consistency",
            "Code-to-result consistency",
            "Overall reproducibility",
        }
        missing = sorted(required - present)
        if missing:
            errors.append("Reproduction Audit missing item(s): " + ", ".join(missing))

    section_15 = "\n".join(section_lines(lines, "## 15. Competition Takeaways"))
    takeaway_count = len(re.findall(r"(?m)^\s*\d+[.)]\s+", section_15))
    if takeaway_count and not 5 <= takeaway_count <= 8:
        warnings.append(f"Competition Takeaways has {takeaway_count} numbered items; expected about 5-8")

    if len(re.findall(r"[\u3400-\u9fff]", text)) < 300:
        warnings.append("Chinese explanatory content appears sparse; v1.1 uses Chinese as the primary language")

    return errors, warnings, {"trace_rows": len(trace_rows), "schema": schema}


def main():
    parser = argparse.ArgumentParser(description="Validate a CUMCM per-paper distillation report.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--schema", choices=["1.1", "1.0-calibration"], default="1.1")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.path.is_file():
        raise SystemExit(f"file not found: {args.path}")

    repo_root = Path(__file__).resolve().parents[4]
    errors, warnings, metrics = validate(args.path, args.schema, repo_root)
    result = {
        "ok": not errors,
        "path": str(args.path),
        "schema": args.schema,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{'PASS' if result['ok'] else 'FAIL'} {args.path} schema={args.schema}")
        for error in errors:
            print(f"ERROR: {error}")
        for warning in warnings:
            print(f"WARNING: {warning}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
