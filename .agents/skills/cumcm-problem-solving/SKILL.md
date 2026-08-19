---
name: cumcm-problem-solving
description: Analyze and execute active CUMCM modeling workflows using the current problem and data, team state, and this repository's distilled historical knowledge. Use for problem choice or decomposition, historical-method retrieval, candidate-pipeline comparison, model and validation planning, approved-model implementation, or result diagnosis; do not use for historical-paper acquisition or distillation, repository cleanup, Git-only work, or unrelated isolated coding.
---

# CUMCM Problem Solving

Use the historical knowledge base to improve reasoning about the current competition problem. Historical papers are methodological evidence, not answer templates. This Skill is independent from `cumcm-paper-distillation` and does not call its PDF, OCR, acquisition, or schema workflow.

## Runtime gate and source order

Before substantial work, read `AGENTS.md` and the five shared context files:

- `context/PROBLEM.md`
- `context/CURRENT_STATE.md`
- `context/ASSUMPTIONS.md`
- `context/DECISIONS.md`
- `context/TODO.md`

Read `context/MODELING_PLAN.md` when it exists. Inspect the current Git/worktree state before writing shared files.

Use evidence in this order:

1. the official current problem, `context/PROBLEM.md`, `data/raw/`, and official supplements;
2. current team state, accepted assumptions, decisions, tasks, and results;
3. `literature/synthesis/INDEX.md` and `literature/synthesis/QUICK_REFERENCE.md`;
4. a small set of relevant files under `literature/per_paper/`.

The current problem always overrides historical analogies. If authoritative current-problem information is missing, identify what is unavailable instead of inventing it. Normal historical retrieval must not depend on `literature/raw_papers/`, OCR, or acquisition artifacts. If the cleaned INDEX, QUICK_REFERENCE, metadata, or per-paper layer is missing or inconsistent, stop and report the blocker.

## Choose the working mode

- **Analyze or plan:** understand the problem, retrieve relevant methods, compare pipelines, and plan validation. Do not implement merely because the user asks which model to use.
- **Implement an approved direction:** confirm the accepted plan and translate it into explicit data, baseline, model, validation, sensitivity, visualization, and paper-output tasks.
- **Diagnose or revise:** inspect results and assumptions first. Prefer diagnosis over adding models; retrieve more historical papers only when a newly discovered methodological issue warrants it.

## Core workflow

1. Analyze the current problem independently. Separate official facts, inferred structure, proposed assumptions, and missing information. For each subproblem identify the objective, required output, variables, data, constraints, temporal/spatial structure, uncertainty, prediction, optimization, ranking, causal, simulation, and evaluation requirements.
2. Classify subproblems separately and make their dependency graph explicit. Do not force the whole problem into one archetype.
3. Follow [references/retrieval-policy.md](references/retrieval-policy.md). Retrieve by methodological similarity, normally 3–6 reports when coverage is material. When the primary archetype is a known corpus gap, especially strict causal inference, form the main approach from first principles and open at most 2 reports only for explicitly named auxiliary interfaces. Use 0–2 reports for narrow validation diagnosis. Explain transfer logic and non-transferable weaknesses.
4. When genuine alternatives exist, form about 2–4 serious end-to-end candidate pipelines. Include a meaningful baseline. Let complex methods earn their complexity through diagnostics, realism, constraints, or validation.
5. Compare candidates qualitatively before recommending one. Do not manufacture a weighted score unless the current problem itself requires formal multi-criteria selection.
6. Read only the applicable sections of [references/archetype-audits.md](references/archetype-audits.md), then use [references/validation-policy.md](references/validation-policy.md) to define validation before implementation.
7. Check units, dimensions, ranges, counts, parameter counts, percentages, inequality directions, objective signs, constraints, and boundary behavior throughout.
8. Recommend a main pipeline with explicit assumptions, validation boundaries, risks, fallback, and immediate next actions. When the user approves or requests a concrete plan or implementation, follow [references/output-contract.md](references/output-contract.md).

## Invariants

- Do not reuse historical numerical results, prose, or assumptions without current-problem justification.
- Do not select a method because the topic letter or title looks similar, or because a paper won an award.
- Do not claim historical validation transfers to the current problem.
- Do not introduce assumptions silently or mark them accepted merely because retrieval suggested them.
- Do not call training fit, internal consistency, or same-model simulation independent validation.
- Do not describe a heuristic as globally optimal without an appropriate certificate or exhaustive argument.
- Never modify `data/raw/`. Do not overwrite teammate work or silently contradict accepted decisions.
- Do not commit, push, merge, rebase, or force-push unless explicitly requested.

## Reference router

- Read [references/retrieval-policy.md](references/retrieval-policy.md) when selecting or transferring historical knowledge, especially when coverage is weak.
- Read only the matched archetype sections in [references/archetype-audits.md](references/archetype-audits.md) after decomposing the current problem.
- Read [references/validation-policy.md](references/validation-policy.md) when comparing candidates, designing experiments, or judging results.
- Read [references/output-contract.md](references/output-contract.md) before creating `MODELING_PLAN.md`, mutating shared context, transitioning to implementation, or revising an accepted plan.
