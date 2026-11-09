# Supplementary package index

**Updated:** 9 November 2026. Internal index of the research record. The journal draft, extended report and anonymous conference draft are separate files.

## Manuscripts, literature, and venue preparation

- `output/pdf/xai_ids_recent2025_paper.pdf` and `paper/ieee/` — extended report and editable generated IEEE source
- `output/pdf/xai_ids_conference_review.pdf` and `paper/conference/` — anonymous conference candidate and editable source
- `output/pdf/xai_ids_traffic_sources_and_feature_masking.pdf` and `paper/journal/` — journal-format manuscript with protocol shortcut controls and TCP-only sensitivity
- [Training-size protocol](TRAINING_SCALE_PROTOCOL.md), [48 model results](outputs/training_scale/metrics.csv), and [experiment runner](run_training_scale.py) — 10,000, 40,000, and 160,000 training rows per model on the same eight complete GeNIS source holdouts
- [Independent TCP protocol](INDEPENDENT_TCP_PROTOCOL.md), [error counts](outputs/independent_tcp/metrics.csv), [label coverage](outputs/independent_tcp/coverage.csv), and [acquisition and execution manifest](outputs/independent_tcp/manifest.json) — replay with `python run_independent_tcp.py` after downloading the [PDMFC v1 CSV](https://zenodo.org/records/16943481) to `data/official/16943481/labeled_cicflow_genelen.csv` and preparing the original GeNIS and OCPP inputs
- `LITERATURE_REVIEW_20261107.md` and `literature_review_20261107.json` — 20 additional primary full-text reading notes, version/status distinctions, findings, and resulting decisions
- `outputs/literature_review_20261107/acquisition.json` — acquisition successes, failed local PDF requests, and hashes of 18 acquired PDFs; two other full texts were read through the web
- `BANGLADESH_SUBMISSION_PLAN.md` — provisional venue fit, official requirements, date conflict, and eligibility questions
- `RECENT_REFERENCE_VALIDATION.md` — reference and claim-support audit
- `outputs/literature_review_20261107/manuscript_validation.json` — reference counts, DOI title matching for the full report, local literature hashes, PDF fonts and conference anonymity checks
- `verify_manuscript_revision.py` — repeatable local manuscript checks without network or raw datasets

Locally acquired reference PDFs are excluded from Git and from the submission package. Bibliographic links are supplied instead.

## Protocol and provenance

- `config_recent.yaml` — frozen experiment configuration
- `RECENT_DATASET_PROVENANCE.md` — acquisition, conversion, sampling, exclusions, and group split
- `DATA_PROVENANCE.md` — primary versus historical source status
- `outputs/recent2025/run_manifest.json` — source hashes, environment, and configuration
- `outputs/recent2025/environment-lock.txt` and `runtime.json`

## Predictive and explanation results

- `outputs/recent2025/predictive_metrics.csv` — 40 fitted contexts
- `outputs/recent2025/predictive_summary.csv` — five-seed supported-class summary
- `outputs/recent2025/predictive_baselines.csv` — majority and depth-5 tree
- `outputs/recent2025/per_class_metrics.csv` — precision, recall, F1, and support
- `outputs/recent2025/paired_comparisons.csv` — 24 TreeSHAP-versus-LIME group tests
- `outputs/recent2025/fidelity_control_tests.csv` — 48 top-versus-random tests
- `outputs/recent2025/explanation_summary.csv` — latency and neighborhood similarity
- `outputs/recent2025/feature_ablation.csv`
- `outputs/recent2025/summary.json`

## Sensitivity audits

- `EXPLANATION_ROBUSTNESS.md` — post-hoc two-sided sign and single-connection influence methods/results
- `outputs/explanation_robustness/sensitivity.csv` — 24 matched-context sensitivity results
- `outputs/explanation_robustness/manifest.json` — analysis scope, summary, and SHA-256 input/script hashes
- `run_explanation_robustness.py` — reproducible supplementary analysis, preserving frozen primary outputs
- `run_pattern_sensitivity.py` — post-hoc exact raw-predictor matching and conditional exclusion, without refitting or changing the primary holdout
- `outputs/pattern_sensitivity_20261107/coverage.csv` — 379 GeNIS and 1,914 Gotham train-matching test records removed; original and retained coverage
- `outputs/pattern_sensitivity_20261107/predictive.csv` — eight saved seed-42 models, original and conditionally filtered results with the original test-supported label denominator
- `outputs/pattern_sensitivity_20261107/explanatory.csv` — 24 retained explanation contexts, sign/influence diagnostics, and a separate exploratory Holm family
- `outputs/pattern_sensitivity_20261107/manifest.json` — input/script/model hashes, summary, and limits; exclusion is not a new split or independent validation
- `outputs/recent2025/extended/calibration_summary.csv`
- `outputs/recent2025/extended/masking_baseline_ablation.csv`
- `outputs/recent2025/extended/lime_budget_ablation.csv`
- `outputs/recent2025/extended/balancing_ablation.csv`

## Alert examples

See [the closeout](PAPER_WORK_REMAINING.md) for the source-holdout, uncapped, independent capture and protocol audit evidence.

- `outputs/recent2025/alert_reports/genis_binary_xgb_example.md`
- `outputs/recent2025/alert_reports/gotham_binary_xgb_example.md`

## Reproduction

See the current-study commands in `README.md`. Raw official data, prepared parquet files, and serialized models stay local and are not part of the Git package.

`python verify_research_closeout.py` verifies the frozen evidence without retraining. The optional `--verify-raw` additionally checks the locally acquired GeNIS and Gotham inputs against the primary source records.

The later local `outputs/retrain_20261021/` and `outputs/retrain_predictive_20261021/` folders are separate retraining records, not replacements for `outputs/recent2025/`. Do not merge partial explanation runs with the frozen primary tables or infer a complete explanation reproduction from predictive-only validation.
