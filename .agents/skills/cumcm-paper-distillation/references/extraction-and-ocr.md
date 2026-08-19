# Extraction and OCR Fallback

## Embedded-text path

1. Run `python3 literature/scripts/corpus_pipeline.py inventory`.
2. Extract only approved IDs with repeated `--paper-id` arguments.
3. Inspect `<paper_id>.quality.json`, page records, and source SHA before reading the text.
4. Read the complete PDF and visually check critical pages even when status is `success`.

The pipeline's embedded-text status measures extractability, not semantic or mathematical fidelity.

## When OCR is required

Use OCR when the PDF is image-only, text is missing on material pages, ordering is unusable, or glyph corruption prevents reliable reading.

1. Keep the original PDF unchanged.
2. Check `pdftoppm`, `tesseract`, and required language packs.
3. Run `scripts/ocr_extract.py` from this Skill directory. It writes separate `.ocr.*` derivatives and does not replace embedded extraction artifacts.
4. Record source hash, engine/version, language packs, DPI, page segmentation mode, per-page failures, and quality metrics.
5. Visually compare OCR against representative prose, equations, tables, figures, and every page supporting a major claim.
6. Prefer direct visual transcription for a small number of formula cells rather than trusting OCR punctuation or symbols.

Example:

```bash
python3 .agents/skills/cumcm-paper-distillation/scripts/ocr_extract.py \
  literature/raw_papers/2024/C123.pdf \
  --paper-id cumcm_example \
  --output-dir literature/extracted \
  --languages chi_sim+eng
```

Outputs:

- `<paper_id>.ocr.txt`
- `<paper_id>.ocr.pages.jsonl`
- `<paper_id>.ocr.quality.json`

These are supplementary evidence. The canonical embedded extraction may remain `poor_quality`, which is useful because `progress.json` continues to flag OCR reliance. A completed per-paper analysis must record the OCR fallback in Metadata.

## Failure boundary

- If a required language pack or OCR engine is missing, report the exact dependency; do not silently use the wrong language.
- If central equations/tables remain unreadable after rendering and OCR, do not mark the analysis complete.
- If only noncentral characters are ambiguous, record the exact page/object and keep conclusions within what is readable.
- OCR output never verifies award status or provenance.
