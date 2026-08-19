---
name: cumcm-paper-distillation
description: Deep-distill approved historical CUMCM paper PDFs into the repository's 16-section v1.1 evidence record with mathematical audit, page-level traceability, extraction QA, and progress updates. Use for per-paper distillation or review; do not use for corpus acquisition, paper selection alone, or unsupported global synthesis.
---

# CUMCM Paper Distillation

Deep-distill only the papers explicitly authorized in the current batch. The Skill defines how to distill; source PDFs and knowledge outputs remain under `literature/`.

## Scope and invariants

- Read `context/PROBLEM.md`, `context/CURRENT_STATE.md`, `context/ASSUMPTIONS.md`, `context/DECISIONS.md`, and `context/TODO.md` before substantial work.
- Treat `literature/raw_papers/` as immutable. Never edit, optimize, OCR-in-place, rename, or overwrite a source PDF.
- Preserve provenance boundaries. A filename, watermark, collection label, or official-display page does not by itself prove an award level.
- Never fabricate unreadable equations, missing parameters, absent validation, unavailable code, or paper conclusions.
- Use claim types `explicit`, `interpretation`, and `criticism`. Record `independent calculation` as a Traceability transformation, not as a fourth claim type.
- Do not start a later batch, final global playbook, or unrelated synthesis without explicit authorization.
- The five Batch 1 reports are the calibration set. Do not regenerate or reformat them merely to conform to v1.1; use the calibration profile only when validating them.

## Start or resume safely

1. Read `literature/README.md`, `literature/synthesis/CORE_PAPER_SELECTION.md`, `literature/metadata/core_paper_selection.csv`, `literature/metadata/papers.csv`, `literature/metadata/progress.json`, and any current batch review/status file under `literature/synthesis/`.
2. Resolve the exact approved paper IDs, source paths, expected SHA-256 values, provenance records, and output paths before writing.
3. Reuse source-hash-matched extraction artifacts and completed analysis. Continue partial work instead of replacing it. If the PDF hash changed, stop and reassess provenance and extraction.
4. Run the inventory before processing, but do not use inventory as permission to process papers outside the approved set.

Read [references/metadata-and-resume.md](references/metadata-and-resume.md) whenever starting, resuming, or closing a batch.

## Extract and inspect the whole paper

Use the repository extraction pipeline for the specified paper IDs. Read every physical PDF page, including appendices and code. Inspect the quality report before trusting text.

- Render and visually verify pages supporting important equations, tables, figures, code, parameter values, contradictions, and numerical checks.
- Embedded-text success does not certify formula or table accuracy.
- When the text layer is poor or absent, follow [references/extraction-and-ocr.md](references/extraction-and-ocr.md). OCR is an aid, not source authority; preserve its engine, language, settings, and uncertainties.
- If a central page remains unreadable, record the limitation and stop rather than infer its content.

Follow the available PDF inspection skill for rendering and visual QA.

## Write the v1.1 analysis

Use `literature/scripts/per_paper_template.md` and retain all 16 H2 sections. Read [references/schema-v1.1.md](references/schema-v1.1.md) before authoring.

- Use Chinese as the primary explanatory language. At first occurrence, give the standard English name and abbreviation for an important method when useful.
- Keep mathematical notation intact unless notation normalization improves readability; label that transformation in traceability.
- Extract model-selection reasoning, not just model names.
- Distinguish assumptions, problem-provided values, estimated parameters, literature-derived values, author choices, and algorithm hyperparameters.
- Classify validation evidence as L1-L5 together with its limitations. Never treat the labels as a monotonic score.
- Put detailed numerical evidence primarily in Validation, Sensitivity/Robustness, ledgers, and Traceability. Avoid repeating it in Strengths and Weaknesses.
- Make Reusable Techniques conditional and transferable. Keep Competition Takeaways to about 5-8 concise actions.

After identifying the paper's archetypes, read only the applicable parts of [references/audit-rules.md](references/audit-rules.md).

## Audit before accepting claims

Perform active numerical and source audits, including simple arithmetic. Compare the paper's prose, equations, tables, figures, code, and reported output where available.

- Check units, dimensions, degrees of freedom, parameter counts, percentages, inequalities, reconciled counts, boundary solutions, objectives, and constraints.
- For negative claims, use “在已审查范围内，未发现……” and record the full review scope. Keyword search alone is not evidence of absence.
- Distinguish `not reported`, `not assessable`, `proposed but not implemented`, and `contradicted`. Put the unavailable-artifact reason in Notes or the Reproduction Audit.
- A paper's award or display status does not reduce the audit burden.

## Validate and update repository state

1. Run `scripts/validate_distillation.py <per-paper-file>` from this Skill directory for future v1.1 reports. Use `--schema 1.0-calibration` only for the five unchanged Batch 1 files.
2. Confirm the source SHA-256 still matches `papers.csv` and acquisition metadata.
3. Add exactly one normalized row to `literature/metadata/model_matrix.csv`; update an existing row instead of duplicating it.
4. Run `python3 literature/scripts/corpus_pipeline.py inventory` and then `validate` so `papers.csv` and `progress.json` are derived from actual files.
5. Update `literature/synthesis/CORE_PAPER_SELECTION.md`, the current batch review/status file under `literature/synthesis/`, and shared context only when their state changed. Build cross-paper synthesis only from completed analyses.
6. If a paper cannot complete, record or update it in `literature/metadata/distillation_blockers.csv` with `scripts/update_blocker.py`; do not force `analysis_status=complete`. Mark the blocker resolved when work later resumes successfully.
7. Run `git diff --check` and confirm that no unapproved per-paper files or final playbook were created.

## Output contract

For each approved paper, the normal outputs are:

- `literature/extracted/<paper_id>.*` for embedded extraction, plus `.ocr.*` artifacts only when needed;
- `literature/per_paper/<paper_id>.md` using schema v1.1;
- one row in `literature/metadata/model_matrix.csv`;
- derived updates to `literature/metadata/papers.csv` and `literature/metadata/progress.json`.

At handoff, reconcile every authorized ID as completed, reused, blocked, or explicitly deferred. Report extraction/OCR issues, provenance boundaries, validation labels with limitations, major source contradictions, files changed, verification results, and the exact stop point. Do not claim batch completion while any authorized paper remains blocked or deferred.
