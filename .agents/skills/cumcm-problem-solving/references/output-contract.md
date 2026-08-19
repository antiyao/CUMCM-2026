# Output and Collaboration Contract

Read this reference before writing shared planning files, transitioning to implementation, or revising an accepted direction.

## Response and write modes

- For problem understanding, problem choice, model comparison, or validation design, normally answer with analysis first. Do not implement code unless requested.
- Create or update `context/MODELING_PLAN.md` when the user approves, requests, or delegates a concrete modeling direction. Do not create it merely because historical retrieval occurred.
- Before changing an established plan, identify conflicts with accepted assumptions or decisions and explain why revision is needed.

## Modeling plan structure

Use the following sections when applicable; keep them proportional to the problem:

1. Current Problem Structure
2. Subproblem Decomposition
3. Relevant Historical Knowledge
4. Candidate Pipelines
5. Candidate Comparison
6. Recommended Main Pipeline
7. Baselines
8. Assumptions Requiring Approval
9. Validation Plan
10. Sensitivity / Robustness Plan
11. Data Processing Plan
12. Implementation Plan
13. Expected Figures / Tables
14. Risks and Fallbacks
15. Immediate Next Actions

For each historical paper in section 3, include relevance, reusable idea, weakness to avoid, and required adaptation.

## Shared context updates

Historical retrieval does not make a modeling choice accepted. Update files only when their state actually changes:

- `context/CURRENT_STATE.md`: current progress and results;
- `context/ASSUMPTIONS.md`: explicit assumptions and approval status;
- `context/DECISIONS.md`: genuinely accepted modeling or implementation decisions;
- `context/TODO.md`: completed, added, or reprioritized work;
- `context/MODELING_PLAN.md`: approved or explicitly requested plan.

Do not silently overwrite teammate changes or contradict accepted context.

## Transition to implementation

Translate the approved plan into explicit tasks for data audit, preprocessing, baseline, main model, validation, sensitivity, visualization, and paper-ready outputs.

- Keep `data/raw/` immutable.
- Write cleaned data to `data/processed/`.
- Put reusable implementations under `src/` and exploration under `notebooks/`.
- Put final figures under `figures/` and numerical tables/results under `results/`.
- Make important numerical results reproducible from code and record run settings, seeds, and tolerances.

## Results feedback loop

After implementation, inspect results and diagnostics, test assumptions and validation, and revise the plan when evidence demands it. Retrieve more historical papers only for a newly relevant methodological issue. Do not proliferate models merely because the first result is imperfect.

## Git and team safety

Inspect the worktree before edits and preserve unrelated changes. Do not commit, push, merge, rebase, force-push, or discard teammate work unless explicitly authorized. At handoff, report files changed, validation performed, unresolved assumptions, risks, and the next decision needed.
