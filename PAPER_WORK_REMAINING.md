# Research closeout and remaining work

Updated 9 November 2026. The current study is complete within its documented scope. Publication decisions and author approval are deferred.

## Completed research

- Official GeNIS 2025 and Gotham 2025 data preparation, connection-group separation, training-only preprocessing, and coverage reporting. GeNIS archive and member checks and Gotham member checks retain their separate scopes. The complete Gotham archive checksum remains unverified. See [dataset provenance](RECENT_DATASET_PROVENANCE.md).
- The primary analysis contains 40 predictive fits, 24 paired explanation comparisons, 48 random-control comparisons, and eight extended audit contexts. The [literature review](LITERATURE_REVIEW_20261107.md) records 20 additional full-text reviews and the resulting design choices.
- The source-holdout replay covers 64 detector fits and 64 matched explanation comparisons. See [the methods and results](PUBLICATION_EXTENSION_20261108.md) and [the saved numerical replay](outputs/source_holdout_20261108/saved_results_replay.json).
- Fixed source-held-out models scored 37,941,390 eligible records without applying a test-time class cap. A separate EV-charging capture supplied 4,415 flows for reduced-feature binary transfer. See [extended validation](EXTENDED_VALIDATION_RESULTS.md).
- A protocol-only baseline and a TCP-only diagnostic exposed a shortcut in the EV-charging capture. Both protocol-and-port tree models falsely flagged 161 of 162 benign TCP flows. The [journal audit](Q1_JOURNAL_READINESS.md) records the baseline and prevalence sensitivity results.
- The [training-size experiment](TRAINING_SCALE_PROTOCOL.md) tests 10,000, 40,000, and 160,000 training rows on the same complete GeNIS source holdouts. The journal draft reports the paired changes, and [fold-level results](outputs/training_scale/metrics.csv) retain both missed attacks and false alarms.
- The [independent TCP check](INDEPENDENT_TCP_PROTOCOL.md) reproduces the OCPP false-alarm problem on PDMFC v1. The two protocol-and-port trees falsely flag 11,882 and 11,834 of 12,006 benign TCP flows. Both also flag all 52 benign flows in the exact mixed-label port-pair subset. See [all error counts](outputs/independent_tcp/metrics.csv).

## Research package

- [Journal-format manuscript](output/pdf/xai_ids_traffic_sources_and_feature_masking.pdf) and [editable LaTeX](paper/journal/main.tex)
- [Detailed report](output/pdf/xai_ids_recent2025_paper.pdf) and [anonymous review archive](output/ids_xai_anonymous_review.zip)
- [Index of protocols, results, and rerun instructions](SUPPLEMENTARY_INDEX.md)
- Run `python -m unittest discover -s tests` and `python verify_research_closeout.py` for the local checks. The latter replays frozen evidence from a clean checkout without raw data or fitted models. With the official GeNIS and Gotham inputs present, `--verify-raw` also rehashes the consumed source files. The verification is an internal replay of recorded evidence. It does not establish independent retraining of all experiments.

## Future evidence for broader claims

- The two external captures support a binary diagnostic for the reduced-feature models. Additional independently repeated captures would be needed to estimate broader cross-network performance. The study measures explanation fidelity on GeNIS and Gotham under specified replacement rules. External explanation fidelity remains untested.
- A human-analyst study would be needed to measure decisions and usability. Live drift and workload measurements would be needed to assess deployment.

## If publication is resumed

Confirm each author's affiliation, contributions and approval, plus the corresponding author, funding and conflicts. Confirm the chosen venue's requirements and decide how to archive the code and evidence with the coauthors. The journal and conference formats are available for review.
