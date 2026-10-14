# Evidence-Backed IDS Alert Explanation

## Decision transparency status

- **Evidence tier:** `SUPPORTED_FOR_THIS_ALERT`
- **Meaning:** The validated explainer also beat randomized rankings for this alert under the primary training median/mode intervention.
- **Black-box status:** mitigated with tested local evidence; not theoretically eliminated
- **Evidence scope:** primary training median/mode masking intervention
- **Required warning:** This report explains the fitted model under explicit masking tests. It is not a causal explanation and does not replace analyst review.

## Prediction

- Dataset/model context: CIC-IDS2017 / binary / random_forest
- Predicted class: **Attack**
- Predicted probability: **1.000000**
- Model seed: 42

Class probabilities:

- Attack: 1.000000
- Normal: 0.000000

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | Bwd Packet Length Std | 2544.918912 | 0.090114 | supports prediction |
| 2 | Bwd Packet Length Max | 5792 | 0.081169 | supports prediction |
| 3 | Packet Length Std | 1803.026788 | 0.064312 | supports prediction |
| 4 | Destination Port | 80 | 0.059749 | supports prediction |
| 5 | Bwd Packet Length Mean | 1938.666667 | 0.046061 | supports prediction |
| 6 | Init_Win_bytes_forward | 29200 | 0.042774 | supports prediction |
| 7 | Init_Win_bytes_backward | 235 | 0.034450 | supports prediction |
| 8 | Fwd Packet Length Min | 0 | 0.027556 | supports prediction |
| 9 | Average Packet Size | 853.7142857 | 0.020985 | supports prediction |
| 10 | Max Packet Length | 5792 | 0.017040 | supports prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.459569
- Bottom-ranked deletion score: 0.012597
- Mean of 200 random rankings: 0.136155
- Top-minus-random lift: 0.323414
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
