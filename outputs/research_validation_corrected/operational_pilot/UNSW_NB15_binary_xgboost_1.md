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
- Predicted probability: **0.643266**
- Model seed: 42

Class probabilities:

- Attack: 0.643266
- Normal: 0.356734

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | ackdat | 0.191876 | 0.559938 | supports prediction |
| 2 | dload | 2462.047 | 0.286272 | supports prediction |
| 3 | sloss | 27 | -0.284911 | opposes prediction |
| 4 | smean | 1137 | 0.216803 | supports prediction |
| 5 | synack | 0.16563 | -0.210311 | opposes prediction |
| 6 | trans_depth | 1 | 0.193147 | supports prediction |
| 7 | stcpb | 3997529164 | -0.192994 | opposes prediction |
| 8 | service | - | -0.131313 | opposes prediction |
| 9 | dbytes | 612 | -0.123705 | opposes prediction |
| 10 | dtcpb | 3579042778 | -0.106919 | opposes prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.116690
- Bottom-ranked deletion score: -0.023110
- Mean of 200 random rankings: -0.038284
- Top-minus-random lift: 0.154974
- Empirical one-sided local p-value: 0.044776

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
