# Evidence-Backed IDS Alert Explanation

## Decision transparency status

- **Evidence tier:** `SUPPORTED_FOR_THIS_ALERT`
- **Meaning:** The validated explainer also beat randomized rankings for this alert under the primary training median/mode intervention.
- **Black-box status:** mitigated with tested local evidence; not theoretically eliminated
- **Evidence scope:** primary training median/mode masking intervention
- **Required warning:** This report explains the fitted model under explicit masking tests. It is not a causal explanation and does not replace analyst review.

## Prediction

- Dataset/model context: UNSW-NB15 / binary / random_forest
- Predicted class: **Attack**
- Predicted probability: **0.760262**
- Model seed: 42

Class probabilities:

- Attack: 0.760262
- Normal: 0.239738

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | ackdat | 0.191876 | 0.087430 | supports prediction |
| 2 | smean | 1137 | 0.042427 | supports prediction |
| 3 | tcprtt | 0.357506 | 0.024331 | supports prediction |
| 4 | ct_flw_http_mthd | 1 | 0.024223 | supports prediction |
| 5 | synack | 0.16563 | 0.022426 | supports prediction |
| 6 | dinpkt | 129.47916 | 0.019180 | supports prediction |
| 7 | dload | 2462.047 | 0.018266 | supports prediction |
| 8 | dur | 1.848868 | 0.016020 | supports prediction |
| 9 | rate | 39.48362 | 0.014842 | supports prediction |
| 10 | sloss | 27 | -0.013895 | opposes prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.383095
- Bottom-ranked deletion score: 0.046276
- Mean of 200 random rankings: 0.070303
- Top-minus-random lift: 0.312792
- Empirical one-sided local p-value: 0.004975

The deletion score is the mean predicted-probability drop after replacing the top 1, 3, 5, and 10 features with training-derived baseline values.

## Benchmark validation context

- TreeSHAP passed corrected random control: True
- Mean top-minus-random lift: 0.195496
- 95% bootstrap interval: [0.099003, 0.293926]
- Holm-adjusted p-value: 0.001583
- Mean neighbor cosine stability: 0.796288
- Mean top-5 neighbor overlap: 0.610813
- Median/P95 explanation latency: 107.986 / 143.526 ms

Mean TreeSHAP deletion scores from the separate reference-sensitivity audit:

- marginal_training_row: 0.185343
- nearest_opposite_prediction: 0.177086
- nearest_same_prediction: -0.020485
- training_median_mode: 0.242833
- zero: 0.239438

## Interpretation rule

- `SUPPORTED_FOR_THIS_ALERT`: benchmark control passed and this alert beats randomized rankings at empirical p <= 0.05.
- `REVIEW_REQUIRED`: benchmark control passed, but the alert-specific ranking did not clear the strict local test.
- `UNSUPPORTED`: the explainer failed benchmark-level validation.

This report makes the model's decision auditable and tests whether its stated evidence changes the model output under a declared intervention. It does not claim causal truth, intervention-invariant fidelity, complete human comprehension, or immunity to dataset shift.
