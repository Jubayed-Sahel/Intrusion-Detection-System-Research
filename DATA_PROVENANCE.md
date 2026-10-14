# Dataset provenance and reproducibility

The primary study now uses separately acquired author-published **GeNIS2025** and **Gotham2025** data. This replacement resolves the original source-history gap for the primary inputs through recorded official acquisition, member checksums, deterministic transformation code, frozen source snapshots, and prepared-file SHA-256 hashes. It does not recover or certify the missing conversion history of the four earlier CIC/UNSW parquet files.

## Current primary inputs

- **GeNIS2025:** [official author record 14919237](https://zenodo.org/records/14919237), version 1.0.0, published 24 February 2025; [primary data article](https://doi.org/10.1016/j.dib.2025.111487). `0-info.zip` and `3-scenarios.zip` pass the provider's full-file MD5 checks and have local SHA-256 hashes. The preparation scans all eight five-second scenario CSVs, keeping the author's category target.
- **Gotham2025:** [official author record 14502760](https://zenodo.org/records/14502760), published 5 February 2025; [authors' paper](https://arxiv.org/abs/2502.03134). All 78 processed device CSVs are retrieved from the official archive. Each full member passes the ZIP index's CRC32 and length checks and has a local SHA-256 hash. The 23.8 GB whole-archive MD5 is not recomputed.

Both author records specify CC BY 4.0. Their original traffic already comes from controlled testbeds; this project consumes the authors' CSV features and labels rather than claiming to independently rebuild them from packet captures or independently validate every source label.

The exact acquisition and transformation procedure is in [RECENT_DATASET_PROVENANCE.md](RECENT_DATASET_PROVENANCE.md). Local acquisition files are under `data/official/`, and preparation records and frozen conversion code are under `data/prepared/`. `outputs/recent2025/acquisition_snapshots/` keeps post-acquisition copies of author metadata, ledgers, the ZIP member index, and retrieval scripts with a separately timed hash manifest. It does not establish download-time retrieval-code hashes. The committed `outputs/recent2025/run_manifest.json` embeds preparation provenance and records the benchmark configuration, package versions, and source hashes. Extended audits freeze their own runner/helper code and input hashes. The paired and control tables use explained connection groups as the inference unit.

The replacement pipeline excludes Gotham's ambiguous `Unknown` label from both supervised tasks, caps each remaining label at 10,000 records, holds out global connection groups, excludes identifier/target/export artifacts from model inputs, and fits preprocessing only on training data. Full scanned source counts are retained alongside the excluded-label counts. Class counts, training-only classes, retained identical feature patterns, exclusions, member hashes, and output hashes are disclosed in the provenance manifest. CoAP Amplification has no held-out connection; primary `macro_f1_supported_classes` uses test-supported classes, while `macro_f1_training_vocabulary` also includes the training-only class. The recent benchmark is a new experiment and may legitimately produce different results from the historical study.

DataSense 2025 was also checked through its [official provider page](https://www.unb.ca/cic/datasets/iiot-dataset-2025.html). Its download landing page requests registration, and the official browse endpoint still returned HTTP 403 on the 14 October 2026 retry. The user chose openly accessible official data, so GeNIS and Gotham were acquired.

## Historical CIC-IDS2017 and UNSW-NB15 inputs

The four earlier local parquet files match the SHA-256 values in the historical `outputs/run_manifest.json`. This confirms file identity, not equivalence to the official source datasets. The original mirror URL, revision, conversion script, and feature selection history have not been supplied and remain unknown.

Official sources checked on 14 October 2026:

- [CIC-IDS2017](https://www.unb.ca/cic/datasets/ids-2017.html): the provider distributes packet captures and flow CSVs. The historical local representation contains 2,830,743 flows with 28 selected features and lacks capture-day metadata. Its missing transformation prevents a claim of official-source reproduction.
- [UNSW-NB15](https://research.unsw.edu.au/projects/unsw-nb15-dataset): the provider describes predefined partitions with 175,341 training and 82,332 testing records. Matching counts alone does not establish row identity. Historical local filenames are reversed relative to their configured roles, and the loader removes substantial duplicates and cross-partition feature overlap in the 34-feature representation.

The historical loader removed 78,519 duplicate training rows, 32,361 duplicate test rows, and 2,255 test feature vectors also present in training. The resulting UNSW partition has 96,822 training and 47,716 test rows. One additional CIC multiclass cross-partition feature vector was removed, leaving 24,902 test rows in that context. These corrections apply to the observed parquet representations, not proven duplicate real-world captures.

## Historical independent-environment reproduction

The corrected seed-42 predictive results for all eight historical dataset/task/model contexts reproduced exactly in a fresh Python 3.12 environment. Expanded 100-flow, three-model-seed explanation evidence is under `outputs/research_validation_corrected/`; separate clean-environment results are under `outputs/clean_reproduction/`. These are historical evidence and are not reused as results for the 2025 study.

```powershell
.\.venv-reproduction\Scripts\python.exe -B -m unittest discover -s tests -v
.\.venv-reproduction\Scripts\python.exe -B verify_outputs.py
.\.venv-reproduction\Scripts\python.exe -B run_research_validation.py --output outputs/clean_reproduction --seeds 42 --samples 100
```

`outputs/research_validation/original-environment-lock.txt` and `clean-environment-lock.txt` record all installed dependencies. Top-level pins agree, but transitive package versions can differ because `requirements.txt` does not lock them. The clean run tests portability across the recorded environments rather than byte-for-byte environment identity.

Hash checks and independent retraining do not replace the missing source conversion record. If the old files are used in a future primary claim, obtain that record or reconstruct them through a separately documented official-source pipeline; do not invent historical provenance.

## Historical representation ambiguity

The cleaned UNSW data retain multiple attack labels for 1,397 identical training feature vectors involving 6,121 rows and 302 identical test vectors involving 1,274 rows. Binary targets also conflict for 259 training vectors involving 526 rows and 20 test vectors involving 42 rows. These cases are within partitions and do not renew train/test overlap. They remain because removing difficult labels selectively would change the evaluation.

Reduced-feature aliasing and source-label errors cannot be distinguished without the missing conversion history and full source data. Class-dependent removal fractions are recorded in `outputs/research_validation/unsw_cleaning_by_class.csv`; about 93.5% of Generic test rows were removed from the historical mirror. The corrected historical scores therefore describe that derivative and should not be presented as official-dataset leaderboard results.
