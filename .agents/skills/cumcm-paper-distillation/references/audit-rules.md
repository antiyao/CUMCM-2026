# Prototype-specific Audit Rules

Apply only the sections matching the paper. A hybrid paper may require several sections.

## Statistical and regression models

- Compare sample size, parameter count, residual degrees of freedom, and effective sample size.
- Check residual assumptions, heteroscedasticity, multicollinearity, leverage/outliers, and whether deletion is evaluated on the same data.
- Check leakage, train/test independence, significance interpretation, multiplicity, and uncertainty intervals.
- Do not treat response marginal non-normality as proof that regression is invalid; inspect conditional residuals or posterior predictive behavior.
- Distinguish statistical significance, effect size, calibration error, and predictive performance.

## Forecasting and time-series models

- Establish data frequency, chronological split, forecast horizon, and whether the reported sample window is internally consistent.
- Look for rolling-origin/walk-forward validation, prediction intervals, stable lag selection, stationarity/cointegration when relevant, and forecast baselines.
- Check leakage from future covariates or full-period preprocessing.
- Track nonnegative or constrained outputs and how forecast uncertainty propagates into downstream decisions.

## Machine-learning models

- Record train/validation/test structure, class imbalance, leakage controls, baseline comparison, hyperparameter-selection data, repeated validation, and metric suitability.
- Verify that preprocessing and feature selection are fitted only on training data.
- Do not use accuracy alone for materially imbalanced classes.

## Inverse problems

- Check identifiability, initialization, bounds, forward/reprojection consistency, synthetic recovery, noise robustness, and uncertainty propagation.
- Mark synthetic recovery as `synthetic-same-model` when forward and inverse procedures share the model; state inverse-crime risk.
- Distinguish recovery of parameters from validation of the reconstructed target.

## Simulation

- Record parameter calibration, time/space resolution, initialization, boundary conditions, repetitions, random seed, convergence, and scenario coverage.
- Do not accept simulated outputs as independent validation of the same model that generated them.
- Separate qualitative visualization from quantitative validation.

## Optimization

- Reconstruct the objective, variables, bounds, constraints, solver settings, initialization, stopping rule, and reported solution status.
- Check feasibility and whether the optimum is a trivial boundary solution.
- Distinguish analytic/global optimality from heuristic best-found solutions.
- When algorithms are compared, verify that they solve the same objective and feasible set.
- Check sensitivity and robust/scenario formulations when inputs are uncertain.

## Multi-criteria evaluation

- Verify indicator direction, units, normalization, missing-data treatment, weight derivation, and whether weights are subjective or objective.
- Recompute weight sums and simple rankings where possible.
- Check weight sensitivity and whether ranking conclusions match reported scores.

## Cross-cutting numerical checks

- Units and dimensional consistency.
- Percent/ratio conversions and denominator choice.
- Degrees of freedom and parameter counts.
- Matrix/vector dimensions and indexing.
- Inequality directions and signs.
- Counts that should reconcile across text, tables, figures, and code.
- Reported errors versus independent calculations.
- Objective/constraint formulas versus implementation.
- Formula/code/result consistency.
- Claimed robustness versus actual perturbation magnitude and repetitions.
