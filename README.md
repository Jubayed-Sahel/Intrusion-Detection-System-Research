# Quantitative XAI for Network Intrusion Detection

This project measures the quality of feature explanations for intrusion-detection alerts. Random Forest and XGBoost perform binary and multiclass detection; TreeSHAP and LIME explain matched held-out records. The evaluation measures deletion fidelity, random and bottom-ranked controls, stability, latency, calibration, and sensitivity to the masking reference.

**Current primary study:** author-published **GeNIS2025** enterprise network flows and **Gotham2025** IoT packets, acquired from their open official Zenodo records. A documented acquisition and preparation pipeline replaces the earlier parquet inputs whose conversion history was unavailable. These are 2025 releases; this project does not claim that they are the newest datasets in every intrusion-detection domain.

**Research status, 14 October 2026:** official-source acquisition, corrected preparation, all 40 predictive fits, all 24 paired explanation contexts, and all eight extended audits are complete. The full source/inference verifier passes, including raw-byte checks, and all 18 unit tests pass. The six-page recent manuscript now includes a related-work comparison against prior XAI-IDS evaluation studies and has been visually reviewed. Gotham's ambiguous `Unknown` labels are excluded from both supervised tasks. IEEE is the intended publisher family; a specific journal or conference has not been selected. The work has not been peer reviewed or accepted.

## Start here

- [Recent-data manuscript](output/pdf/xai_ids_recent2025_paper.pdf)
- [Current dataset acquisition and transformation record](RECENT_DATASET_PROVENANCE.md)
- [Primary and historical provenance overview](DATA_PROVENANCE.md)
- [Publication-readiness report](PUBLICATION_READINESS_REPORT.md)
- [Recent experiment manifest](outputs/recent2025/run_manifest.json)
- [Current numerical summary](outputs/recent2025/summary.json)
- [Five-seed predictive summary](outputs/recent2025/predictive_summary.csv)
- [IEEE submission preparation](IEEE_SUBMISSION_NOTES.md)
- [Recent-study reference and claim support](RECENT_REFERENCE_VALIDATION.md)
- [Supplementary artifact index](SUPPLEMENTARY_INDEX.md)
- [Analyst and operational follow-up protocols](RESEARCH_NEXT_STUDIES.md)

The earlier [project handbook](PROJECT_HANDBOOK.md), [notebook](PROJECT_WALKTHROUGH.ipynb), [literature traceability](LITERATURE_REQUIREMENTS_TRACEABILITY.md), and [2017/2015 manuscript](output/pdf/xai_ids_ieee_paper.pdf) describe the historical study. Use the recent commands below for the current primary study.

## Official datasets and preparation

[GeNIS](https://zenodo.org/records/14919237), released on 24 February 2025, contains enterprise traffic from the Airbus CyberRange. This pipeline scans all eight five-second scenario CSVs, keeping one aggregation interval. It uses the author's category labels: benign, brute force, denial of service, and reconnaissance. The downloaded `0-info.zip` and `3-scenarios.zip` match the author's published MD5 checksums, and local SHA-256 hashes are recorded. Cite the [primary data article](https://doi.org/10.1016/j.dib.2025.111487) when using it.

[Gotham](https://zenodo.org/records/14502760), released on 5 February 2025, contains packet features captured at 78 IoT devices in a virtual smart-city testbed. All 78 author-provided processed CSVs are retrieved directly from the official ZIP using ordinary HTTP byte ranges, with full-member length and CRC32 verification and local SHA-256 hashes. The whole 23.8 GB archive's MD5 is advertised by the provider but is **not recomputed**, because unrelated packet captures are not downloaded. Cite the [authors' paper](https://arxiv.org/abs/2502.03134) and dataset record.

Both records specify CC BY 4.0. Original data, prepared parquet files, and serialized models are generated locally and excluded from Git. The transformation scans every selected source member and retains a deterministic random sample of at most 10,000 records per source label. This changes the class distribution, so the resulting scores describe a documented derivative rather than natural traffic prevalence or an official leaderboard split.

Gotham's `Unknown` source label is excluded from both supervised tasks because its benign/attack meaning is unspecified. Source counts and hashes still include those records; the preparation separately records the exclusions. CoAP Amplification is confined to one sampled connection group and has no held-out performance claim. Primary multiclass `macro_f1_supported_classes` averages classes with test support. `macro_f1_training_vocabulary` includes all training labels, and the original `macro_f1` retains the actual/predicted-label union for transparency.

Splitting holds out whole connection groups: global provider `FlowID` values for GeNIS and bidirectional endpoint/port/protocol tuples across all device files for Gotham. The first label-covered group split is fixed before model fitting. Classes with only one sampled group stay in training and are explicitly reported as absent from test. Identical feature patterns may occur across different held-out groups; the provenance audit records them without removing legitimate repeated behavior. Identifiers, timestamps, labels, and selected payload/export artifacts are excluded from model inputs. Constant removal, imputation, and categorical encoding use training data only.

## Reproduce the current study

Run from the repository root with Python 3.12 and the pinned top-level dependencies. Acquisition requires internet access and local storage for the selected official sources.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python fetch_recent_datasets.py --record 14919237 --files 0-info.zip 3-scenarios.zip
python fetch_gotham_members.py
python freeze_recent_acquisition.py
python prepare_recent_datasets.py
python run_recent_benchmark.py --config config_recent.yaml
python run_recent_audit.py
python summarize_recent_results.py
python build_recent_paper.py
python -B verify_recent_benchmark.py
# Also rehash all locally downloaded official source bytes:
python -B verify_recent_benchmark.py --verify-raw
python -B -m unittest discover -s tests -v
```

The benchmark checkpoints completed dataset/task/model/seed contexts and can resume with the same configuration and source code. It rejects a changed input hash or changed frozen benchmark source rather than mixing experiments from different versions. The provenance files contain exact source URLs, member hashes, parsed counts, exclusions, split audits, preparation-source snapshots, and prepared-file hashes. Acquisition snapshots are post-acquisition copies of the provider records, ledgers, and retrieval scripts; they do not assert that retrieval-script hashes were captured at download time. Extended audits separately freeze their runner and helper sources at run start. `environment-lock.txt` and `runtime.json` record the actual fresh-environment run, including Python 3.12.14 and transitive packages.

Re-running the same output directory skips completed checkpoints. To independently retrain using the prepared official inputs, copy `config_recent.yaml` to `config_reproduction.yaml` and set `output_dir: outputs/recent2025_reproduction`. Then run:

```bash
python freeze_recent_acquisition.py --output outputs/recent2025_reproduction
python run_recent_benchmark.py --config config_reproduction.yaml
python run_recent_audit.py --config config_reproduction.yaml
python summarize_recent_results.py --output outputs/recent2025_reproduction
python build_recent_paper.py --results outputs/recent2025_reproduction --output output/pdf/xai_ids_recent2025_reproduction.pdf
python -B verify_recent_benchmark.py --output outputs/recent2025_reproduction --verify-raw
```

To independently repeat source conversion as well, run `prepare_recent_datasets.py` again before retraining and compare its prepared-file hashes. A changed configuration or source version also needs a separate output directory. Frozen runtime sources and acquisition metadata have Git byte-preservation rules so line-ending conversion does not invalidate their hashes after cloning.

## Evaluation protocol

- Five predictive model seeds: 42, 52, 62, 72, and 82; both models, both tasks, and both datasets give 40 predictive fits.
- Three explanation model seeds: 42, 52, and 62; TreeSHAP and LIME explain the same 100 selected test records within each context. Selection is label-stratified with available prediction-error cases deliberately included. GeNIS records are flows; Gotham records are packets.
- Deletion replaces the top-ranked features by the declared training median/mode reference at k={1,3,5,10}. Random and bottom-ranked rankings provide controls.
- Primary uncertainty uses equal-weight means for the explained connection groups, then paired bootstrap intervals and one-sided Wilcoxon tests. Holm correction spans all 24 TreeSHAP-versus-LIME comparisons and all 48 top-versus-random comparisons. A per-record summary interval is descriptive; it does not replace the group-level inference tables.
- Seed-42 audits examine binary calibration, class weighting, five masking references, LIME sampling budgets, and feature ablation. Majority prediction and a depth-five decision tree provide simple predictive baselines.

`outputs/recent2025/paired_comparisons.csv` and `fidelity_control_tests.csv` contain the primary group-level evidence. `holm_adjusted_p_all_contexts` is the adjustment across the complete study. Three model seeds quantify algorithmic variation on one fixed split; they are not three independent traffic collections.

Recompute statistical endpoints from each original `contexts/<context>/fidelity.csv` with pandas `float_precision="round_trip"`. Re-reading and rewriting near-tied floating-point values can change Wilcoxon ranks; the aggregate `fidelity.csv` is a convenience export rather than the precision authority. The verifier uses the original per-context evidence for inference checks.

## Current results

Five-seed mean supported-class macro-F1 is:

- **GeNIS binary:** Random Forest 0.9998; XGBoost 0.9998.
- **GeNIS multiclass:** Random Forest 0.9997; XGBoost 1.0000.
- **Gotham binary:** Random Forest 1.0000; XGBoost 0.9999.
- **Gotham multiclass:** Random Forest 0.8755; XGBoost 0.8665, across the 16 labels with held-out support.

These are connection-holdout results within class-capped testbed data. A depth-five tree already reaches 0.9906 on GeNIS multiclass, showing how separable that derivative is. On Gotham multiclass, its supported-class macro-F1 is 0.3589. Gotham's training-majority baseline predicts the training-only CoAP label and scores zero on test; this follows from the split's class coverage rather than proving that a majority baseline always fails.

TreeSHAP exceeds LIME's group-mean deletion score in 24/24 model/seed contexts, with bootstrap intervals above zero and Holm-adjusted directional tests passing in all 24. Mean differences range from 0.0570 to 0.3058 probability-drop units. TreeSHAP's top-versus-random comparison passes the strict positive-interval plus Holm-significance criterion in 24/24 contexts; LIME passes 20/24. Each context contains 57-95 explained connection groups from the 100 selected records. These findings apply to the declared training median/mode intervention and diagnostic sample.

## Alert reports

The alert-report command accepts a locally generated recent model. Its evidence gate uses the model's seed and the study-wide adjusted control result, followed by that alert's local randomized-ranking test.

Two current examples illustrate the local gate: [GeNIS binary XGBoost](outputs/recent2025/alert_reports/genis_binary_xgb_example.md) is `SUPPORTED_FOR_THIS_ALERT`, while [Gotham binary XGBoost](outputs/recent2025/alert_reports/gotham_binary_xgb_example.md) is `REVIEW_REQUIRED`. A model's passing study-level result does not guarantee support for every alert.

```bash
python explain_alert.py \
  --model outputs/recent2025/models/GeNIS2025_binary_xgboost.joblib \
  --input path/to/flows.csv \
  --row 0 \
  --output outputs/alert_reports/alert_0
```

Deletion evidence tests model behavior under a specified intervention. It does not establish a causal attack explanation, analyst benefit, or safe autonomous response. Current latency measurements were collected during concurrent local preparation/experiment jobs and are descriptive. The previous three-alert-per-context report timing pilot belongs to the historical study and is not a recent-dataset service benchmark.

## Repository structure

```text
src/xai_ids/                  shared models, XAI, recent preparation, audits, paper code
tests/                        leakage, grouping, reporting, and preparation checks
data/official/                local official sources and acquisition records (ignored)
data/prepared/                local prepared inputs and preparation snapshots (ignored)
outputs/recent2025/           current results, source snapshots, and provenance manifest
output/pdf/                   generated current and historical manuscripts
config_recent.yaml            fixed recent-data experiment configuration
fetch_recent_datasets.py      complete-archive acquisition with provider checksum checks
fetch_gotham_members.py        official processed-member acquisition and CRC32 checks
freeze_recent_acquisition.py  acquisition-ledger and retrieval-code snapshots
prepare_recent_datasets.py    deterministic sampling and connection-group holdout
run_recent_benchmark.py       predictive and matched explanation experiments
run_recent_audit.py           current sensitivity and calibration audits
summarize_recent_results.py   current supported-class and group-inference summary
build_recent_paper.py         current manuscript generator
verify_recent_benchmark.py    current cross-artifact and source-chain checks
```

## Historical 2017/2015 study

`config.yaml`, `run_benchmark.py`, `run_extended_audit.py`, `build_paper.py`, `verify_outputs.py`, and the top-level `outputs/` tables retain the earlier CIC-IDS2017 and UNSW-NB15 study. Its corrected experiments and a fresh-environment seed-42 reproduction are archived under `outputs/research_validation_corrected/` and `outputs/clean_reproduction/`.

Those four original parquet files match the historical manifest, but their original download and conversion history remains unknown. Historical reproducibility does not establish equivalence to official source files. The current study uses the separately acquired 2025 sources and its own manifest; it does not retroactively certify the old files. See [DATA_PROVENANCE.md](DATA_PROVENANCE.md) for the historical leakage and representation findings.

## Scope and publication

Connection holdout within each testbed is neither temporal generalization nor cross-organization deployment. Gotham's packet representation differs from GeNIS's flow representation; report results separately. Per-class sampling changes priors, rare classes may lack independent held-out connections, and deletion scores depend on the masking distribution. No human analyst, live deployment, production drift, or throughput study has been completed.

The recent PDF is an anonymous IEEE-style research draft. Authors and supervisors must review its claims and contributions. Submission also requires a named IEEE venue, its exact template and page limit, author/affiliation metadata, and applicable disclosure and PDF checks. The research code, results, provenance, and draft manuscript were published to this repository on 14 October 2026. See [remaining paper work](PAPER_WORK_REMAINING.md) and [GitHub Actions](https://github.com/Jubayed-Sahel/Intrusion-Detection-System-Research/actions) for completion and verification status.
