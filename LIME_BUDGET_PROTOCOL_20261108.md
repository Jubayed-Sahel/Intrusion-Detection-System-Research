# Controlled LIME budget sensitivity protocol

**Frozen before this new computation:** 8 November 2026 (Asia/Dhaka).

This exploratory extension evaluates whether the primary TreeSHAP–LIME deletion comparison depends on LIME's simulation budget. It does not replace, reproduce exactly, or modify the primary experiment. The original primary LIME run used a sequential RNG schedule with a warmed explainer; the controlled new runs below use fresh explainers and per-record seeds.

## Inputs and contrasts

- Use the eight saved seed-42 models: GeNIS/Gotham × binary/multiclass × Random Forest/XGBoost. Do not refit or tune models.
- Retain the same 100 diagnostic source-test indices per context as the original seed-42 TreeSHAP and LIME outputs. Read original attributions using round-trip CSV precision. Verify feature identity, class target, and saved-model predictions.
- Reuse each saved training-only preprocessor. The LIME background contains at most 5,000 training rows selected with `stratified_indices(model.predict(x_train), min(5000, len(x_train)), 42)`, as in the primary implementation.
- Explain the original predicted class with all prepared features and the primary LIME defaults (continuous discretization, sample-around-instance, classification probability prediction). For every record create a fresh LIME explainer at each of 350 and 3,500 perturbations. Both budgets receive the same deterministic per-record/context seed. Seeds are paired; generated samples are not claimed to form nested prefixes.
- Compare each controlled LIME ranking with the **saved original TreeSHAP ranking**. Rank by absolute attribution as in the primary endpoint. Use the saved training median/mode mask and budgets 1, 3, 5, 10, retaining signed probability drops. No timing claim is made.
- Save LIME's weighted surrogate R² (`explanation.score`), local surrogate prediction, original predicted-class probability, and absolute local prediction error. These are descriptive fit measures, not causal validity or a convergence certificate.

## Endpoint, inference, and reporting

Within each context, average records within each connection and masking budget, then budgets, leaving equal weight per explained connection. Evaluate exactly 16 two-sided contrasts in one Holm family: eight TreeSHAP-minus-controlled-LIME-3500 and eight controlled-LIME-3500-minus-controlled-LIME-350. Report every contrast, including null results and reversals.

Use 2,000 paired connection-group percentile bootstrap resamples for descriptive 95% intervals and exact two-sided sign tests excluding differences with absolute magnitude at most 1e-12. Bootstrap seeds are deterministic by context and contrast. Intervals are per-contrast, not simultaneous. Sign tests avoid a symmetry assumption on magnitudes but still require suitable independence of connections, which can fail within shared campaigns. Model fitting seeds are not additional independent datasets.

Compare controlled LIME fit measures and deletion effects descriptively; a result at 3,500 draws is not proof of convergence. This is a post-hoc robustness family with a protocol fixed before its computation, not a preregistered confirmatory study or independent dataset replication. Source hashes, package versions, protocol/source snapshots, inputs, checkpoint completion, raw attributions, raw deletion measurements, fit measures, group endpoints, and complete contrasts are retained under `outputs/lime_budget_20261108/`.

The existing primary artifacts, model files, source snapshots, and saved statistics remain unchanged. In-memory prediction worker counts may be reduced to one to share the local machine; this extension makes no runtime comparison.
