# Recent-study reference and claim support

**Updated:** 14 October 2026

This record is for the GeNIS/Gotham manuscript in `src/xai_ids/recent_paper.py`. It is separate from the historical CIC/UNSW bibliography checks in `REFERENCE_VALIDATION.md`. Registration metadata establish bibliographic identity, not novelty, plagiarism clearance, or that a citation supports every nearby sentence. Supervisor and named-author review of the comparisons remains required.

## DOI identity

`verify_references.py` now extracts DOIs from both manuscript generators. Recent-study DOI records are written to `outputs/recent2025/reference_metadata.json`. Crossref is used for IEEE/ACM/Nature records; DataCite is used for Zenodo (`10.5281/`) and arXiv (`10.48550/`) records.

Checked primary records:

| ID | Claimed work | Identity check |
|---|---|---|
| [1] | Silva et al., GeNIS Zenodo 1.0.0, 24 Feb 2025 | DataCite/Zenodo DOI `10.5281/zenodo.14919237` |
| [2] | Silva et al., *Data in Brief*, vol. 60, art. 111487, 2025 | Crossref `10.1016/j.dib.2025.111487` |
| [3] | Belarbi et al., Gotham Zenodo v1, 5 Feb 2025 | DataCite/Zenodo DOI `10.5281/zenodo.14502760` |
| [4] | Belarbi et al., arXiv:2502.03134, 2025 | DataCite `10.48550/arXiv.2502.03134` |
| [5] | Lundberg and Lee, NeurIPS 2017 | NeurIPS abstract `8a20a8621978632d76c43dfd28b67767`; arXiv:1705.07874 |
| [6] | Lundberg et al., *Nat. Mach. Intell.*, vol. 2, pp. 56-67, 2020 | Crossref `10.1038/s42256-019-0138-9` |
| [7] | Ribeiro, Singh, and Guestrin, KDD 2016, pp. 1135-1144 | Crossref `10.1145/2939672.2939778` |
| [8] | Neupane et al., *IEEE Access*, vol. 10, pp. 112392-112415, 2022 | Crossref `10.1109/ACCESS.2022.3216617` |
| [9] | Arreche, Guntur, Roberts, and Abdallah, *IEEE Access*, vol. 12, pp. 23954-23988, 2024 | Crossref `10.1109/ACCESS.2024.3365140` |
| [10] | Gaspar, Silva, and Silva, *IEEE Access*, vol. 12, pp. 30164-30175, 2024 | Crossref `10.1109/ACCESS.2024.3368377` |
| [11] | Mane and Rao, arXiv:2103.07110, 2021 | arXiv abs/2103.07110; DataCite `10.48550/arXiv.2103.07110` |
| [12] | Yeh, Hsieh, Suggala, Inouye, and Ravikumar, NeurIPS 2019, pp. 10965-10976 | NeurIPS hash `a7471fdc77b3435276507cc8f2dc2569`; arXiv:1901.09392 |
| [13] | Adebayo et al., NeurIPS 2018 | NeurIPS hash `294a8ed24b1ad22ec2e7efea049b8737` |
| [14] | Warnecke, Arp, Wressnegger, and Rieck, EuroS&P 2020, pp. 158-174 | Crossref `10.1109/EuroSP48549.2020.00018` |

Do not cite `10.1109/EuroSP48549.2020.00021` for Warnecke; that DOI is Sperl et al., “DLA: Dense-Layer-Analysis for Adversarial Example Detection.”

## Claim support

| Manuscript claim | Supported by | Not supported / limit |
|---|---|---|
| GeNIS and Gotham are author-published 2025 releases used as primary inputs | [1]-[4]; `RECENT_DATASET_PROVENANCE.md`; `outputs/recent2025/run_manifest.json` | Release year is not capture year for GeNIS; Gotham timestamps are parsed from CSVs |
| SHAP/TreeSHAP and LIME are additive or local-surrogate attribution methods | [5]-[7] | Not a claim that either method is causal |
| Visual attributions can fail objective checks | [12], [13] | Those papers are not IDS studies |
| X-IDS literature asks for evaluation metrics and stakeholder-specific explanations | [8] | Survey recommendations are not measurements in this study |
| Mane and Rao demonstrate several explanation styles on NSL-KDD without a standardized deletion-control protocol | [11] abstract/methods: SHAP, LIME, CEM, ProtoDash, and Boolean rules | They do apply explanations; the gap is quantitative deletion/random-control protocol |
| Gaspar et al. perturb LIME/SHAP features and include a survey | [10] abstract | This project has no participant study and must not claim one |
| Warnecke et al. evaluate explanation criteria on malware and vulnerability tasks | [14] abstract | Not a network-flow/packet IDS benchmark |
| E-XAI scores SHAP and LIME with six metrics, including Wilcoxon tests, on NSL-KDD, CIC-IDS2017, and RoEduNet-SIMARGL2021 | [9] abstract and methods | Closest prior evaluation framework; not GeNIS/Gotham; descriptive accuracy is a model-accuracy change after feature removal |
| This study's contribution is provenance-traceable 2025 sources, Unknown exclusion, class caps, connection-group inference, matched TreeSHAP/LIME deletion, random/bottom controls, and Holm families of 24 and 48 | `outputs/recent2025/summary.json`; Sections IV-VI | Not novelty of SHAP/LIME, perturbation, or explainer metrics as such |
| TreeSHAP-minus-LIME mean differences are positive in 24/24 contexts | `paired_comparisons.csv`; group-level inference | Limited to the diagnostic 100-record samples, median/mode mask, and connection-group holdout |
| TreeSHAP top-versus-random passes 24/24; LIME 20/24 under the strict CI+Holm rule | `fidelity_control_tests.csv` | Not evidence of analyst benefit or causal attack features |
| No analyst, live, drift, or deployment study | Section VII | Future work only |

## Editorial checks completed in this revision

- Related-work comparison added as Section II and numbered through Section IX.
- Figure and table call-outs added for Figs. 1-2 and Tables I-X.
- Deletion endpoint defined as \(D_k\) then \(D(x,r)\).
- Recent manuscript generator reads `paper_metadata.yaml`, including `recent_title` and `anonymous_review`.
- Abstract and conclusion state that the contribution is the protocol, not a new explainer.

Author approval, venue-template conversion, similarity screening, and PDF eXpress remain outstanding.
