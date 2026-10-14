# Evidence-Backed IDS Alert Explanation

## Decision transparency status

- **Evidence tier:** `SUPPORTED_FOR_THIS_ALERT`
- **Meaning:** The validated explainer also beat randomized rankings for this alert under the primary training median/mode intervention.
- **Black-box status:** mitigated with tested local evidence; not theoretically eliminated
- **Evidence scope:** primary training median/mode masking intervention
- **Required warning:** This report explains the fitted model under explicit masking tests. It is not a causal explanation and does not replace analyst review.

## Prediction

- Dataset/model context: CIC-IDS2017 / binary / xgboost
- Predicted class: **Attack**
- Predicted probability: **0.999930**
- Model seed: 42

Class probabilities:

- Attack: 0.999930
- Normal: 0.000070

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | Bwd Packet Length Std | 2544.918912 | 4.326296 | supports prediction |
| 2 | Destination Port | 80 | 1.819842 | supports prediction |
| 3 | Init_Win_bytes_forward | 29200 | 1.418892 | supports prediction |
| 4 | Init_Win_bytes_backward | 235 | 1.270743 | supports prediction |
| 5 | Flow Duration | 12435266 | 0.614271 | supports prediction |
| 6 | Bwd Packets/s | 0.482498726 | -0.427139 | opposes prediction |
| 7 | Total Fwd Packets | 8 | 0.341569 | supports prediction |
| 8 | Bwd Packet Length Mean | 1938.666667 | -0.261158 | opposes prediction |
| 9 | Packet Length Std | 1803.026788 | 0.248037 | supports prediction |
| 10 | Flow IAT Max | 7430112 | -0.230982 | opposes prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.305844
- Bottom-ranked deletion score: 0.000010
- Mean of 200 random rankings: 0.011571
- Top-minus-random lift: 0.294273
- Empirical one-sided local p-value: 0.009950

The deletion score is the mean predicted-probability drop after replacing the top 1, 3, 5, and 10 features with training-derived baseline values.

## Benchmark validation context

- TreeSHAP passed corrected random control: True
- Mean top-minus-random lift: 0.167747
- 95% bootstrap interval: [0.112102, 0.230170]
- Holm-adjusted p-value: 0.000001
- Mean neighbor cosine stability: 0.877756
- Mean top-5 neighbor overlap: 0.759425
- Median/P95 explanation latency: 1.553 / 1.815 ms

Mean TreeSHAP deletion scores from the separate reference-sensitivity audit:

- marginal_training_row: 0.237470
- nearest_opposite_prediction: 0.266406
- nearest_same_prediction: -0.046890
- training_median_mode: 0.302206
- zero: 0.421755

## Interpretation rule

- `SUPPORTED_FOR_THIS_ALERT`: benchmark control passed and this alert beats randomized rankings at empirical p <= 0.05.
- `REVIEW_REQUIRED`: benchmark control passed, but the alert-specific ranking did not clear the strict local test.
- `UNSUPPORTED`: the explainer failed benchmark-level validation.

This report makes the model's decision auditable and tests whether its stated evidence changes the model output under a declared intervention. It does not claim causal truth, intervention-invariant fidelity, complete human comprehension, or immunity to dataset shift.
