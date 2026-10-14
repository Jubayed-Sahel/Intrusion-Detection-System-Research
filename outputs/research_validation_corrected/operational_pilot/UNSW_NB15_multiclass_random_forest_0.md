# Evidence-Backed IDS Alert Explanation

## Decision transparency status

- **Evidence tier:** `SUPPORTED_FOR_THIS_ALERT`
- **Meaning:** The validated explainer also beat randomized rankings for this alert under the primary training median/mode intervention.
- **Black-box status:** mitigated with tested local evidence; not theoretically eliminated
- **Evidence scope:** primary training median/mode masking intervention
- **Required warning:** This report explains the fitted model under explicit masking tests. It is not a causal explanation and does not replace analyst review.

## Prediction

- Dataset/model context: UNSW-NB15 / multiclass / random_forest
- Predicted class: **Exploits**
- Predicted probability: **0.399118**
- Model seed: 42

Class probabilities:

- Analysis: 0.005183
- Backdoor: 0.006762
- DoS: 0.218191
- Exploits: 0.399118
- Fuzzers: 0.054574
- Generic: 0.243504
- Normal: 0.018033
- Reconnaissance: 0.048698
- Shellcode: 0.005937
- Worms: 0.000000

## Top signed TreeSHAP evidence

| Rank | Feature | Observed value | Attribution | Direction |
|---:|---|---:|---:|---|
| 1 | service | dns | 0.076104 | supports prediction |
| 2 | smean | 65 | 0.064008 | supports prediction |
| 3 | ct_src_dport_ltm | 3 | 0.052117 | supports prediction |
| 4 | sbytes | 130 | 0.050716 | supports prediction |
| 5 | ct_dst_sport_ltm | 1 | -0.027593 | opposes prediction |
| 6 | proto | udp | 0.024721 | supports prediction |
| 7 | sload | 130000000.0 | 0.018228 | supports prediction |
| 8 | dur | 4e-06 | 0.012863 | supports prediction |
| 9 | rate | 250000.0 | 0.010759 | supports prediction |
| 10 | sinpkt | 0.004 | 0.010364 | supports prediction |

Positive attribution supports the reported class; negative attribution opposes it. Attribution is model evidence, not real-world causality.

## Alert-specific fidelity test

- Top-ranked deletion score: 0.323784
- Bottom-ranked deletion score: 0.000758
- Mean of 200 random rankings: 0.143156
- Top-minus-random lift: 0.180628
- Empirical one-sided local p-value: 0.029851

The deletion score is the mean predicted-probability drop after replacing the top 1, 3, 5, and 10 features with training-derived baseline values.

## Benchmark validation context

- TreeSHAP passed corrected random control: True
- Mean top-minus-random lift: 0.170313
- 95% bootstrap interval: [0.128344, 0.214269]
- Holm-adjusted p-value: 0.000000
- Mean neighbor cosine stability: 0.837808
- Mean top-5 neighbor overlap: 0.636278
- Median/P95 explanation latency: 324.206 / 356.715 ms

Mean TreeSHAP deletion scores from the separate reference-sensitivity audit:

- marginal_training_row: 0.338191
- nearest_opposite_prediction: 0.263020
- nearest_same_prediction: 0.034415
- training_median_mode: 0.320509
- zero: 0.375646

## Interpretation rule

- `SUPPORTED_FOR_THIS_ALERT`: benchmark control passed and this alert beats randomized rankings at empirical p <= 0.05.
- `REVIEW_REQUIRED`: benchmark control passed, but the alert-specific ranking did not clear the strict local test.
- `UNSUPPORTED`: the explainer failed benchmark-level validation.

This report makes the model's decision auditable and tests whether its stated evidence changes the model output under a declared intervention. It does not claim causal truth, intervention-invariant fidelity, complete human comprehension, or immunity to dataset shift.
