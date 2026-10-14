# Evidence-Backed IDS Alert Explanation

## Decision transparency status

- **Evidence tier:** `REVIEW_REQUIRED`
- **Meaning:** The explainer passed globally, but this alert did not clear the strict local random-ranking test.
- **Black-box status:** mitigated with tested local evidence; not theoretically eliminated
- **Evidence scope:** primary training median/mode masking intervention
- **Required warning:** This report explains the fitted model under explicit masking tests. It is not a causal explanation and does not replace analyst review.

## Prediction

- Dataset/model context: CIC-IDS2017 / binary / xgboost
- Predicted class: **Attack**
- Predicted probability: **0.999081**
- Model seed: 42

Class probabilities:

- Attack: 0.999081
- Normal: 0.000919

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | Bwd Packets/s | 21739.13043 | 2.469852 | supports prediction |
| 2 | PSH Flag Count | 1 | 0.938335 | supports prediction |
| 3 | Init_Win_bytes_forward | 1024 | 0.922367 | supports prediction |
| 4 | Packet Length Std | 2.309401077 | 0.711737 | supports prediction |
| 5 | Total Length of Fwd Packets | 2 | 0.653734 | supports prediction |
| 6 | Flow IAT Mean | 46.0 | 0.369234 | supports prediction |
| 7 | Destination Port | 1121 | -0.318860 | opposes prediction |
| 8 | Bwd Packet Length Mean | 6.0 | 0.253180 | supports prediction |
| 9 | Fwd Packet Length Min | 2 | 0.238334 | supports prediction |
| 10 | Flow IAT Max | 46 | 0.226744 | supports prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.523770
- Bottom-ranked deletion score: 0.003771
- Mean of 200 random rankings: 0.160748
- Top-minus-random lift: 0.363022
- Empirical one-sided local p-value: 0.059701

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
