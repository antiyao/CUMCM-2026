# Distillation Schema v1.1

Canonical output template: `literature/scripts/per_paper_template.md`.

## Fixed structure

Keep the existing 16 H2 sections in this order:

1. Problem Archetype
2. Problem Decomposition
3. Data Processing
4. Models Used
5. Model Pipeline
6. Model Improvements
7. Parameter Estimation and Optimization
8. Validation
9. Sensitivity and Robustness
10. Visualization Strategy
11. Writing Structure
12. Strengths
13. Weaknesses
14. Reusable Techniques
15. Competition Takeaways
16. Traceability

Metadata must identify schema `1.1`, paper ID, year/problem, award verification boundary, provenance tier, source and verification URLs, source path, page count, SHA-256, extraction mode/quality, page convention, visually checked pages, and unresolved extraction ambiguities.

Also record available or unavailable supplemental artifacts. A referenced but unavailable supplement is `not assessable`; it is not evidence that the author failed to implement the method.

## Structured blocks

### Model Decision Ledger in Section 4

Use these columns exactly:

`Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment`

Record one row per genuine decision. Do not invent alternatives. If the author provides no comparison, write `not reported` and assess the resulting boundary.

### Parameter and Assumption Ledger in Section 7

Use these columns exactly:

`Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes`

Allowed source types are:

- `problem-provided`
- `data-estimated`
- `literature-derived`
- `author-assumed`
- `algorithm hyperparameter`

If a value is independently derived from another source object, state that in Notes and trace the calculation in Section 16. Do not relabel assumptions as estimates.

### Validation Evidence Table in Section 8

Use these columns exactly:

`Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary`

Evidence labels:

- `L1` - in-sample fit
- `L2` - internal consistency / sanity check
- `L3` - perturbation / sensitivity evidence
- `L4` - synthetic truth recovery
- `L5` - independent real-world validation

Always append the concrete method and limitation. The labels are evidence types, not a monotonic score. For example, L4 using the same forward and inverse model has inverse-crime risk. Properly designed independent real-world validation remains the strongest form, but the L5 label alone does not guarantee sound design.

Useful data-independence values include `same sample`, `hold-out`, `external`, `synthetic-same-model`, `synthetic-mismatched`, `theoretical`, and `unknown`.

### Sensitivity / Robustness Table in Section 9

Use these columns exactly:

`Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation`

If no experiment is found, do not fabricate a table of N/A values. Write a scoped negative finding and trace its review scope in Section 16.

### Reproduction Audit in Section 13

Evaluate at least:

- data availability;
- code availability;
- dependency/environment information;
- random seed;
- hard-coded constants;
- formula-to-code consistency;
- code-to-result consistency;
- overall reproducibility and blockers.

Use `reproducible`, `partially reproducible`, `not reproducible`, or `not assessable` only after stating the evidence scope.

### Numerical Sanity Checks in Section 13

Actively test applicable units, dimensions, degrees of freedom, parameter counts, percentages, inequality directions, counts that should reconcile, boundary solutions, objective consistency, constraint consistency, and reported errors.

Use columns:

`Check | Source claim | Independent check | Result | Source page / object | Notes`

`Pass` means the specific check passed, not that the whole model is correct.

## Traceability v1.1

Use these columns exactly:

`Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes`

Claim types:

- `explicit`: directly stated in the available paper, table, figure, equation, or code;
- `interpretation`: a bounded reading of the source structure or numbers;
- `criticism`: an evidence limitation, contradiction, mathematical issue, or failed check.

Transformations:

- `direct transcription`
- `notation normalization`
- `derived interpretation`
- `independent calculation`

Identify the source object as `equation`, `table`, `figure`, `code`, `paragraph`, or `none found`, adding its number/name when available.

For a negative claim:

- phrase it as “在已审查范围内，未发现……” unless the author explicitly states absence;
- set claim type to `criticism`;
- use source object `none found`;
- give the actual physical page range;
- make Review scope nonempty and state whether main text, validation/results sections, appendices, code, and available supplements were reviewed;
- state unavailable supplements in Notes.

Keyword search may locate sections but cannot alone establish absence.

## Missing-value vocabulary

- `N/A`: genuinely inapplicable.
- `not reported`: applicable, but the paper does not report it within the reviewed scope.
- `unknown`: evidence is ambiguous.
- `not assessable`: required artifact or comparator is unavailable.
- `none`: use only when the paper explicitly establishes none.

Do not use `N/A` for missing seeds, hyperparameters, stopping rules, comparison models, sample sizes, cleaning rules, code, or data.

## Writing discipline

- Chinese is primary; introduce standard English name/abbreviation at first useful occurrence.
- Do not translate mathematical notation unnecessarily.
- Keep detailed values in Sections 8-9, structured ledgers, and Section 16.
- Strengths and Weaknesses should cite established findings rather than reproduce all values.
- Reusable Techniques must include when useful, why useful, and limitations.
- Competition Takeaways should contain about 5-8 concise actions.
- Do not impose a fixed length on papers of different complexity.
