# CUMCM 2026 Team Instructions

This repository is the shared workspace for our mathematical modeling competition team.

## Shared Context

Before doing substantial work, read the following files:

- `context/PROBLEM.md`
- `context/CURRENT_STATE.md`
- `context/ASSUMPTIONS.md`
- `context/DECISIONS.md`
- `context/TODO.md`

Treat these files as the shared source of truth for the team.

Do not silently contradict an accepted modeling decision or assumption.
If information is missing or ambiguous, explicitly state the uncertainty instead of inventing details.

## Repository Structure

- `data/raw/`: original competition data. Do not modify original files.
- `data/processed/`: cleaned or transformed data.
- `src/`: reusable scripts and model implementations.
- `notebooks/`: exploratory analysis and experiments.
- `figures/`: figures intended for analysis or the final paper.
- `results/`: numerical results, tables, model outputs, and intermediate artifacts.
- `paper/`: LaTeX source and paper-related files.
- `context/`: shared project state and team memory.

## Paper Writing

Before drafting, revising, or reviewing project prose, read `docs/WRITING_STYLE.md` and `.agents/skills/humanizer/SKILL.md`. Apply them to Chinese academic writing, including abstracts, assumptions, captions, tables, and result discussions. The project-specific rules in `docs/WRITING_STYLE.md` take precedence over Humanizer's generic style and output suggestions.

Write direct, complete statements about the model, method, result, and applicable conditions. Avoid vague jargon such as repeated “口径” and drafting instructions such as “这里不能说……只能说……”. Preserve necessary assumptions, uncertainty, numerical values, formulas, and evidence. Do not copy internal review instructions into the paper.

## Modeling Rules

All important numerical results must be reproducible from code.

Prefer:
- mathematically interpretable models when practical;
- explicit assumptions;
- validation and sensitivity analysis;
- clear definitions of variables, parameters, and units;
- reproducible data-processing pipelines.

Never fabricate:
- data;
- numerical results;
- citations;
- references;
- experimental outcomes.

Clearly distinguish established facts, modeling assumptions, and speculative ideas.

## Data Rules

Never modify files in `data/raw/`.

Write cleaned or transformed datasets to `data/processed/`.

Do not overwrite important intermediate results unless explicitly requested.

## Team Coordination

Before editing files, inspect the current repository state and avoid overwriting unrelated work from teammates.

Do not run destructive Git commands.

Do not commit, push, merge, rebase, or force-push unless explicitly requested by the user.

Do not discard existing uncommitted changes.

## Shared Memory Updates

After completing substantial work:

- update `context/CURRENT_STATE.md` if the overall project state changed;
- update `context/TODO.md` if tasks were completed, added, or reprioritized;
- update `context/ASSUMPTIONS.md` if a modeling assumption was introduced or changed;
- update `context/DECISIONS.md` when an important modeling or implementation decision is accepted.

Keep these updates concise and useful to another teammate or Codex instance continuing the work.

## Completion Standard

When finishing a task:

1. verify that the relevant code or analysis is reproducible;
2. check for obvious numerical, logical, or dimensional errors;
3. state which files were changed;
4. summarize important results and unresolved issues;
5. update the shared context files when appropriate.
