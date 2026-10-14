# Evidence-Backed IDS Alert Explanation

## Decision transparency status

- **Evidence tier:** `SUPPORTED_FOR_THIS_ALERT`
- **Meaning:** The validated explainer also beat randomized rankings for this alert under the primary training median/mode intervention.
- **Black-box status:** mitigated with tested local evidence; not theoretically eliminated
- **Evidence scope:** primary training median/mode masking intervention
- **Required warning:** This report explains the fitted model under explicit masking tests. It is not a causal explanation and does not replace analyst review.

## Prediction

- Dataset/model context: UNSW-NB15 / multiclass / xgboost
- Predicted class: **Normal**
- Predicted probability: **0.630009**
- Model seed: 42

Class probabilities:

- Analysis: 0.001368
- Backdoor: 0.023242
- DoS: 0.044667
- Exploits: 0.024959
- Fuzzers: 0.247598
- Generic: 0.015075
- Normal: 0.630009
- Reconnaissance: 0.007591
- Shellcode: 0.005152
- Worms: 0.000339

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | ct_src_dport_ltm | 2 | 1.194023 | supports prediction |
| 2 | ackdat | 0.049494 | -0.364148 | opposes prediction |
| 3 | service | - | 0.354529 | supports prediction |
| 4 | proto | tcp | 0.172954 | supports prediction |
| 5 | tcprtt | 0.114132 | -0.097001 | opposes prediction |
| 6 | trans_depth | 0 | 0.092676 | supports prediction |
| 7 | smean | 71 | -0.087957 | opposes prediction |
| 8 | dur | 0.441082 | -0.071958 | opposes prediction |
| 9 | sinpkt | 60.02557 | 0.071518 | supports prediction |
| 10 | ct_dst_sport_ltm | 1 | 0.062514 | supports prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.591361
- Bottom-ranked deletion score: 0.115767
- Mean of 200 random rankings: 0.191022
- Top-minus-random lift: 0.400338
- Empirical one-sided local p-value: 0.024876

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
