# Evidence-Backed IDS Alert Explanation

## Decision transparency status

- **Evidence tier:** `REVIEW_REQUIRED`
- **Meaning:** The explainer passed globally, but this alert did not clear the strict local random-ranking test.
- **Black-box status:** mitigated with tested local evidence; not theoretically eliminated
- **Evidence scope:** primary training median/mode masking intervention
- **Required warning:** This report explains the fitted model under explicit masking tests. It is not a causal explanation and does not replace analyst review.

## Prediction

- Dataset/model context: UNSW-NB15 / multiclass / xgboost
- Predicted class: **DoS**
- Predicted probability: **0.347468**
- Model seed: 42

Class probabilities:

- Analysis: 0.010321
- Backdoor: 0.017914
- DoS: 0.347468
- Exploits: 0.082578
- Fuzzers: 0.030990
- Generic: 0.334949
- Normal: 0.068420
- Reconnaissance: 0.104229
- Shellcode: 0.002092
- Worms: 0.001039

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | ct_src_dport_ltm | 3 | -0.381690 | opposes prediction |
| 2 | service | dns | 0.211520 | supports prediction |
| 3 | sbytes | 130 | 0.203350 | supports prediction |
| 4 | rate | 250000.0 | -0.174054 | opposes prediction |
| 5 | ackdat | 0.0 | -0.164436 | opposes prediction |
| 6 | smean | 65 | -0.119120 | opposes prediction |
| 7 | ct_dst_sport_ltm | 1 | -0.093175 | opposes prediction |
| 8 | stcpb | 0 | 0.044584 | supports prediction |
| 9 | dload | 0.0 | 0.043862 | supports prediction |
| 10 | proto | udp | -0.041968 | opposes prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.102940
- Bottom-ranked deletion score: -0.015530
- Mean of 200 random rankings: 0.074132
- Top-minus-random lift: 0.028808
- Empirical one-sided local p-value: 0.437811

The deletion score is the mean predicted-probability drop after replacing the top 1, 3, 5, and 10 features with training-derived baseline values.

## Benchmark validation context

- TreeSHAP passed corrected random control: True
- Mean top-minus-random lift: 0.233682
- 95% bootstrap interval: [0.180551, 0.293675]
- Holm-adjusted p-value: 0.000000
- Mean neighbor cosine stability: 0.702156
- Mean top-5 neighbor overlap: 0.601137
- Median/P95 explanation latency: 23.492 / 25.409 ms

Mean TreeSHAP deletion scores from the separate reference-sensitivity audit:

- marginal_training_row: 0.447860
- nearest_opposite_prediction: 0.287006
- nearest_same_prediction: -0.006492
- training_median_mode: 0.412303
- zero: 0.457845

## Interpretation rule

- `SUPPORTED_FOR_THIS_ALERT`: benchmark control passed and this alert beats randomized rankings at empirical p <= 0.05.
- `REVIEW_REQUIRED`: benchmark control passed, but the alert-specific ranking did not clear the strict local test.
- `UNSUPPORTED`: the explainer failed benchmark-level validation.

This report makes the model's decision auditable and tests whether its stated evidence changes the model output under a declared intervention. It does not claim causal truth, intervention-invariant fidelity, complete human comprehension, or immunity to dataset shift.
