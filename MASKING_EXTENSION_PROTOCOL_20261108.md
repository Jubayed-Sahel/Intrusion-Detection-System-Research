# Paired replacement sensitivity protocol — 8 November 2026

This protocol is written before execution of the extension. It is an exploratory,
post-hoc sensitivity analysis; the original primary endpoint, results and hypotheses
remain frozen. The purpose is to test whether the comparison of saved TreeSHAP and
LIME rankings changes when removed predictors receive a different replacement.
No classifier, explanation, preprocessing parameter or diagnostic record is tuned.

## Fixed inputs and comparison

- Use the eight saved seed-42 classifiers: two datasets, binary/multiclass tasks,
  and Random Forest/XGBoost. Reuse **all 100 matched diagnostic records** and both
  complete attribution vectors from each original context. These records were
  selected for diagnostic coverage and do not estimate deployment prevalence.
- Rank features by absolute attribution using the original NumPy ordering.
  Explain the original predicted class and retain masking budgets 1, 3, 5 and 10.
- Use the saved training-only preprocessor and prepared input files. Record
  checksums of code, protocol, models, input parquets and attribution/fidelity CSVs.
- Original training median/mode replacement must reproduce the saved per-record
  deletion results within floating-point tolerance before the extension proceeds.

## Three replacement schemes

1. **Training median/mode:** the original deterministic reference.
2. **Empirical joint donor:** uniformly sample 32 distinct donor rows from a fixed,
   uniformly sampled pool of at most 5,000 training rows. Use identical donor draws
   for both explainers and all masking budgets of a given diagnostic record. Copy
   all removed feature values jointly from each donor; average the 32 resulting
   target-class probabilities before computing the probability drop.
3. **Retained-feature nearest donor:** from the same training pool choose 32 donors
   nearest to the diagnostic record using only its *retained* predictors. Average
   absolute numeric differences scaled by training IQR and capped at one;
   if IQR is zero use training standard deviation, then one if still constant.
   Categorical predictors declared by the saved preprocessor contribute zero/one
   mismatch. Each retained predictor has equal weight. Distance ties use the fixed
   shuffled pool order. No target labels or classifier outputs enter selection.
   Copy removed predictors jointly from these rows and average probabilities.

The uniform pool seed is 20261108 per dataset, and per-record empirical donor seeds
are generated reproducibly from this seed, context identity and test-row index.
The nearest-donor scheme is an **approximate conditioning sensitivity**, not a
validated conditional generative model. Numerical distance does not establish
semantic similarity for ports or other encoded numerical fields. Copying observed
joint values among removed predictors preserves their donor combinations but may
still create incompatible retained/removed combinations. None of the schemes
establishes causal intervention validity or guarantees network-realizable records.

## Endpoint and exploratory inference

Within each connection and budget average record-level TreeSHAP-minus-LIME drops;
then average the four budgets, and give each explained connection equal weight.
Retain per-record and per-connection values, donor identities, and distance summaries.
For each of the 8 contexts × 3 schemes report the mean/median paired difference,
2,000 connection-resampled percentile bootstrap interval, two-sided exact sign test
(exclude ties of absolute size ≤ 1e-12), and Holm adjustment over these **24** tests.
The sign test targets direction frequency, not the mean magnitude. This new family
does not replace the primary directional Wilcoxon family. Bootstrap intervals are
pointwise and do not have simultaneous family coverage. Shared source scenarios and
diagnostic sampling can leave dependence beyond a connection; no external or causal
generalization is claimed. Descriptive mean differences between schemes are not a
new confirmatory test. Conclusions must report reversals or reduced consistency,
including null findings, without selecting the best scheme.

## Reproducibility and completion

`run_masking_extension.py` writes only `outputs/masking_extension_20261108/`.
It fails on incomplete pairing, feature mismatch, missing original budgets,
non-finite values, model/attribution prediction disagreement, or failure of reference
reproduction. Meaningful unit tests check donor pairing, retained-feature-only
selection, group weighting, and inference/validation edge cases. A complete manifest
is written only after all eight contexts and all 24 comparisons are available.
