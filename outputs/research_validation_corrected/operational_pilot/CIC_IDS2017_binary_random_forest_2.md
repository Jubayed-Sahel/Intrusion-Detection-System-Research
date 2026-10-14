# Evidence-Backed IDS Alert Explanation

## Decision transparency status

- **Evidence tier:** `SUPPORTED_FOR_THIS_ALERT`
- **Meaning:** The validated explainer also beat randomized rankings for this alert under the primary training median/mode intervention.
- **Black-box status:** mitigated with tested local evidence; not theoretically eliminated
- **Evidence scope:** primary training median/mode masking intervention
- **Required warning:** This report explains the fitted model under explicit masking tests. It is not a causal explanation and does not replace analyst review.

## Prediction

- Dataset/model context: CIC-IDS2017 / binary / random_forest
- Predicted class: **Normal**
- Predicted probability: **0.999897**
- Model seed: 42

Class probabilities:

- Attack: 0.000103
- Normal: 0.999897

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | Destination Port | 58478 | 0.133785 | supports prediction |
| 2 | Packet Length Std | 0.0 | 0.037279 | supports prediction |
| 3 | Average Packet Size | 9.0 | 0.036338 | supports prediction |
| 4 | PSH Flag Count | 0 | 0.034513 | supports prediction |
| 5 | Init_Win_bytes_backward | -1 | 0.028534 | supports prediction |
| 6 | Bwd Packet Length Std | 0.0 | 0.024454 | supports prediction |
| 7 | Flow IAT Std | 0.0 | 0.022761 | supports prediction |
| 8 | Bwd Packet Length Max | 0 | 0.022153 | supports prediction |
| 9 | Bwd Packet Length Mean | 0.0 | 0.021455 | supports prediction |
| 10 | Flow Duration | 3 | 0.017851 | supports prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.264810
- Bottom-ranked deletion score: 0.035636
- Mean of 200 random rankings: 0.086719
- Top-minus-random lift: 0.178092
- Empirical one-sided local p-value: 0.004975

The deletion score is the mean predicted-probability drop after replacing the top 1, 3, 5, and 10 features with training-derived baseline values.

## Benchmark validation context

- TreeSHAP passed corrected random control: True
- Mean top-minus-random lift: 0.113034
- 95% bootstrap interval: [0.078138, 0.150025]
- Holm-adjusted p-value: 0.000005
- Mean neighbor cosine stability: 0.901507
- Mean top-5 neighbor overlap: 0.714087
- Median/P95 explanation latency: 15.861 / 17.196 ms

Mean TreeSHAP deletion scores from the separate reference-sensitivity audit:

- marginal_training_row: 0.338283
- nearest_opposite_prediction: 0.305439
- nearest_same_prediction: 0.002478
- training_median_mode: 0.304345
- zero: 0.372750

## Interpretation rule

- `SUPPORTED_FOR_THIS_ALERT`: benchmark control passed and this alert beats randomized rankings at empirical p <= 0.05.
- `REVIEW_REQUIRED`: benchmark control passed, but the alert-specific ranking did not clear the strict local test.
- `UNSUPPORTED`: the explainer failed benchmark-level validation.

This report makes the model's decision auditable and tests whether its stated evidence changes the model output under a declared intervention. It does not claim causal truth, intervention-invariant fidelity, complete human comprehension, or immunity to dataset shift.
