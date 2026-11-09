# Source-separated holdout feasibility

Checked 8 November 2026 against the local prepared cohorts, without fitting models or changing the frozen primary experiment. Machine-readable counts and input SHA-256 values are in `outputs/holdout_feasibility_20261108.json`.

## Recommended additional experiment

Run an exhaustive leave-one-scenario-out stress test on the eight GeNIS scenario files. Fix the source ordering before fitting, hold out each source once, and purge every training record whose global connection-group identifier occurs in that held-out source. Use the declared primary hyperparameters, a declared model seed, and preprocessing fitted separately on each fold's training records. Do not choose a source split using its eventual score. Report every fold, including poor scores, and describe the experiment as a post hoc source-separated stress test on the already sampled cohort.

The 40,000 selected GeNIS records contain 29,359 connection groups across eight source files. There are 920 groups spanning multiple source files, so simply splitting files would leak groups. Group purging removes 3,934–4,029 training rows per fold. The resulting folds have 27,582–32,954 training rows, 3,039–8,484 test rows, and zero group overlap. Every held-out label still has training examples in every fold. Benign and reconnaissance occur in all eight scenarios; denial of service occurs in the five `disrupt` scenarios; brute force occurs in the three `authtest` scenarios. Thus each held-out scenario has only three of the four overall labels. State which labels have test support rather than implying four-label testing in every scenario.

This experiment is feasible and more demanding than the original within-cohort connection-group split. It tests transfer among recorded scenarios from one testbed. It does not establish transfer to another enterprise, campaign, or capture period.

## Gotham extension

The 133,490 selected Gotham records represent 65 of the 78 acquired CSV files. The remaining 13 source files received no records under the declared class cap; they must not be described as evaluated sources. The selected cohort contains 58,269 connection groups, of which 3,991 span source files. The global group definition must also be purged here.

Eight selected sources contain attack labels. Their held-out test folds contain 130,318 records, including 6,828 benign records. The other 57 selected source files contain 3,172 benign records in total. An economical, explicitly scoped extension can predeclare the eight attack-bearing sources as the mixed-label source stress test; a comprehensive device-source validation would also evaluate the 57 benign-only files and report false-alarm rates separately. Choosing the eight sources using label coverage is a design decision made before model fitting, not a performance-based choice; their results must not be presented as covering all 65 sources.

The `iotsim-combined-cycle-1.csv` fold is particularly important: all 10,000 CoAP Amplification records and all 4,242 UDP Scan records occur in this source only. After source holdout and group purge, these two multiclass labels have no training examples. They account for 14,242 of the fold's 41,749 test rows (34.11%). All other attack-bearing source folds retain every held-out multiclass label in training. Do not silently drop these novel labels. Report all-test supported-label macro-F1, their counts and zero possible multiclass recall, plus an explicitly secondary known-label-only score if useful. In the binary task those records map to the already trained attack category, so binary detection of these records and multiclass naming are different questions.

Per-fold training rows after purging range from 84,095 to 131,871 over the eight attack-bearing sources. The small benign support in several attack-heavy sources (as low as one record) makes their individual false-alarm rates highly uncertain. Report benign counts with those rates.

## Preprocessing and interpretation safeguards

- The prepared union has already used the original primary training partition to choose its feature inventory. Fifteen GeNIS columns and Gotham `ip.tos` were removed as primary-training constants. A sensitivity study may explicitly reuse this fixed, previously declared inventory and then fit imputation, encoding, and any further constant removal within each new training fold. It must not claim that this feature inventory was newly selected without exposure to the original primary split. Reconstructing the sampled raw source rows would allow the original candidate columns to be restored and constant removal repeated fully within each new fold.
- Keep the source metadata, group identifiers, row identifiers, and labels out of predictors. Hash and freeze the new protocol, source ordering, model settings, input files, and implementation separately from the frozen primary experiment.
- These are source-separated folds, not chronological folds. Gotham raw CSVs retain `frame.time`, while the prepared cohort does not. A chronological experiment would require mapping retained `__source_row` values back to the raw files, declaring a time cutoff before seeing scores, and purging groups crossing the cutoff. The existing GeNIS time-of-day values do not support an unambiguous full chronological split across days.
- Class-capped sampling was already performed over the original source collection. These additional evaluations consequently describe the sampled cohort, not deployment prevalence or an independently acquired prospective sample.
- Repeated source folds share training records. Do not treat fold scores or model seeds as independent deployment samples. Show every fold, supported-label coverage, and descriptive mean/range; avoid a population generalization interval unsupported by the small, dependent source collection.
- No selected connection group spans two different labels in either dataset. This is a consistency check, not proof that labels or captures are error-free.

## Per-fold GeNIS counts after purging

- Scenario 1: 3,039 test rows; 32,954 training rows; 4,007 training rows purged.
- Scenario 2: 3,682 test rows; 32,329 training rows; 3,989 training rows purged.
- Scenario 3: 4,889 test rows; 31,100 training rows; 4,011 training rows purged.
- Scenario 4: 4,859 test rows; 31,149 training rows; 3,992 training rows purged.
- Scenario 5: 4,855 test rows; 31,116 training rows; 4,029 training rows purged.
- Scenario 6: 5,829 test rows; 30,162 training rows; 4,009 training rows purged.
- Scenario 7: 4,363 test rows; 31,670 training rows; 3,967 training rows purged.
- Scenario 8: 8,484 test rows; 27,582 training rows; 3,934 training rows purged.

The JSON file includes source-level row counts, group counts, label counts, retained training labels, unsupported labels, and zero-overlap checks for all eight GeNIS and all 65 selected Gotham source files.
