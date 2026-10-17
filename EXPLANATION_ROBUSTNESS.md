# Supplementary explanation robustness analysis

Completed 17 October 2026. This is an explicitly post-hoc extension of the recent GeNIS/Gotham study. The frozen primary experiment, directional tests, and manuscript PDF remain unchanged.

## Research question

Does the reported TreeSHAP deletion advantage persist when considering direction frequency rather than signed ranks, and can any single explained connection determine the sign of the mean advantage?

## Method

`run_explanation_robustness.py` reconstructs TreeSHAP-minus-LIME deletion differences from the original per-context fidelity files. It requires matched records, complete configured masking budgets, unique record/explainer/budget observations, finite scores, consistent connection identities, and the full 24-context design. It averages packets within each connection and masking budget, then averages the four budgets. Each connection receives equal weight. It verifies every reconstructed mean and group count against the primary comparison table before emitting results.

For each context, an exact two-sided binomial sign test evaluates equal probabilities of positive and negative differences among non-tied explained connections. Absolute differences at or below 1e-12 count as ties and are excluded from the binomial denominator. Holm correction covers all 24 sign tests as a separate exploratory family. The test targets direction frequency, not mean magnitude, and does not assume a symmetric distribution of difference magnitudes. It still relies on sufficiently independent group signs under its null. The implementation uses [SciPy's exact binomial test](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html).

The influence diagnostic removes each connection in turn and recomputes the equal-weight mean difference. The minimum and maximum leave-one-connection-out means and a sign-reversal flag are reported. This diagnostic measures single-connection sensitivity; it is not a confidence interval or evidence against joint influence by several connections.

## Completed results

All 24 reconstructed primary means and connection counts agree with the saved study. Mean differences favor TreeSHAP in all 24 contexts. All 24 sign tests favor TreeSHAP with Holm-adjusted p < 0.05. No context reverses the positive mean difference after removing any single explained connection.

These results support consistency of the measured advantage across the selected connections under this masking protocol. They do not establish a causal explanation measure, useful analyst decisions, a superior detector, or external generalization. The sign-test endpoint differs from the primary mean-deletion endpoint and should be reported alongside it rather than substituted for it.

## Manuscript-ready supplementary paragraph

In a post-hoc sensitivity analysis, we reconstructed the paired deletion endpoint from the saved explanation records and reproduced all 24 primary means and connection counts. An exact two-sided sign test on connection-level differences, excluding numerical ties within 1e-12 and applying Holm correction across 24 tests, favored TreeSHAP in every context (adjusted p < 0.05). Removing any single explained connection preserved a positive mean difference in every context. These checks address direction-frequency and single-connection influence sensitivity within the diagnostic cohort; they do not resolve cross-connection dependence, explanation-selection bias, or external validity.

## Reproduction and audit trail

Run `python run_explanation_robustness.py` in the pinned study environment, then `python -m unittest discover -s tests`. Outputs are `outputs/explanation_robustness/sensitivity.csv` and `outputs/explanation_robustness/manifest.json`. The manifest records SHA-256 hashes of the script, original manifest, primary comparison table, and all 24 fidelity inputs. Tests cover an influential outlier, exact sign probabilities, numerical ties, Holm correction, equal connection weighting, missing pairs, and duplicate observations. The full suite passed 21 tests when this supplement was prepared.

## Highest-value next study

The main remaining scientific limitation is the single preparation split. Model seeds vary fitting randomness while reusing that split. A new study should freeze its protocol before fitting, reserve an independently captured or device/scenario-separated cohort where source metadata permits, fit preprocessing exclusively on training data, and lock model and explanation settings before evaluating the new holdout. Do not tune the new study against the current final-test results. Neither this supplementary analysis nor another fit seed supplies independent capture evidence.
