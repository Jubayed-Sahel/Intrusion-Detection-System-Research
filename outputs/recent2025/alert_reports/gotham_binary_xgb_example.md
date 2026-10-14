# Evidence-Backed IDS Alert Explanation

## Decision transparency status

- **Evidence tier:** `REVIEW_REQUIRED`
- **Meaning:** The explainer passed globally, but this alert did not clear the strict local random-ranking test.
- **Black-box status:** mitigated with tested local evidence; not theoretically eliminated
- **Evidence scope:** primary training median/mode masking intervention
- **Required warning:** This report explains the fitted model under explicit masking tests. It is not a causal explanation and does not replace analyst review.

## Prediction

- Dataset/model context: Gotham2025 / binary / xgboost
- Predicted class: **Attack**
- Predicted probability: **0.999920**
- Model seed: 42

Class probabilities:

- Attack: 0.999920
- Normal: 0.000080

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | tcp.dstport | 23.0 | 6.496611 | supports prediction |
| 2 | frame.protocols | eth:ethertype:ip:tcp:telnet | 3.010663 | supports prediction |
| 3 | frame.len | 68 | 2.676430 | supports prediction |
| 4 | ip.ttl | 61 | -1.888815 | opposes prediction |
| 5 | tcp.window_size_value | 502.0 | -0.675311 | opposes prediction |
| 6 | ip.proto | 6 | 0.299425 | supports prediction |
| 7 | ip.flags | 2 | -0.277040 | opposes prediction |
| 8 | tcp.srcport | 48424.0 | -0.216327 | opposes prediction |
| 9 | udp.dstport | None | -0.216193 | opposes prediction |
| 10 | tcp.window_size_scalefactor | 128.0 | 0.156620 | supports prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.697649
- Bottom-ranked deletion score: 0.000015
- Mean of 200 random rankings: 0.283629
- Top-minus-random lift: 0.414020
- Empirical one-sided local p-value: 0.129353

The deletion score is the mean predicted-probability drop after replacing the top 1, 3, 5, and 10 features with training-derived baseline values.

## Benchmark validation context

- TreeSHAP passed corrected random control: True
- Mean top-minus-random lift: 0.129138
- 95% bootstrap interval: [0.067870, 0.190898]
- Holm-adjusted p-value: 0.000014
- Inference unit: explained connection-group mean
- Explained inference units: 57
- Mean neighbor cosine stability: 0.980943
- Mean top-5 neighbor overlap: 0.933452
- Median/P95 explanation latency: 1.054 / 1.442 ms

Mean TreeSHAP deletion scores from the separate reference-sensitivity audit:

- marginal_training_row: 0.226747
- nearest_opposite_prediction: 0.766343
- nearest_same_prediction: -0.014612
- training_median_mode: 0.271424
- zero: 0.109124

## Interpretation rule

- `SUPPORTED_FOR_THIS_ALERT`: benchmark control passed and this alert beats randomized rankings at empirical p <= 0.05.
- `REVIEW_REQUIRED`: benchmark control passed, but the alert-specific ranking did not clear the strict local test.
- `UNSUPPORTED`: the explainer failed benchmark-level validation.

This report makes the model's decision auditable and tests whether its stated evidence changes the model output under a declared intervention. It does not claim causal truth, intervention-invariant fidelity, complete human comprehension, or immunity to dataset shift.
