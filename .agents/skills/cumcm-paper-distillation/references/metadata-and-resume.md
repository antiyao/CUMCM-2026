# Metadata, Resumability, and Batch Closure

## Resolve the approved scope

Use `literature/synthesis/CORE_PAPER_SELECTION.md` and `literature/metadata/core_paper_selection.csv` to obtain exact paper IDs and batch numbers. If the current batch has a review/status file, it lives under `literature/synthesis/` and must be named in the task handoff. User authorization controls scope; a selected paper is not automatically authorized for the current turn.

Before work, check:

- `literature/metadata/papers.csv`
- `literature/metadata/progress.json`
- `literature/metadata/acquisition.csv`
- `literature/metadata/distillation_blockers.csv`
- existing `literature/extracted/<paper_id>.*`
- existing `literature/per_paper/<paper_id>.md`
- source PDF SHA-256

## Resume rules

- If source hash and a complete per-paper analysis match, skip it unless the user explicitly requests revision.
- If extraction is complete but analysis is partial, reuse extraction and continue the missing sections.
- If analysis exists but fails structural validation, preserve useful content and repair only the gaps.
- If source hash differs, do not reuse extraction or analysis without review.
- Never use a batch limit that could select unintended papers; pass explicit paper IDs.
- Do not overwrite another task's partial report without inspecting it.

If missing OCR support, unreadable central evidence, an unavailable required supplement, or another concrete dependency prevents completion, record the block with:

```bash
python3 .agents/skills/cumcm-paper-distillation/scripts/update_blocker.py \
  --paper-id <paper_id> --batch <batch> --stage <stage> \
  --status blocked --reason <reason> --evidence <evidence> \
  --required-action <required_action>
```

When resolved, run the same command with `--status resolved`. A partially closed batch must reconcile every authorized ID as `completed`, `reused`, `blocked`, or explicitly `deferred`; it must not claim completion while a blocker remains.

The only reports eligible for `--schema 1.0-calibration` are the unchanged Batch 1 files:

- `cumcm_9ac848b6825e`
- `cumcm_3c2a8301acac`
- `cumcm_6deaa40c4a2d`
- `cumcm_12ec8230e264`
- `cumcm_d8ff740a46d8`

Every later paper uses v1.1.

## Provenance

Use acquisition and verification metadata, not filenames, to set:

- `V`: award level independently verified;
- `E`: organizer explicitly labels an excellent paper, exact award unknown;
- `O`: official display, award level not inferred;
- `O*`: official code/year match but local version needs version review;
- `L`: local collection only, award unverified.

Keep the concrete `verification_status`, URL, and limitations in Metadata. An official display confirms display status, not national first prize.

## Required closeout sequence

1. Validate every new v1.1 report with the Skill validator.
2. Add or update one `model_matrix.csv` row per completed paper; reject duplicate IDs.
3. Run:

```bash
python3 literature/scripts/corpus_pipeline.py inventory
python3 literature/scripts/corpus_pipeline.py validate
```

4. Confirm `analysis_status=complete`, source hash unchanged, and progress counts correct.
5. Update `literature/synthesis/CORE_PAPER_SELECTION.md`, the named current batch review/status file, and `context/CURRENT_STATE.md` / `context/TODO.md` if state changed.
6. Reconcile each authorized ID against completed/reused reports and active blockers; confirm no later-batch file or final playbook was created.
7. Do not commit or push unless separately authorized.

`papers.csv` and `progress.json` are derived state. Do not hand-edit their statuses when the pipeline can compute them from artifacts.
