# GeNIS training-size experiment

This exploratory experiment asks whether supplying more training rows improves binary detection on unseen GeNIS source scenarios. Reuse the eight saved source assignments, one author CSV per fold. Score every row of the held-out CSV. Remove training rows sharing a provider FlowID with any row in the held-out CSV, even if the matching test row would have been excluded from an earlier experiment.

Draw nested, uniform samples without replacement of 10,000, 40,000 and 160,000 rows from the same eligible pool per fold. Generate one deterministic sample order per fold from seed 42 plus the fold number. Keep the raw training class mix and apply the existing model weighting. Use the existing GeNIS predictor exclusion list, no feature selection, and refit preprocessing on each training prefix. Fix Random Forest and XGBoost settings and seed 42. Use the default binary decision boundary. Training sizes and metrics are fixed before fitting.

Report macro-F1, attacks missed and benign false alarms for each fold and size. Summarize paired changes with equal weight per scenario and show reversals. Treat folds as descriptive because their training pools overlap. Sample size changes the number of rows and can change the mixture of connections and attack categories. This design covers binary GeNIS source transfer only.
