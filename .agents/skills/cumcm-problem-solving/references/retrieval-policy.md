# Historical Retrieval Policy

Retrieve historical knowledge only after independently decomposing the current problem. The goal is to transfer useful structure while retaining evidence and applicability boundaries.

## Stable retrieval layer

- `literature/README.md`: scope and provenance definitions.
- `literature/synthesis/INDEX.md`: primary navigation by archetype, objective, technique, and validation need.
- `literature/synthesis/QUICK_REFERENCE.md`: recurring decision rules and failure modes.
- `literature/metadata/core_papers.csv`: compact filters for archetypes, methods, validation, exemplar, and batch.
- `literature/metadata/model_matrix.csv`: detailed preprocessing, model, optimization, sensitivity, and robustness fields.
- `literature/metadata/completion.csv`: completion and nonblocking issue status.
- `literature/metadata/provenance.csv`: source and version boundaries when identity or award claims matter.
- `literature/per_paper/<paper_id>.md`: mathematical detail, audits, reusable techniques, and Traceability.

Do not follow `Source file:` paths into raw PDFs during normal competition retrieval. Use raw or acquisition evidence only for an exceptional source re-audit explicitly required by the task.

## Retrieval sequence

1. Map each current subproblem to one or more archetypes and validation needs.
2. Inspect the matching INDEX sections and relevant QUICK_REFERENCE topics.
3. Use `core_papers.csv` or `model_matrix.csv` to narrow candidates by actual methods and validation, not by problem letter.
4. Select about 3–6 reports when they materially cover the current methodological needs. If the primary archetype is listed as a corpus gap, first construct the primary approach from the current problem and mathematical principles; do not open a per-paper report by default. Open at most 2 only when each supports a specifically named auxiliary interface such as panel structure, uncertainty propagation, or constrained allocation. This is a hard cap, and the normal 3–6 default does not apply. For a narrow diagnostic question, likewise use 0–2 targeted reports. Expand only when historical coverage is material and the problem genuinely spans several distinct families.
5. Read only the relevant sections first: Problem Archetype, Model Pipeline, Validation, Weaknesses, Reusable Techniques, Competition Takeaways, and Traceability. Read more when needed to resolve a concrete transfer question.

Do not scan all 32 reports by default or repeatedly reread reports already summarized in the active task context.

## Transfer record

For each selected paper, state:

- **Relevant because:** the current subproblem or methodological challenge it informs.
- **Reusable:** the transferable formulation, workflow, validation design, optimization structure, or audit technique.
- **Do not copy:** source-specific assumptions, implementation failures, validation gaps, or unjustified claims.
- **Required adaptation:** changes needed for the current data, units, constraints, horizon, uncertainty, and validation options.

When a historical claim materially affects the current plan, trace it to the per-paper report rather than citing INDEX or QUICK_REFERENCE as source evidence.

## Weak or absent matches

Say explicitly when historical coverage is weak. Use the knowledge base to identify generic risks, then reason from the official problem, mathematical principles, and current data. Do not force an analogy, inflate retrieval size, or turn award status into evidence of correctness.

Known corpus gaps include strict causal inference, rolling-origin validation, credible end-to-end L5 evidence, optimality certificates for heuristics, multi-seed uncertainty, and end-to-end risk propagation.
