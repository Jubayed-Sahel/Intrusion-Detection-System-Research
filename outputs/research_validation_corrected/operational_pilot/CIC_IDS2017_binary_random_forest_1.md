# Evidence-Backed IDS Alert Explanation

## Decision transparency status

- **Evidence tier:** `REVIEW_REQUIRED`
- **Meaning:** The explainer passed globally, but this alert did not clear the strict local random-ranking test.
- **Black-box status:** mitigated with tested local evidence; not theoretically eliminated
- **Evidence scope:** primary training median/mode masking intervention
- **Required warning:** This report explains the fitted model under explicit masking tests. It is not a causal explanation and does not replace analyst review.

## Prediction

- Dataset/model context: CIC-IDS2017 / binary / random_forest
- Predicted class: **Attack**
- Predicted probability: **0.999958**
- Model seed: 42

Class probabilities:

- Attack: 0.999958
- Normal: 0.000042

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | PSH Flag Count | 1 | 0.080811 | supports prediction |
| 2 | Average Packet Size | 5.0 | 0.067462 | supports prediction |
| 3 | Destination Port | 1121 | -0.059555 | opposes prediction |
| 4 | Packet Length Std | 2.309401077 | 0.054967 | supports prediction |
| 5 | Fwd Packet Length Max | 2 | 0.047785 | supports prediction |
| 6 | Fwd Packet Length Min | 2 | 0.044125 | supports prediction |
| 7 | Packet Length Mean | 3.333333333 | 0.039200 | supports prediction |
| 8 | Init_Win_bytes_forward | 1024 | 0.038278 | supports prediction |
| 9 | Total Length of Fwd Packets | 2 | 0.037870 | supports prediction |
| 10 | Max Packet Length | 6 | 0.029022 | supports prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.223448
- Bottom-ranked deletion score: 0.119677
- Mean of 200 random rankings: 0.292264
- Top-minus-random lift: -0.068817
- Empirical one-sided local p-value: 0.751244

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
