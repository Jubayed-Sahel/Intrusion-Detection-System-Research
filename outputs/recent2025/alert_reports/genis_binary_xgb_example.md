# Evidence-Backed IDS Alert Explanation

## Decision transparency status

- **Evidence tier:** `SUPPORTED_FOR_THIS_ALERT`
- **Meaning:** The validated explainer also beat randomized rankings for this alert under the primary training median/mode intervention.
- **Black-box status:** mitigated with tested local evidence; not theoretically eliminated
- **Evidence scope:** primary training median/mode masking intervention
- **Required warning:** This report explains the fitted model under explicit masking tests. It is not a causal explanation and does not replace analyst review.

## Prediction

- Dataset/model context: GeNIS2025 / binary / xgboost
- Predicted class: **Normal**
- Predicted probability: **0.999945**
- Model seed: 42

Class probabilities:

- Attack: 0.000055
- Normal: 0.999945

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | dHops | 14.0 | 3.930561 | supports prediction |
| 2 | State | CON | 2.259258 | supports prediction |
| 3 | sMinPktSz | 88.0 | 0.681364 | supports prediction |
| 4 | SAppBytes | 46 | 0.587619 | supports prediction |
| 5 | dMinPktSz | 178.0 | 0.419900 | supports prediction |
| 6 | SrcWin | None | 0.401129 | supports prediction |
| 7 | Rate | 153.374237 | 0.314872 | supports prediction |
| 8 | Dur | 0.00652 | 0.270631 | supports prediction |
| 9 | Dport | 53.0 | 0.269586 | supports prediction |
| 10 | dMeanPktSz | 178.0 | 0.197374 | supports prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.016500
- Bottom-ranked deletion score: 0.000000
- Mean of 200 random rankings: 0.000092
- Top-minus-random lift: 0.016408
- Empirical one-sided local p-value: 0.004975

The deletion score is the mean predicted-probability drop after replacing the top 1, 3, 5, and 10 features with training-derived baseline values.

## Benchmark validation context

- TreeSHAP passed corrected random control: True
- Mean top-minus-random lift: 0.393161
- 95% bootstrap interval: [0.344900, 0.436143]
- Holm-adjusted p-value: 0.000000
- Inference unit: explained connection-group mean
- Explained inference units: 93
- Mean neighbor cosine stability: 0.954950
- Mean top-5 neighbor overlap: 0.885000
- Median/P95 explanation latency: 1.046 / 1.445 ms

Mean TreeSHAP deletion scores from the separate reference-sensitivity audit:

- marginal_training_row: 0.229178
- nearest_opposite_prediction: 0.564812
- nearest_same_prediction: -0.002230
- training_median_mode: 0.415154
- zero: 0.068175

## Interpretation rule

- `SUPPORTED_FOR_THIS_ALERT`: benchmark control passed and this alert beats randomized rankings at empirical p <= 0.05.
- `REVIEW_REQUIRED`: benchmark control passed, but the alert-specific ranking did not clear the strict local test.
- `UNSUPPORTED`: the explainer failed benchmark-level validation.

This report makes the model's decision auditable and tests whether its stated evidence changes the model output under a declared intervention. It does not claim causal truth, intervention-invariant fidelity, complete human comprehension, or immunity to dataset shift.
