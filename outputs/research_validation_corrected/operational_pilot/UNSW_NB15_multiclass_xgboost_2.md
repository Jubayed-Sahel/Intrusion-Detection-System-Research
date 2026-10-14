# Evidence-Backed IDS Alert Explanation

## Decision transparency status

- **Evidence tier:** `SUPPORTED_FOR_THIS_ALERT`
- **Meaning:** The validated explainer also beat randomized rankings for this alert under the primary training median/mode intervention.
- **Black-box status:** mitigated with tested local evidence; not theoretically eliminated
- **Evidence scope:** primary training median/mode masking intervention
- **Required warning:** This report explains the fitted model under explicit masking tests. It is not a causal explanation and does not replace analyst review.

## Prediction

- Dataset/model context: UNSW-NB15 / multiclass / xgboost
- Predicted class: **Backdoor**
- Predicted probability: **0.389994**
- Model seed: 42

Class probabilities:

- Analysis: 0.360342
- Backdoor: 0.389994
- DoS: 0.108801
- Exploits: 0.019307
- Fuzzers: 0.027528
- Generic: 0.032031
- Normal: 0.000546
- Reconnaissance: 0.060784
- Shellcode: 0.000480
- Worms: 0.000187

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | sbytes | 200 | 0.742196 | supports prediction |
| 2 | proto | unas | 0.228195 | supports prediction |
| 3 | sloss | 0 | 0.209550 | supports prediction |
| 4 | sload | 200000000.0 | -0.150926 | opposes prediction |
| 5 | smean | 100 | 0.149109 | supports prediction |
| 6 | dmean | 0 | -0.081102 | opposes prediction |
| 7 | ct_dst_sport_ltm | 4 | 0.074788 | supports prediction |
| 8 | dur | 3e-06 | 0.052680 | supports prediction |
| 9 | sinpkt | 0.004 | 0.037045 | supports prediction |
| 10 | rate | 250000.0 | -0.024586 | opposes prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.314861
- Bottom-ranked deletion score: -0.005318
- Mean of 200 random rankings: 0.122699
- Top-minus-random lift: 0.192162
- Empirical one-sided local p-value: 0.004975

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
