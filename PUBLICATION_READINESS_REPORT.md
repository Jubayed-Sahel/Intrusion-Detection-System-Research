# Publication Readiness Report

**Audit date:** 14 October 2026.

**Status:** the local research replacement and verification are complete: official acquisition, corrected preparation, all 40 predictive fits, 24 paired explanation contexts, 48 control comparisons, and eight extended audits. The full source/inference verifier passes with raw-byte checks, and all 17 unit tests pass. Gotham's ambiguous `Unknown` label is excluded from both supervised tasks. The six-page recent manuscript is generated and visually reviewed. Submission still requires a specific venue and author/supervisor review; this is a technical assessment, not peer review or IEEE acceptance.

## Dataset-provenance gap and replacement

The historical CIC-IDS2017 and UNSW-NB15 parquet files reproduce against their saved hashes, but the original download/conversion history is unavailable. The primary study now uses independently acquired author-published [GeNIS2025](https://zenodo.org/records/14919237) and [Gotham2025](https://zenodo.org/records/14502760) instead. Their provider records specify CC BY 4.0; source URLs, metadata, checksums, parsed member counts, preparation code, exclusions, deterministic sampling, group splits, and prepared hashes are recorded.

GeNIS's complete selected archives pass the provider's published MD5 checks. Gotham's 78 retrieved CSVs plus README pass ZIP CRC32/length checks and have local SHA-256 hashes; the whole archive's MD5 is not recomputed. All eight GeNIS five-second scenario CSVs and all 78 Gotham processed device CSVs are included in source scanning. Post-acquisition provider/ledger/retrieval-code snapshots have explicit copy-time hashes; benchmark and extended-audit sources have separate run-start snapshots. These claims concern the official authors' supplied CSVs and do not imply a fresh packet-to-feature reconstruction or independent validation of all labels.

This recorded replacement resolves source history for the new primary inputs. It does not certify the old parquet files or transfer their results to the new study. Exact details are in [RECENT_DATASET_PROVENANCE.md](RECENT_DATASET_PROVENANCE.md), with historical issues preserved in [DATA_PROVENANCE.md](DATA_PROVENANCE.md).

## Current design

- Fixed deterministic sampling cap of 10,000 records per observed source label, with all chosen source members scanned. The derivative has altered class priors.
- Explicit exclusion of Gotham's ambiguous `Unknown` label from both supervised tasks, with full source counts and excluded-label counts retained. CoAP Amplification has only one sampled group and no held-out claim. Primary `macro_f1_supported_classes` averages test-supported classes; `macro_f1_training_vocabulary` and the original actual/predicted-label-union `macro_f1` are also retained.
- Whole connection-group holdout, using global GeNIS flow IDs and bidirectional Gotham endpoint/protocol groups across all device files. No source group may appear on both sides; single-group labels are explicitly training-only.
- Declared identifier, target, timestamp, and exporter/payload exclusions. Constant removal, imputation, and category mapping use training data only.
- Binary and multiclass tasks, Random Forest and XGBoost, five predictive seeds, majority and shallow-tree baselines: 40 completed primary predictive fits.
- TreeSHAP and LIME on 100 matched held-out records per context across three model seeds. Primary paired and control inference uses equal-weight explained connection-group means, with Holm correction across the complete 24 and 48 comparison families.
- Seed-42 calibration, weighting, masking-reference, LIME-budget, and feature-ablation audits, with source snapshots and an integrity verifier.

Per-record summary confidence intervals are descriptive; the group-level paired and control tables carry the primary inference. The complete source counts, test-supported metric definition, context counts, and numerical conclusions are recorded in `outputs/recent2025/summary.json` and `predictive_summary.csv`.

## Current findings

Five-seed mean supported-class macro-F1 for GeNIS is 0.9998/0.9998 for binary Random Forest/XGBoost and 0.9997/1.0000 for multiclass. Gotham means are 1.0000/0.9999 for binary and 0.8755/0.8665 for multiclass, where 16 labels have test support. GeNIS's depth-five tree already scores 0.9906 on multiclass; its near-perfect ensemble scores describe a highly separable sampled testbed derivative. Gotham's depth-five multiclass baseline is 0.3589. Its zero-scoring majority baseline predicts training-only CoAP Amplification, so that baseline is affected by the split's class coverage.

TreeSHAP has positive group-mean fidelity differences versus LIME in 24/24 contexts; all paired bootstrap intervals are above zero and all directional Wilcoxon tests pass Holm correction across the 24 comparisons. Mean differences range from 0.0570 to 0.3058 probability-drop units. For top-versus-random controls, the strict joint criterion of a positive bootstrap interval and study-wide corrected significance passes TreeSHAP in 24/24 and LIME in 20/24. The explained samples contain 57-95 connection groups per context; repeated model seeds are not pooled as independent traffic.

Seed-42 calibration, weighting, masking-reference, LIME-budget, and feature-ablation audits are complete. Weighting is not uniformly beneficial: on Gotham multiclass, the unweighted Random Forest scores 0.8791 versus 0.8748 for the weighted primary model, and unweighted XGBoost scores 0.8686 versus 0.8659. These are diagnostic fixed-test comparisons, not a justification for test-driven model selection. Current latency was measured during concurrent jobs and is descriptive.

Statistical recomputation uses original per-context fidelity CSVs with round-trip float parsing. The aggregated convenience CSV passes through default parsing and rewriting, which can perturb near-ties and alter Wilcoxon ranks. Recorded endpoints are recomputed from the original precision-preserving context evidence, with aggregate consistency checked separately.

## Completed verification

`verify_recent_benchmark.py --verify-raw` passes in the fresh Python 3.12.14 environment. It checks the author-record chain, acquisition snapshots, GeNIS provider MD5s, every acquired source SHA-256, Gotham member CRC32/lengths, prepared-file hashes, source-group separation, source-row identities, frozen benchmark/audit code, model/input hashes, complete context coverage, matched explanations, group-level statistical recomputation, and study-wide corrections. All 17 unit tests pass, including the near-tie round-trip CSV and floating-point portability regressions. Frozen metadata and hashed runtime sources have Git byte-preservation rules. The research update was published in [commit 6579189](https://github.com/Jubayed-Sahel/Intrusion-Detection-System-Research/commit/6579189a241cf8e7eeab8792f1b988bef08d5586) on 14 October 2026. Its [hosted research-integrity workflow](https://github.com/Jubayed-Sahel/Intrusion-Detection-System-Research/actions/runs/38556657111) passed the unit tests and current/historical artifact checks. Raw-data and local model-file rehashing remain local checks because those files are excluded from Git.

All six manuscript pages were rendered and visually inspected. Columns, tables, and figures were checked; searchable text, embedded fonts, formatted predictive means, and cohort counts agree with the verified outputs. This visual/technical review does not replace the target venue's PDF or submission checks.

The recent experiment was executed in the recorded fresh environment. Reusing its completed checkpoints does not constitute another independent retraining. A separate reproduction must use a copied configuration with a fresh output directory for both benchmark and extended-audit runners.

## Historical work retained

The old study remains available for comparison and traceability:

- Corrected CIC multiclass cross-partition feature overlap, leaving 24,902 test rows, and reran affected models and explanations.
- Corrected duplicates and feature-vector overlap in the reduced UNSW mirror. The cleaned derivative has 96,822 training and 47,716 test rows; class proportions differ substantially from the mirror.
- Completed 100-flow explanations across three model seeds for 24 historical contexts, with matched pairs and study-wide Holm correction. Historical TreeSHAP-versus-LIME results passed in 24/24 contexts; TreeSHAP and LIME top-versus-random passed in 24/24 and 21/24, respectively, under that masking reference.
- Reproduced all eight corrected historical seed-42 predictive contexts exactly in a fresh Python 3.12 environment. Recorded package lists disclose transitive version differences.
- Audited minority labels and reduced-feature ambiguity. Multiple historical UNSW attack labels share 302 test feature vectors involving 1,274 rows; the unknown conversion prevents a diagnosis of source-label error versus feature aliasing.
- Batched the alert-report masking controls and measured a historical three-alert-per-context report pilot. Its 67.2-845.4 ms configuration medians are not recent-data timing, tail-latency, or throughput evidence.
- Repaired historical manuscript generation and retained the six-page draft, reference metadata, old audit evidence, and independent-environment results.

The historical bibliography identity checks do not by themselves establish support for every new claim. The recent manuscript must cite and discuss its new dataset sources and actual findings.

## Material limits for the current paper

GeNIS provides flows and Gotham provides packets; scores are reported separately, without treating the units as interchangeable. Each is a controlled testbed with connection holdout within its own capture environment. Sampling alters priors. Rare labels may not have an independent test connection, so test support and training-only labels are central to interpretation.

Connection-level inference reduces packet/window dependence but does not eliminate campaign or capture dependence. Five predictive seeds and three explanation model seeds describe algorithmic variation on a fixed split, not repeated independent datasets. Deletion fidelity remains dependent on reference values and may mask features into implausible combinations. It is a behavioral test, not causal evidence.

No temporal holdout, cross-organization evaluation, human analyst experiment, live security deployment, production drift, or recent-data throughput study has been completed. A claim of operational benefit would require the corresponding evidence rather than only an explanation score.

## Remaining submission work

1. Choose a specific IEEE journal or conference and apply its exact template, page limit, anonymity, and disclosure requirements. The current generated draft is IEEE-style, not venue-certified.
2. Have the supervisor and named authors review the design, source-label limitations, claims, references, novelty, and AI-assisted contributions.
3. Populate author/affiliation metadata, complete any venue-required similarity and PDF checks, and arrange a reviewed versioned release and archival DOI if appropriate.
4. Conduct the prepared analyst or live/drift studies if the eventual submission makes those claims. Existing protocols are plans, not observations.

## Local deliverables

- Current manuscript: `output/pdf/xai_ids_recent2025_paper.pdf` (six-page anonymous draft, visually reviewed).
- Current results, manifest, prepared-input provenance, source snapshots, and connection-group statistics: `outputs/recent2025/`.
- Current numerical and predictive summaries: `outputs/recent2025/summary.json` and `predictive_summary.csv`.
- Current alert examples: `outputs/recent2025/alert_reports/genis_binary_xgb_example.md` (`SUPPORTED_FOR_THIS_ALERT`) and `gotham_binary_xgb_example.md` (`REVIEW_REQUIRED`).
- Current acquisition and conversion notes: `RECENT_DATASET_PROVENANCE.md`.
- Primary versus historical source status: `DATA_PROVENANCE.md`.
- Historical manuscript: `output/pdf/xai_ids_ieee_paper.pdf`.
- Historical expanded validation and independent environment: `outputs/research_validation_corrected/` and `outputs/clean_reproduction/`.
- Historical source/minority audits, bibliography metadata, and environment locks: `outputs/research_validation/`.
- Submission and follow-up preparation: `IEEE_SUBMISSION_NOTES.md`, `RESEARCH_NEXT_STUDIES.md`, and `REFERENCE_VALIDATION.md`.
