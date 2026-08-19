# Current State

## Phase

Pre-competition preparation.

## Current Status

Repository infrastructure and shared Codex context system are being prepared.

## Completed

- GitHub repository created.
- Shared repository structure created.
- Repository-level AGENTS.md configured.
- Shared context system initialized.
- Historical-paper acquisition completed for the active 2015–2025 corpus: 194 unique PDFs.
- Cross-problem core selection approved: 32 papers in three batches.
- Batch 1 deep distillation completed for 5 papers, including extraction artifacts, per-paper reports, model-matrix rows, and workflow review.
- Batch 1 review approved; the 16-section workflow is frozen as v1.1.
- Repository Skill `.agents/skills/cumcm-paper-distillation/` created with schema, audit, OCR fallback, resumability, and structural-validation support.
- Tesseract 5.5.0 Chinese OCR dependency verified: `chi_sim` is available.
- Batch 2 deep distillation completed for all 10 approved papers: 528 pages, 289 traceability rows after the B159 version-review entry, 10 v1.1 reports, and 10 model-matrix rows.
- Batch 3 deep distillation completed for all 17 approved papers: 757 pages, 415 traceability rows, 17 v1.1 reports, and 17 model-matrix rows.
- The approved core-paper corpus is complete at 32/32 papers; `literature/metadata/completion.csv` records the final machine-readable closure state.
- The final shareable `literature/` knowledge layer has been productionized: 32 reports, compact core/provenance/completion metadata, a detailed model matrix, `INDEX.md`, and `QUICK_REFERENCE.md`.
- Raw PDFs, OCR artifacts, acquisition evidence, old batch audits, and corpus-maintenance scripts remain local and are excluded by `.gitignore`; no original source was deleted.
- Repository Skill `.agents/skills/cumcm-problem-solving/` created for competition-time problem understanding, historical retrieval, candidate-pipeline comparison, validation-first planning, approved implementation, and result diagnosis.
- The new Skill passed structural validation, Tests A-E, and a filtered 2020 B historical holdout. Its weak-coverage route was tightened after two forward tests exposed excessive historical retrieval; known corpus gaps now use at most two targeted auxiliary reports.

## In Progress

- The cleaned knowledge base and the new competition-time problem-solving Skill are stopped at the requested human-review checkpoint before any Git staging or publication.

## Current Model

None.

## Current Results

None.

## Open Issues

- Structural validation cannot replace page-level visual and mathematical review.
- B050 uses an 18-page university publication as primary and a 59-page official display as companion; this nonblocking version boundary remains explicit for human confirmation.
- Local acquisition/OCR maintenance still has known renderer and inventory limitations, but normal knowledge retrieval no longer depends on those process artifacts.
- The older `cumcm-paper-distillation` Skill remains independent but still references several pre-cleanup process paths; repair it separately before any future distillation work.
- The 2026 official problem and data are not yet available, so the new Skill has not been exercised on the live competition context.
- The final competition playbook has not started.

## Next Steps

- Human-review the cleaned literature layer, the B050 version boundary, and `.agents/skills/cumcm-problem-solving/`.
- After approval, explicitly authorize `git add → git commit → git push`; none has been performed.
- Use the new Skill against the official problem and data once released; keep current-problem facts above historical analogies.
- Do not create the final playbook without separate explicit approval.
- Continue competition-start collaboration preparation separately.
