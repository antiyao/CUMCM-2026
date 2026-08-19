# Validation-First Policy

Plan validation before choosing or implementing the main model. A sophisticated model without a credible test is not automatically preferable to a simpler baseline.

## Baselines

Use a meaningful baseline whenever practical:

- linear or low-order regression before nonlinear or ML regression;
- naive or seasonal forecasting before complex forecasting;
- deterministic optimization before robust or stochastic extensions;
- simple clustering before representation learning;
- analytic, greedy, exact-enumeration, or DP baselines before metaheuristics.

Complexity should be justified by diagnostic evidence, improved validation, necessary realism or constraints, or a meaningful performance gain.

## Evidence taxonomy

- **L1:** in-sample fit.
- **L2:** internal consistency or sanity check.
- **L3:** perturbation or sensitivity evidence.
- **L4:** synthetic truth recovery.
- **L5:** independent real-world validation.

These are evidence categories, not a quality score. A pipeline may have different levels for different components, and L4 same-model recovery does not imply real-world validity.

## Per-model validation contract

For every major model define:

- validation target and claim being tested;
- data independence and available ground truth;
- baseline and comparison fairness;
- metric with units and aggregation;
- split, rolling window, experiment, or simulation design;
- repetitions and seeds for stochastic methods;
- sensitivity variables and ranges;
- expected failure cases;
- conclusion boundary if the test passes or fails.

Training R², training accuracy, objective decrease, visual agreement, or same-data model agreement remains L1/L2 unless independent evidence exists.

## Independence and comparison

- Split before preprocessing. Preserve time, group, subject, spatial, or experimental-unit boundaries.
- Hyperparameter/model selection requires a layer separate from final evaluation when data permit.
- Algorithms cross-check each other only when data, objective, constraints, feasible set, tolerances, and compute budget match.
- Same-model synthetic recovery is useful for code consistency but must disclose inverse-crime risk.
- For stochastic algorithms, report repeated outcomes, feasibility rate, distribution summaries, and convergence diagnostics.

## Sensitivity and robustness

Sensitivity changes inputs or parameters and measures output response. Robustness asks whether the substantive conclusion or decision survives relevant joint uncertainty, resampling, modeling choices, and scenarios.

Record parameter source, unit, baseline, range, sampling method, output metric, feasibility, and whether the decision changes. Expand bounds or report safety margin when a solution or parameter hits a boundary.

## Candidate comparison

Use a qualitative matrix such as:

| Criterion | Pipeline A | Pipeline B | Pipeline C |
|---|---|---|---|
| Fits problem structure | | | |
| Data requirement | | | |
| Interpretability | | | |
| Validation strength possible | | | |
| Robustness handling | | | |
| Implementation risk | | | |
| Computational cost | | | |
| Historical support and adaptation | | | |
| Major weakness | | | |

Use judgment rather than arbitrary weighted scoring unless formal multi-criteria selection is itself part of the current problem.
