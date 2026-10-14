# Evidence-Backed IDS Alert Explanation

## Decision transparency status

- **Evidence tier:** `SUPPORTED_FOR_THIS_ALERT`
- **Meaning:** The validated explainer also beat randomized rankings for this alert under the primary training median/mode intervention.
- **Black-box status:** mitigated with tested local evidence; not theoretically eliminated
- **Evidence scope:** primary training median/mode masking intervention
- **Required warning:** This report explains the fitted model under explicit masking tests. It is not a causal explanation and does not replace analyst review.

## Prediction

- Dataset/model context: CIC-IDS2017 / multiclass / xgboost
- Predicted class: **FTP-Patator**
- Predicted probability: **0.999866**
- Model seed: 42

Class probabilities:

- BENIGN: 0.000037
- Bot: 0.000003
- DDoS: 0.000011
- DoS GoldenEye: 0.000003
- DoS Hulk: 0.000003
- DoS Slowhttptest: 0.000006
- DoS slowloris: 0.000016
- FTP-Patator: 0.999866
- Heartbleed: 0.000002
- Infiltration: 0.000002
- PortScan: 0.000016
- SSH-Patator: 0.000019
- Web Attack - Brute Force: 0.000007
- Web Attack - Sql Injection: 0.000003
- Web Attack - XSS: 0.000007

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | Destination Port | 21 | 6.020392 | supports prediction |
| 2 | Init_Win_bytes_backward | 0 | 1.173337 | supports prediction |
| 3 | Packet Length Std | 8.082903769 | 0.332757 | supports prediction |
| 4 | Flow IAT Max | 144 | 0.304147 | supports prediction |
| 5 | Fwd Packet Length Max | 14 | 0.301457 | supports prediction |
| 6 | Init_Win_bytes_forward | 229 | 0.270083 | supports prediction |
| 7 | Packet Length Mean | 7.0 | 0.177308 | supports prediction |
| 8 | SYN Flag Count | 1 | 0.093449 | supports prediction |
| 9 | Flow Duration | 231 | -0.089528 | opposes prediction |
| 10 | Max Packet Length | 14 | 0.071211 | supports prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.878206
- Bottom-ranked deletion score: 0.002671
- Mean of 200 random rankings: 0.143611
- Top-minus-random lift: 0.734595
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
