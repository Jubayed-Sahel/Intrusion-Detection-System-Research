# Evidence-Backed IDS Alert Explanation

## Decision transparency status

- **Evidence tier:** `SUPPORTED_FOR_THIS_ALERT`
- **Meaning:** The validated explainer also beat randomized rankings for this alert under the primary training median/mode intervention.
- **Black-box status:** mitigated with tested local evidence; not theoretically eliminated
- **Evidence scope:** primary training median/mode masking intervention
- **Required warning:** This report explains the fitted model under explicit masking tests. It is not a causal explanation and does not replace analyst review.

## Prediction

- Dataset/model context: CIC-IDS2017 / multiclass / xgboost
- Predicted class: **DoS GoldenEye**
- Predicted probability: **0.999813**
- Model seed: 42

Class probabilities:

- BENIGN: 0.000066
- Bot: 0.000002
- DDoS: 0.000003
- DoS GoldenEye: 0.999813
- DoS Hulk: 0.000017
- DoS Slowhttptest: 0.000034
- DoS slowloris: 0.000025
- FTP-Patator: 0.000003
- Heartbleed: 0.000002
- Infiltration: 0.000003
- PortScan: 0.000004
- SSH-Patator: 0.000002
- Web Attack - Brute Force: 0.000014
- Web Attack - Sql Injection: 0.000004
- Web Attack - XSS: 0.000010

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | Idle Mean | 10100000.0 | 1.716646 | supports prediction |
| 2 | Total Length of Bwd Packets | 11632 | 1.311928 | supports prediction |
| 3 | Bwd Packet Length Max | 8688 | 0.836514 | supports prediction |
| 4 | Bwd Packet Length Std | 3777.823289 | 0.690101 | supports prediction |
| 5 | Init_Win_bytes_backward | 235 | 0.684587 | supports prediction |
| 6 | Bwd Packets/s | 0.313776443 | 0.375020 | supports prediction |
| 7 | Fwd IAT Std | 3338454.698 | 0.288422 | supports prediction |
| 8 | Bwd Packet Length Mean | 2326.4 | 0.278681 | supports prediction |
| 9 | Average Packet Size | 881.8666667 | 0.260823 | supports prediction |
| 10 | Flow Bytes/s | 830.1269565 | 0.241097 | supports prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.637864
- Bottom-ranked deletion score: 0.000068
- Mean of 200 random rankings: 0.073092
- Top-minus-random lift: 0.564772
- Empirical one-sided local p-value: 0.004975

The deletion score is the mean predicted-probability drop after replacing the top 1, 3, 5, and 10 features with training-derived baseline values.

## Benchmark validation context

- TreeSHAP passed corrected random control: True
- Mean top-minus-random lift: 0.352548
- 95% bootstrap interval: [0.257835, 0.446852]
- Holm-adjusted p-value: 0.000000
- Mean neighbor cosine stability: 0.916253
- Mean top-5 neighbor overlap: 0.730159
- Median/P95 explanation latency: 10.188 / 11.738 ms

Mean TreeSHAP deletion scores from the separate reference-sensitivity audit:

- marginal_training_row: 0.671102
- nearest_opposite_prediction: 0.500330
- nearest_same_prediction: -0.010093
- training_median_mode: 0.636995
- zero: 0.627432

## Interpretation rule

- `SUPPORTED_FOR_THIS_ALERT`: benchmark control passed and this alert beats randomized rankings at empirical p <= 0.05.
- `REVIEW_REQUIRED`: benchmark control passed, but the alert-specific ranking did not clear the strict local test.
- `UNSUPPORTED`: the explainer failed benchmark-level validation.

This report makes the model's decision auditable and tests whether its stated evidence changes the model output under a declared intervention. It does not claim causal truth, intervention-invariant fidelity, complete human comprehension, or immunity to dataset shift.
