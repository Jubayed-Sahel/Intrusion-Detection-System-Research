# Extended evaluation — 9 November 2026

Both studies in [the locked protocol](EXTENDED_VALIDATION_PROTOCOL.md) are complete. The original benchmark, models, and results remain unchanged.

- **Uncapped source tests:** all eight GeNIS and 65 previously assigned Gotham source files were read. Of 38,208,586 raw records, 7,670 were unknown-labeled and 259,526 had connection keys present in the corresponding fold training set. The remaining **37,941,390** were scored without test caps by the same 64 fixed detectors. Counts describe unique input records across source folds, not independent network observations. The 13 Gotham files without a capped assignment are not part of this comparison.
- **The difficult scenario remains difficult.** The uncapped GeNIS scenario 6 XGBoost detector missed 10,003/11,995 attacks and raised 15 false alarms over 33,670 benign records. Scores can shift when the test composition changes even though the model stays fixed.
- **Independent capture:** the official [Federated OCPP 1.6 dataset](https://zenodo.org/records/14887131) provides 4,415 flows from an EV-charging testbed. New binary classifiers were trained only on GeNIS, with harmonized features and no target tuning. With protocol and ports only, the two models missed 2–5 of 3,532 attack-labeled flows but flagged 303–325 of 883 benign flows. Adding duration and packet count improved GeNIS scores but reduced OCPP macro-F1 to 0.637–0.657. It missed 807–821 attacks, primarily unauthorized access.
- **Scope:** The external data are balanced by the provider across five categories and use a different flow exporter. This tests a limited form of binary transfer and does not measure natural attack prevalence or the transfer of the original full-feature models or their explanations.

Reproduce from the project root with the pinned environment:
1. Run `python run_extended_validation.py GeNIS2025` and `python run_extended_validation.py Gotham2025`.
2. Run `python run_extended_validation.py external`.
3. Run `python -m unittest discover -s tests`. The extension reader checks output hashes and reconstructs macro-F1 from 64 uncapped confusion matrices and external error counts from per-label results.

Results and manifests: [GeNIS](outputs/extended_validation_20261108/uncapped_GeNIS2025/), [Gotham](outputs/extended_validation_20261108/uncapped_Gotham2025/), [OCPP](outputs/extended_validation_20261108/external/).
