# Decision Log

## D001 — Historical-paper distillation workflow v1.1

**Decision:**\
Keep the existing 16-section per-paper structure. For future papers, add structured model-decision, parameter/assumption, validation, sensitivity/robustness, reproduction, numerical-sanity, and extended traceability blocks. Encode the workflow in the repository Skill `.agents/skills/cumcm-paper-distillation/`. Keep the five Batch 1 reports unchanged as the calibration set.

**Reason:**\
Batch 1 demonstrated sufficient mathematical depth and traceability, while revealing repeatable needs for explicit source/code checks, numerical reconciliation, evidence classification, and resumable metadata updates.

**Alternatives Considered:**\
Rewrite the five Batch 1 reports into a new structure; replace the 16-section schema; keep the workflow only as prose without a reusable Skill.

**Status:** Accepted

## D002 — Final historical-literature repository layer

**Decision:**\
Keep the Git-shareable `literature/` layer limited to a concise README, 32 validated per-paper reports, compact core/provenance/completion metadata, the detailed model matrix, and lightweight INDEX/QUICK_REFERENCE retrieval files. Keep raw PDFs, OCR, acquisition evidence, old batch audits, and corpus-maintenance scripts locally available but Git-ignored.

**Reason:**\
This preserves distilled knowledge and claim-level provenance while reducing the intended Git payload from hundreds of megabytes to a primarily text-based retrieval layer. The local archive retains original evidence for future re-audit without making it a normal repository dependency.

**Alternatives Considered:**\
Commit the full raw/extracted corpus; delete local source material; keep all acquisition and progress tables in the shared metadata directory; remove the detailed model matrix after creating the compact core table.

**Status:** Accepted

## D003 — Competition-time problem-solving Skill

**Decision:**\
Use a separate repository Skill for active CUMCM problem solving. It prioritizes the current official problem and data, then team context, then the cleaned historical retrieval layer. It retrieves about three to six reports when historical coverage is material, but uses at most two targeted auxiliary reports for known corpus gaps or narrow diagnostics. It compares end-to-end candidate pipelines, requires baselines and validation planning, and writes shared modeling state only after a direction is accepted or explicitly requested.

**Reason:**\
Historical papers improve method selection and auditing but are not templates. Independent forward tests showed that a softer weak-match rule still caused excessive retrieval in a causal-inference problem, so the hard two-report cap preserves first-principles reasoning where the corpus is weak.

**Alternatives Considered:**\
Merge competition solving into the paper-distillation Skill; scan all 32 reports for every problem; rank candidate models with a fixed weighted score; use historical award status as a model-selection signal.

**Status:** Accepted

No competition modeling decisions have been accepted yet.

When recording a decision, use:

## D001 — Short title

**Decision:**\
What was decided.

**Reason:**\
Why this option was selected.

**Alternatives Considered:**\
Other approaches considered.

**Status:** Accepted / Rejected / Under Review
