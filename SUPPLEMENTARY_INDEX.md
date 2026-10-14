# Supplementary package index

Venue-specific supplementary files have not been created because no IEEE journal or conference template has been selected. The completed local artifacts below are the intended contents of a methods/data supplement.

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

- `outputs/recent2025/extended/calibration_summary.csv`
- `outputs/recent2025/extended/masking_baseline_ablation.csv`
- `outputs/recent2025/extended/lime_budget_ablation.csv`
- `outputs/recent2025/extended/balancing_ablation.csv`

## Alert examples

- `outputs/recent2025/alert_reports/genis_binary_xgb_example.md`
- `outputs/recent2025/alert_reports/gotham_binary_xgb_example.md`

## Reproduction

See the current-study commands in `README.md`. Raw official data, prepared parquet files, and serialized models stay local and are not part of the Git package.
