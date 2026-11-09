# Q1 journal working draft

The working target is IEEE Transactions on Dependable and Secure Computing (TDSC). Its stated scope includes security evaluation, which fits this empirical audit. The 2025 SCImago-based listing reports Q1. If the institution requires a Clarivate JCR quartile, confirm the exact edition and category through the institutional subscription. The manuscript uses IEEEtran journal mode and is 10 pages. IEEE Computer Society currently defines 12 formatted pages as the regular Transactions length for overlength charges, including references and author biographies.

[TDSC scope and submission route](https://www.computer.org/digital-library/journals/tq/cfp-dependable-secure-computing) · [IEEE Computer Society author guidance](https://www.computer.org/publications/author-resources) · [2025 SCImago-based listing](https://scienceaijournal.com/journals/ieee-transactions-on-dependable-and-secure-computing-1545-5971)

## New evidence

- A source-trained protocol-only rule scores 0.920 macro-F1 on the OCPP capture. The corresponding transport-only Random Forest and XGBoost scores are 0.874 and 0.865. The protocol-only rule misses zero of 3,532 attacks and raises 206 false alerts on 883 benign flows. The same rule scores 0.771 macro-F1 on GeNIS versus 0.995 for both trees to three decimals.
- All 3,532 OCPP attacks use TCP. In the TCP-only subset, the two transport-only trees each flag 161 of 162 benign TCP flows. The protocol-only rule flags all 162. The TCP check replays the original source-trained model specification and verifies that full-capture error counts reproduce. This is a post-hoc diagnostic on the same external capture.
- Under a hypothetical 1% attack prevalence, the protocol rule's projected positive predictive value is 4.2% and the transport trees' is 2.7–2.9%, conditional on unchanged measured rates. These scenarios illustrate sensitivity to prevalence. They do not measure production alert loads.

Run `python run_journal_audit.py` after reproducing the previous transfer study and obtaining its verified inputs. Build with `python build_recent_paper.py --journal`. The generator checks the protocol, runner, transfer manifest and output hashes before inserting the findings. Editable source is in `paper/journal` and results are in `outputs/journal_audit_20261109`.

## Before submission

- The journal draft now reports a second independent binary check on PDMFC, with both labels on TCP and an exact mixed-label port-pair diagnostic. The frozen GeNIS model configuration transfers to two capture files or datasets under the documented conditions. Further captures are needed for claims about wider traffic distributions.
- The journal draft tests explanation fidelity on GeNIS and Gotham under specified replacement rules. External explanation fidelity and analyst decisions remain untested. Keep those boundaries in the abstract, cover letter and submission metadata.
- Confirm affiliations, corresponding author, funding and conflicts with every author. Agree on the archival code and results release, verify the journal's current instructions at upload, and disclose any related conference submission or publication.
