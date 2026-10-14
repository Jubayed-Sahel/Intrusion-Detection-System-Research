# Evidence-Backed IDS Alert Explanation

## Decision transparency status

- **Evidence tier:** `SUPPORTED_FOR_THIS_ALERT`
- **Meaning:** The validated explainer also beat randomized rankings for this alert under the primary training median/mode intervention.
- **Black-box status:** mitigated with tested local evidence; not theoretically eliminated
- **Evidence scope:** primary training median/mode masking intervention
- **Required warning:** This report explains the fitted model under explicit masking tests. It is not a causal explanation and does not replace analyst review.

## Prediction

- Dataset/model context: CIC-IDS2017 / multiclass / random_forest
- Predicted class: **PortScan**
- Predicted probability: **0.999975**
- Model seed: 42

Class probabilities:

- BENIGN: 0.000025
- Bot: 0.000000
- DDoS: 0.000000
- DoS GoldenEye: 0.000000
- DoS Hulk: 0.000000
- DoS Slowhttptest: 0.000000
- DoS slowloris: 0.000000
- FTP-Patator: 0.000000
- Heartbleed: 0.000000
- Infiltration: 0.000000
- PortScan: 0.999975
- SSH-Patator: 0.000000
- Web Attack - Brute Force: 0.000000
- Web Attack - Sql Injection: 0.000000
- Web Attack - XSS: 0.000000

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | Flow Bytes/s | 195121.9512 | 0.090034 | supports prediction |
| 2 | Bwd Packets/s | 24390.2439 | 0.082480 | supports prediction |
| 3 | Init_Win_bytes_backward | 0 | 0.081292 | supports prediction |
| 4 | Packet Length Mean | 3.333333333 | 0.077523 | supports prediction |
| 5 | Total Length of Fwd Packets | 2 | 0.073573 | supports prediction |
| 6 | Flow IAT Mean | 41.0 | 0.053963 | supports prediction |
| 7 | Fwd Packet Length Max | 2 | 0.051736 | supports prediction |
| 8 | Average Packet Size | 5.0 | 0.044921 | supports prediction |
| 9 | Flow Duration | 41 | 0.042755 | supports prediction |
| 10 | PSH Flag Count | 1 | 0.034031 | supports prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.625296
- Bottom-ranked deletion score: 0.065303
- Mean of 200 random rankings: 0.377170
- Top-minus-random lift: 0.248126
- Empirical one-sided local p-value: 0.009950

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
