# Official 2025 dataset acquisition and preparation

**Record date:** 14 October 2026. These notes describe a new primary study using author-published GeNIS and Gotham data. The historical CIC/UNSW parquet history remains unknown and is documented separately in [DATA_PROVENANCE.md](DATA_PROVENANCE.md).

## Author sources, dates, and attribution

**GeNIS: GECAD Network Intrusion Scenarios** was published as [Zenodo record 14919237](https://zenodo.org/records/14919237), DOI [10.5281/zenodo.14919237](https://doi.org/10.5281/zenodo.14919237), version 1.0.0 on 24 February 2025. Its creators are Miguel Silva, Daniela Pinto, João Vitorino, José Gonçalves, Eva Maia, and Isabel Praça. The record describes enterprise-network simulations on Airbus CyberRange and requests citation of the [primary data article, DOI 10.1016/j.dib.2025.111487](https://doi.org/10.1016/j.dib.2025.111487).

**Gotham: A Device-Level IoT Network Traffic Dataset with Distributed Capture and Non-IID Characteristics** was published as [Zenodo record 14502760](https://zenodo.org/records/14502760), DOI [10.5281/zenodo.14502760](https://doi.org/10.5281/zenodo.14502760), on 5 February 2025. Its creators are Othmane Belarbi, Theodoros Spyridopoulos, Eirini Anthi, Omer Rana, Pietro Carnelli, and Aftab Khan. The [authors' paper](https://arxiv.org/abs/2502.03134) describes the dataset. The record preserves packet traffic from the interfaces of 78 IoT devices in a virtual smart city, with labels derived from orchestration metadata.

Both author records specify **CC BY 4.0**. Attribute the datasets and their papers and describe the sampling, feature exclusions, grouping, and conversion as this project's modifications. Local original sources are not committed to this repository.

Publication year and traffic-capture time are different facts. The retained GeNIS scenario CSVs expose time-of-day information but do not supply a complete per-row date for this pipeline; `source_date_range_utc` is therefore null for GeNIS. Gotham timestamps are parsed across every input row, and their observed range is written to its preparation provenance. Neither release year nor a connection-group holdout establishes temporal generalization.

## Acquisition evidence

The acquisition occurred on 13 October 2026 UTC, which is 14 October in the local Asia/Dhaka timezone. `provider_record.json` preserves the author record metadata downloaded from Zenodo. `acquisition.json` records the specific URLs, acquisition timestamps, source sizes, and integrity checks. `freeze_recent_acquisition.py` copies eight provider-record, ledger, member-index, and retrieval-script files into `outputs/recent2025/acquisition_snapshots/`, with a timed SHA-256 manifest. These are explicitly **post-acquisition** snapshots; they do not assert download-time hashes of the retrieval scripts.

For **GeNIS**, `fetch_recent_datasets.py` downloads the entire `0-info.zip` and `3-scenarios.zip` from record 14919237. Transfers use length-checked ordinary HTTP byte ranges where needed. The full files are checked against the author record's MD5 values, then assigned local SHA-256 hashes:

- `0-info.zip`: 3,308 bytes; provider MD5 `432ada3813f0261ac8b5e371ea4d729e`; SHA-256 `7ef636cc758586f18a5d9958e68eede9b85925610331283cce802f45542701bc`.
- `3-scenarios.zip`: 491,738,368 bytes; provider MD5 `7c560f37af540c9e65abae813bdacab4`; SHA-256 `8a56adc70d4400786b774012c69af1d5264d6733986d5a6d5d500e66b57cf246`.

The preparation consumes all eight `3-scenarios/scenarios-5-sec/*.csv` members. It does not combine the 10-, 30-, or 60-second alternatives, which would aggregate overlapping traffic at multiple intervals. Every consumed member is fully scanned and SHA-256 hashed. `0-info.zip` contains author feature and ground-truth descriptions; the prepared targets come from the author's scenario CSV category labels.

For **Gotham**, `fetch_gotham_members.py` reads the official `GothamDataset2025.zip` index and retrieves all 78 `processed/*.csv` members plus its README directly from the same public archive using HTTP byte ranges: **79 acquired archive members**. The separately downloaded `provider_record.json` is Zenodo record metadata. Each retrieved member is fully decompressed, checked for its expected uncompressed byte length and ZIP CRC32, and assigned a local SHA-256 hash. `member_index.json` and `acquisition.json` preserve the member identities and offsets.

The provider's complete archive is 23,824,968,355 bytes and advertises MD5 `7ca78c0517ccb3d2854e823678e0f206`. **That whole-archive MD5 is not recomputed.** The integrity claim covers the retrieved members, not a downloaded full archive. CRC32 is a ZIP consistency check; local SHA-256 pins the exact acquired member bytes. No independent provider SHA-256 exists for these individual members. The project consumes the authors' processed features and labels and does not claim a fresh extraction from the PCAP files.

## Deterministic transformation

`prepare_recent_datasets.py` calls `src/xai_ids/recent_data.py` with seed 42 and a cap of 10,000 records per source label. The exact preparation source bytes are frozen as `data/prepared/<dataset>/preparation_source.py`, with their hash in `provenance.json`.

1. Scan every selected source CSV in sorted member order and record its full row count and SHA-256. Reject missing labels. For Gotham, also reject unparsed timestamps and record the observed UTC range. Count all source labels before excluding Gotham's `Unknown` records from supervised preparation; their benign/attack meaning is unspecified.
2. Assign independent deterministic RNG priorities and retain the lowest priorities per eligible label across all members. Each class contributes at most 10,000 records, so a rare class may contribute fewer. Keep the original member name and zero-based source row for auditability. The exclusion record preserves the ambiguous label's full source count.
3. Construct global connection groups. GeNIS uses the author's `FlowID` across all scenario files. Gotham uses a canonical bidirectional IP/transport-port tuple plus IP protocol across all device files, with numeric port normalization and TCP-to-UDP fallback. These groups are audit metadata and are excluded from model features.
4. Freeze the first seed-42 `GroupShuffleSplit` candidate that covers eligible labels in test and leaves every test label known in training. The requested test fraction is 20% of eligible groups, not necessarily 20% of rows. Labels confined to one sampled group have that whole group assigned to training; their absence from test is recorded. This uses label coverage before fitting and does not select the split based on test scores.
5. Exclude declared identifier, timestamp, target, and payload/export columns. Coerce declared numeric features with nonfinite values mapped to missing; parse Gotham hexadecimal flags as integers. Keep the declared categorical fields.
6. Remove constants using only training data, then save `train.parquet` and `test.parquet`. Record both file hashes, sizes, features, exclusions, constants, label counts, grouping counts, and retained cross-partition identical feature patterns.
7. During model fitting, learn medians and categorical dictionaries only from training data. No scaling or imputation occurs before the split.

The per-label cap deliberately changes priors. Model accuracy, calibration, and false-positive/negative rates refer to the resulting sampled testbed derivative rather than natural deployment prevalence. Sampling individual records also means that the group structure describes the retained sample, not every event in the full source archive.

GeNIS keeps the author's four category labels: `benign`, `bruteforce`, `dos`, and `recon`; it does not claim fine-subtype detection. Gotham keeps the remaining source `label` taxonomy after excluding `Unknown` from both supervised tasks. Both binary tasks map case-insensitive `benign` to Normal and the remaining eligible labels to Attack. The per-class metric files must be read alongside test support and any training-only labels. Primary `macro_f1_supported_classes` averages classes with actual test support; `macro_f1_training_vocabulary` averages all training labels, and the original `macro_f1` uses the actual/predicted-label union. The explicit vocabulary metric can assign zero to a class without held-out support; that number is not a measurement of its detection ability.

## Prepared data and separation

The current GeNIS preparation scans **3,087,981** source flow rows and samples 40,000 rows: 10,000 per category. It produces **32,346 training rows**, **7,654 test rows**, and **69 model features**. Global groups number 23,487 in training and 5,872 in test, with **zero shared groups**. No category is confined to training. There are 379 test rows whose feature pattern also occurs in training; these observed patterns are retained because equal behavior across distinct connection groups is not automatically the same source record.

The full Gotham scan covers **35,134,281 source packets**, including **7,670 `Unknown` records** excluded from supervised preparation. Observed source timestamps span **14-25 January 2025 UTC**. The corrected sample has **133,490 packets** across **17 known labels**, with **107,120 training rows**, **26,370 test rows**, and **13 model features**. The fixed split uses the first label-covered candidate, index 11, and contains 46,615 training groups and 11,654 test groups with **zero shared groups**. Sixteen known labels have test support; **CoAP Amplification** is confined to one sampled connection group, stays in training, and has no held-out performance claim. There are 1,914 test rows whose feature pattern also occurs in training, retained under the declared policy. Exact class distributions and hashes are recorded in `data/prepared/Gotham2025/provenance.json` and embedded in `outputs/recent2025/run_manifest.json`.

The earlier GeNIS attempt grouped by filename plus flow ID. A subsequent audit found that IDs can recur across scenario files. That partial attempt was stopped and archived locally under the ignored `outputs/recent2025_pre_global_group_fix/`. The current result directory uses global provider flow IDs and the corrected preparation hashes.

The subsequent full Gotham scan exposed the ambiguous `Unknown` label. The partial run before its exclusion is retained locally under the ignored `outputs/recent2025_pre_unknown_label_fix/`. Both primary datasets were prepared and rerun with the final frozen preparation and scoring code; neither partial attempt contributes to the reported primary tables.

Identical feature vectors are audited separately from shared connection groups. The pipeline retains repeated feature patterns and enforces zero shared source groups. This differs from the historical parquet workflow, where reliable source identifiers were unavailable. Connection grouping is still an imperfect dependence boundary: a longer campaign or capture can contain multiple connections, and the holdout is neither a new capture nor a new organization.

## Benchmark and explanation traceability

`config_recent.yaml` fixes five predictive seeds (42, 52, 62, 72, 82) and three explanation model seeds (42, 52, 62). The benchmark uses both model families and both tasks on both datasets, with majority and depth-five-tree baselines. Each explanation context evaluates TreeSHAP and LIME on the same 100 selected held-out records. Selection is label-stratified and covers available binary actual/predicted combinations; a multiclass error is included when available but absent from the initial sample. This is a diagnostic sample rather than a probability sample of operational alerts. The benchmark records source test indices and connection groups for deletion evidence.

The primary deletion score averages k={1,3,5,10}. For uncertainty, deletion scores are averaged within each explained connection group, and those equal-weight group means enter paired bootstrap and one-sided Wilcoxon tests. Holm adjustment covers all 24 TreeSHAP-versus-LIME comparisons and all 48 top-versus-random tests in the complete study. Use `holm_adjusted_p_all_contexts` in the aggregate paired/control tables. Group counts may be below 100 and are reported as `n_pairs`; contexts with fewer than five groups are marked insufficient and cannot pass the significance gate. Per-record summary intervals are descriptive only.

`outputs/recent2025/run_manifest.json` embeds preparation provenance, pinned top-level dependency versions, configuration, and benchmark source hashes. `source_snapshots/` freezes the benchmark runner, shared benchmark module, and preparation module. Prepared files are hash-checked before fitting; configuration and frozen-source changes are rejected when resuming an existing run. The extended audit's `audit_manifest.json` and `source_snapshots/` separately record its runner, audit/benchmark/transparency helper sources, prepared inputs, and serialized model hashes at run start. `outputs/recent2025/environment-lock.txt` records installed packages, including transitive dependencies, and `runtime.json` records the Python 3.12.14 fresh-environment runtime. Its timing scope explicitly describes concurrent jobs; the measurements are not isolated service benchmarks. The verifier checks the result chain and recomputes group-level inference; `--verify-raw` also recomputes downloaded source hashes and member checks.

The complete numerical summary records 40 predictive fits, 24 paired contexts, 48 control comparisons, and eight extended-audit contexts. The explained samples contain 57-95 connection groups per context. All 24 TreeSHAP-minus-LIME group-mean contrasts have a positive bootstrap interval and pass study-wide Holm correction under the declared intervention. The strict top-versus-random criterion, requiring both a positive interval and corrected directional significance, passes for TreeSHAP in 24/24 contexts and LIME in 20/24. These conclusions concern this sampled derivative and intervention; they do not change the acquisition checks' scope.

For exact statistical recomputation, read the **original per-context** `contexts/<context>/fidelity.csv` with pandas `float_precision="round_trip"`. The benchmark computes its statistics before aggregating those exports. Default CSV parsing followed by a rewrite can perturb near-tied floating-point values and hence Wilcoxon ranks, despite negligible numerical differences in deletion scores. The aggregate `fidelity.csv` is a convenience copy, not the precision authority for statistical endpoints. The verifier recomputes inference from the original context files and checks the aggregate against its recorded construction.

## Reproduction commands

Run from the repository root after installing `requirements.txt` in a Python 3.12 environment:

```bash
python fetch_recent_datasets.py --record 14919237 --files 0-info.zip 3-scenarios.zip
python fetch_gotham_members.py
python freeze_recent_acquisition.py
python prepare_recent_datasets.py
python run_recent_benchmark.py --config config_recent.yaml
python run_recent_audit.py
python summarize_recent_results.py
python build_recent_paper.py
python -B verify_recent_benchmark.py
# Optional full rehash of locally acquired source data:
python -B verify_recent_benchmark.py --verify-raw
python -B -m unittest discover -s tests -v
```

The full `verify_recent_benchmark.py --verify-raw` check passed locally in the fresh Python 3.12.14 environment, and all 17 unit tests passed. Frozen metadata and hashed runtime sources have Git byte-preservation rules so cloned artifacts retain their recorded bytes. The historical commands and tables remain available for comparison but are not the primary recent-data workflow. These checks establish consistency of the recorded experiment; they do not establish source-label correctness, causal explanation validity, or submission acceptance.

Completed checkpoints are reused when resuming the same result directory. For independent retraining using the prepared official inputs, copy `config_recent.yaml` to `config_reproduction.yaml` and set `output_dir: outputs/recent2025_reproduction`:

```bash
python freeze_recent_acquisition.py --output outputs/recent2025_reproduction
python run_recent_benchmark.py --config config_reproduction.yaml
python run_recent_audit.py --config config_reproduction.yaml
python summarize_recent_results.py --output outputs/recent2025_reproduction
python build_recent_paper.py --results outputs/recent2025_reproduction --output output/pdf/xai_ids_recent2025_reproduction.pdf
python -B verify_recent_benchmark.py --output outputs/recent2025_reproduction --verify-raw
```

To repeat conversion independently, rerun `prepare_recent_datasets.py` before the benchmark and compare the new prepared-file hashes. A changed source or configuration requires a separate result directory; it cannot be mixed into this frozen primary experiment.
