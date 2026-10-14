# Evidence-Backed IDS Alert Explanation

## Decision transparency status

- **Evidence tier:** `SUPPORTED_FOR_THIS_ALERT`
- **Meaning:** The validated explainer also beat randomized rankings for this alert under the primary training median/mode intervention.
- **Black-box status:** mitigated with tested local evidence; not theoretically eliminated
- **Evidence scope:** primary training median/mode masking intervention
- **Required warning:** This report explains the fitted model under explicit masking tests. It is not a causal explanation and does not replace analyst review.

## Prediction

- Dataset/model context: UNSW-NB15 / binary / xgboost
- Predicted class: **Attack**
- Predicted probability: **0.999431**
- Model seed: 42

Class probabilities:

- Attack: 0.999431
- Normal: 0.000569

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | ct_dst_sport_ltm | 10 | 2.007293 | supports prediction |
| 2 | proto | igp | 1.764732 | supports prediction |
| 3 | dload | 0.0 | 0.878621 | supports prediction |
| 4 | sinpkt | 0.003 | 0.784983 | supports prediction |
| 5 | smean | 90 | 0.467513 | supports prediction |
| 6 | sbytes | 180 | 0.318513 | supports prediction |
| 7 | synack | 0.0 | 0.231380 | supports prediction |
| 8 | rate | 333333.3 | 0.158124 | supports prediction |
| 9 | sload | 239999980.0 | 0.127438 | supports prediction |
| 10 | ct_src_dport_ltm | 10 | 0.126058 | supports prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.055432
- Bottom-ranked deletion score: -0.000015
- Mean of 200 random rankings: 0.006476
- Top-minus-random lift: 0.048956
- Empirical one-sided local p-value: 0.024876

The deletion score is the mean predicted-probability drop after replacing the top 1, 3, 5, and 10 features with training-derived baseline values.

## Benchmark validation context

- TreeSHAP passed corrected random control: True
- Mean top-minus-random lift: 0.199435
- 95% bootstrap interval: [0.108212, 0.291204]
- Holm-adjusted p-value: 0.000877
- Mean neighbor cosine stability: 0.543362
- Mean top-5 neighbor overlap: 0.507837
- Median/P95 explanation latency: 2.781 / 2.937 ms

Mean TreeSHAP deletion scores from the separate reference-sensitivity audit:

- marginal_training_row: 0.189395
- nearest_opposite_prediction: 0.236665
- nearest_same_prediction: -0.005704
- training_median_mode: 0.232671
- zero: 0.277167

## Interpretation rule

- `SUPPORTED_FOR_THIS_ALERT`: benchmark control passed and this alert beats randomized rankings at empirical p <= 0.05.
- `REVIEW_REQUIRED`: benchmark control passed, but the alert-specific ranking did not clear the strict local test.
- `UNSUPPORTED`: the explainer failed benchmark-level validation.

This report makes the model's decision auditable and tests whether its stated evidence changes the model output under a declared intervention. It does not claim causal truth, intervention-invariant fidelity, complete human comprehension, or immunity to dataset shift.
