# Evidence-Backed IDS Alert Explanation

## Decision transparency status

- **Evidence tier:** `SUPPORTED_FOR_THIS_ALERT`
- **Meaning:** The validated explainer also beat randomized rankings for this alert under the primary training median/mode intervention.
- **Black-box status:** mitigated with tested local evidence; not theoretically eliminated
- **Evidence scope:** primary training median/mode masking intervention
- **Required warning:** This report explains the fitted model under explicit masking tests. It is not a causal explanation and does not replace analyst review.

## Prediction

- Dataset/model context: CIC-IDS2017 / multiclass / xgboost
- Predicted class: **PortScan**
- Predicted probability: **0.999509**
- Model seed: 42

Class probabilities:

- BENIGN: 0.000089
- Bot: 0.000003
- DDoS: 0.000006
- DoS GoldenEye: 0.000004
- DoS Hulk: 0.000009
- DoS Slowhttptest: 0.000011
- DoS slowloris: 0.000017
- FTP-Patator: 0.000004
- Heartbleed: 0.000002
- Infiltration: 0.000002
- PortScan: 0.999509
- SSH-Patator: 0.000309
- Web Attack - Brute Force: 0.000012
- Web Attack - Sql Injection: 0.000009
- Web Attack - XSS: 0.000012

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | Bwd Packets/s | 24390.2439 | 3.442180 | supports prediction |
| 2 | PSH Flag Count | 1 | 0.799212 | supports prediction |
| 3 | Init_Win_bytes_backward | 0 | 0.791952 | supports prediction |
| 4 | Flow Duration | 41 | 0.630354 | supports prediction |
| 5 | Flow Bytes/s | 195121.9512 | 0.543775 | supports prediction |
| 6 | Flow IAT Mean | 41.0 | 0.503739 | supports prediction |
| 7 | Init_Win_bytes_forward | 1024 | 0.219190 | supports prediction |
| 8 | Total Fwd Packets | 1 | 0.195658 | supports prediction |
| 9 | Total Length of Fwd Packets | 2 | 0.147672 | supports prediction |
| 10 | Flow IAT Max | 41 | 0.129262 | supports prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.693103
- Bottom-ranked deletion score: 0.000107
- Mean of 200 random rankings: 0.155708
- Top-minus-random lift: 0.537395
- Empirical one-sided local p-value: 0.014925

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
