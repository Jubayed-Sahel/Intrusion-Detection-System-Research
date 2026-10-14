# Evidence-Backed IDS Alert Explanation

## Decision transparency status

- **Evidence tier:** `REVIEW_REQUIRED`
- **Meaning:** The explainer passed globally, but this alert did not clear the strict local random-ranking test.
- **Black-box status:** mitigated with tested local evidence; not theoretically eliminated
- **Evidence scope:** primary training median/mode masking intervention
- **Required warning:** This report explains the fitted model under explicit masking tests. It is not a causal explanation and does not replace analyst review.

## Prediction

- Dataset/model context: UNSW-NB15 / binary / random_forest
- Predicted class: **Attack**
- Predicted probability: **0.998627**
- Model seed: 42

Class probabilities:

- Attack: 0.998627
- Normal: 0.001373

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | dload | 0.0 | 0.063068 | supports prediction |
| 2 | ct_dst_sport_ltm | 10 | 0.057566 | supports prediction |
| 3 | rate | 333333.3 | 0.045020 | supports prediction |
| 4 | dbytes | 0 | 0.042497 | supports prediction |
| 5 | state | INT | 0.039230 | supports prediction |
| 6 | proto | igp | 0.036840 | supports prediction |
| 7 | dmean | 0 | 0.032244 | supports prediction |
| 8 | synack | 0.0 | 0.025350 | supports prediction |
| 9 | smean | 90 | 0.022650 | supports prediction |
| 10 | sload | 239999980.0 | 0.019733 | supports prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.255530
- Bottom-ranked deletion score: 0.052408
- Mean of 200 random rankings: 0.183749
- Top-minus-random lift: 0.071781
- Empirical one-sided local p-value: 0.134328

The deletion score is the mean predicted-probability drop after replacing the top 1, 3, 5, and 10 features with training-derived baseline values.

## Benchmark validation context

- TreeSHAP passed corrected random control: True
- Mean top-minus-random lift: 0.195496
- 95% bootstrap interval: [0.099003, 0.293926]
- Holm-adjusted p-value: 0.001583
- Mean neighbor cosine stability: 0.796288
- Mean top-5 neighbor overlap: 0.610813
- Median/P95 explanation latency: 107.986 / 143.526 ms

Mean TreeSHAP deletion scores from the separate reference-sensitivity audit:

- marginal_training_row: 0.185343
- nearest_opposite_prediction: 0.177086
- nearest_same_prediction: -0.020485
- training_median_mode: 0.242833
- zero: 0.239438

## Interpretation rule

- `SUPPORTED_FOR_THIS_ALERT`: benchmark control passed and this alert beats randomized rankings at empirical p <= 0.05.
- `REVIEW_REQUIRED`: benchmark control passed, but the alert-specific ranking did not clear the strict local test.
- `UNSUPPORTED`: the explainer failed benchmark-level validation.

This report makes the model's decision auditable and tests whether its stated evidence changes the model output under a declared intervention. It does not claim causal truth, intervention-invariant fidelity, complete human comprehension, or immunity to dataset shift.
