# Research extension and submission protocol

## Expanded model-seed validation

`run_research_validation.py` retrains RF and XGBoost on both datasets and tasks, using model seeds 42, 52, and 62 and 100 explanations per configuration. The data split stays at seed 42 to isolate model randomness. SHAP and LIME use matched flows within each model/seed. Error-case coverage can make selected flows differ between model seeds; this is not a fixed-panel comparison across seeds.

The primary comparison preserves the existing average deletion over k = 1, 3, 5, 10 and median/mode replacement. Per-seed paired confidence intervals and Wilcoxon tests are reported. A second Holm adjustment covers the entire family across model seeds. Repeated appearances of a flow across seeds are not pooled as independent observations. Capture/session dependence remains unresolved. These experiments extend the existing result; they do not independently establish population generalization or causal fidelity.

Outputs are checkpointed per configuration and retain attribution, stability, fidelity, class metrics, and comparison data. A completed checkpoint is reused only when its protocol hash matches. Use a new output directory for a different protocol.

The corrected run uses `outputs/research_validation_corrected`. The interrupted pre-correction run under `outputs/research_validation` is historical partial evidence and must not be pooled with the corrected experiment. Latency from concurrent research jobs is descriptive; obtain isolated measurements before making new throughput or deployment claims.

## Minority attack investigation

Inspect precision, recall, F1, support, and confusion destinations for every UNSW attack, with particular attention to Analysis, Backdoor, DoS, Shellcode, and Worms. Report seed variability and absolute test counts. Do not optimize class weighting, thresholds, or feature selection on the final test set. Any new tuning needs training-only validation and a locked final test evaluation. Low support can make per-class conclusions unstable.

## Analyst study: prepared protocol, no participants enrolled

Question: does the explanation report improve attack-review decisions relative to prediction plus confidence?

Use a counterbalanced within-participant design with disjoint matched alert sets in two conditions: prediction/confidence and prediction/confidence plus explanation/evidence tier. Balance normal/attack and correct/incorrect predictions and include weak-evidence examples. Use held-out alerts not used to design the report. Have an independent security expert establish the task answer key.

Primary outcome: review-decision correctness. Secondary outcomes: task time, confidence calibration, appropriate escalation of weak evidence, and perceived usefulness. Record analyst experience. Prespecify analysis and sample size using a power calculation informed by a pilot; do not choose an arbitrary participant count. Analyze participant and alert dependence, for example with mixed-effects models. Obtain institutional review/consent as applicable before recruitment. Never describe this proposed study as completed evidence.

## Operational evaluation: prepared protocol, no live deployment

An initial offline pilot is now implemented in `profile_alert_pipeline.py`, using three alerts per configuration and the full 200-permutation report path. Results are under `outputs/research_validation_corrected/operational_pilot`. This pilot measures the complete local report path, including artifact/input reads and serialization, rather than explainer calls alone. It does not measure queueing, concurrent load, sustained throughput, or drift. Batched local-control predictions avoid thousands of separate prediction calls; floating-point near-ties use a conservative 1e-12 tolerance.

Use authorized offline replay or a controlled test environment. Measure full preprocessing, prediction, explanation, report generation, queue time, throughput, and memory under stated hardware and concurrency. Report warm/cold latency percentiles separately. Evaluate drift on a separate time/source partition with documented metadata. Keep detection and explanation queues independently measurable and avoid automated response actions during evaluation. The current parquet files do not support a valid temporal holdout because capture/session metadata is unavailable.

## Submission gates

- Confirm a target venue before changing template, page count, anonymity, or disclosure wording.
- Complete dataset provenance and assess expanded-validation results.
- Have the supervisor/authors review novelty, claims, statistical assumptions, citations, and limitations.
- Independently verify every reference against publisher or author records.
- Apply the exact venue template and validate the final PDF with the venue's required tools.
- Supply names/affiliations only when permitted by review rules; do not fabricate author details.
- Publish a versioned code/artifact release and archive it after GitHub access is restored. Keep raw data and local environments out of the repository.
- Similarity checks, author approval, ethics approval, and live participant/deployment evidence cannot be substituted by automated checks.
