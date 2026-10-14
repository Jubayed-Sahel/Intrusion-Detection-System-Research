# Evidence-Backed IDS Alert Explanation

## Decision transparency status

- **Evidence tier:** `SUPPORTED_FOR_THIS_ALERT`
- **Meaning:** The validated explainer also beat randomized rankings for this alert under the primary training median/mode intervention.
- **Black-box status:** mitigated with tested local evidence; not theoretically eliminated
- **Evidence scope:** primary training median/mode masking intervention
- **Required warning:** This report explains the fitted model under explicit masking tests. It is not a causal explanation and does not replace analyst review.

## Prediction

- Dataset/model context: CIC-IDS2017 / multiclass / random_forest
- Predicted class: **DoS GoldenEye**
- Predicted probability: **1.000000**
- Model seed: 42

Class probabilities:

- BENIGN: 0.000000
- Bot: 0.000000
- DDoS: 0.000000
- DoS GoldenEye: 1.000000
- DoS Hulk: 0.000000
- DoS Slowhttptest: 0.000000
- DoS slowloris: 0.000000
- FTP-Patator: 0.000000
- Heartbleed: 0.000000
- Infiltration: 0.000000
- PortScan: 0.000000
- SSH-Patator: 0.000000
- Web Attack - Brute Force: 0.000000
- Web Attack - Sql Injection: 0.000000
- Web Attack - XSS: 0.000000

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | Bwd Packet Length Std | 3777.823289 | 0.086248 | supports prediction |
| 2 | Bwd Packet Length Max | 8688 | 0.080384 | supports prediction |
| 3 | Init_Win_bytes_backward | 235 | 0.057879 | supports prediction |
| 4 | Init_Win_bytes_forward | 29200 | 0.055249 | supports prediction |
| 5 | Max Packet Length | 8688 | 0.052554 | supports prediction |
| 6 | Packet Length Std | 2218.844068 | 0.050117 | supports prediction |
| 7 | Fwd Packet Length Max | 399 | 0.046995 | supports prediction |
| 8 | Total Length of Bwd Packets | 11632 | 0.045685 | supports prediction |
| 9 | Bwd Packet Length Mean | 2326.4 | 0.045157 | supports prediction |
| 10 | Destination Port | 80 | 0.043160 | supports prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.690628
- Bottom-ranked deletion score: 0.095991
- Mean of 200 random rankings: 0.384015
- Top-minus-random lift: 0.306612
- Empirical one-sided local p-value: 0.004975

The deletion score is the mean predicted-probability drop after replacing the top 1, 3, 5, and 10 features with training-derived baseline values.

## Benchmark validation context

- TreeSHAP passed corrected random control: True
- Mean top-minus-random lift: 0.267575
- 95% bootstrap interval: [0.228332, 0.305371]
- Holm-adjusted p-value: 0.000000
- Mean neighbor cosine stability: 0.946510
- Mean top-5 neighbor overlap: 0.711718
- Median/P95 explanation latency: 32.940 / 35.582 ms

Mean TreeSHAP deletion scores from the separate reference-sensitivity audit:

- marginal_training_row: 0.680172
- nearest_opposite_prediction: 0.445259
- nearest_same_prediction: 0.020323
- training_median_mode: 0.682073
- zero: 0.575946

## Interpretation rule

- `SUPPORTED_FOR_THIS_ALERT`: benchmark control passed and this alert beats randomized rankings at empirical p <= 0.05.
- `REVIEW_REQUIRED`: benchmark control passed, but the alert-specific ranking did not clear the strict local test.
- `UNSUPPORTED`: the explainer failed benchmark-level validation.

This report makes the model's decision auditable and tests whether its stated evidence changes the model output under a declared intervention. It does not claim causal truth, intervention-invariant fidelity, complete human comprehension, or immunity to dataset shift.
