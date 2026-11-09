# Additional literature review: 7 November 2026

Twenty additional scholarly papers were reviewed beyond the previous 20-entry bibliography. Dataset records and abstract-only leads do not count toward these twenty. This is a focused narrative review of open primary texts, not a systematic review, an exhaustive search, or an independent reproduction of their experiments.

Reading covered the relevant methods, evaluation/results, and discussion. It does not imply line-by-line reading of every page. Eighteen PDFs were acquired locally with byte counts and SHA-256 hashes; one further PDF was read through the web reader and one publisher HTML full text was read. Their failed local PDF downloads are recorded rather than presented as acquisitions. Preprints and reviewed versions are identified below.

Machine-readable notes: [literature_review_20261107.json](literature_review_20261107.json). Acquisition ledger: [outputs/literature_review_20261107/acquisition.json](outputs/literature_review_20261107/acquisition.json). Downloaded PDFs remain in ignored local data storage and are not redistributed with this repository.

## Changes supported by the review

- Position the contribution as an auditable evaluation protocol. SHAP/LIME comparisons, quantitative fidelity checks, stability, timing, and feature selection already have close precedents.
- Keep the conclusion specific to TreeSHAP, fitted tree models, the diagnostic cohort, and the stated masking rule. Different tasks, SHAP variants, perturbation budgets, and scores can favor other methods.
- Separate fixed-model deletion from retraining after feature removal; separate repeatability from input robustness, feature agreement from faithfulness, and prediction explanation from causal attack relevance.
- Report leakage and dependence limits explicitly. A post-hoc exact-feature-pattern exclusion now removes 379 GeNIS and 1,914 Gotham test records matching training predictors, without changing the original split or refitting. Its seed-42 multiclass Gotham macro-F1 falls from 0.8748 to 0.8639 for Random Forest and from 0.8659 to 0.8562 for XGBoost. All 24 retained explanation contexts still have positive mean differences and Holm-significant two-sided sign tests, across 53–95 groups. This is a conditional sensitivity analysis, not external validation.
- Make class-specific failure visible: Gotham Mirai C&C recall is zero for both models across the five primary fitting seeds; CoAP Amplification has no held-out group. High aggregate accuracy does not establish complete attack coverage.
- Keep simple detector baselines and the masking, class-prior, and single-testbed limitations. A five-page anonymous conference candidate and the extended report serve different page constraints; neither is claimed to be accepted.

The original predictive fits and primary hypothesis families remain frozen. New sign/influence and pattern-exclusion analyses are labeled post-hoc and use separate exploratory correction families. See [SUPPLEMENTARY_INDEX.md](SUPPLEMENTARY_INDEX.md) for evidence and [BANGLADESH_SUBMISSION_PLAN.md](BANGLADESH_SUBMISSION_PLAN.md) for provisional venue fit.

## Twenty reviewed papers

### 1. Evaluating Explainable AI for Deep Learning-based Network Intrusion Detection System Alert Classification (2025)

**Authors/version:** R. Kalakoti, R. Vaarandi, H. Bahsi, S. Nomm. arXiv:2506.07882v1, preprint version reviewed. [Primary text](https://arxiv.org/pdf/2506.07882v1)

**Reading focus:** Sections 3.1, 3.4, 4; Table 2; conclusion.

**Finding:** Real SOC alert prioritization differs from traffic attack classification. DeepLIFT leads several metrics, while LIME's reported faithfulness exceeds SHAP's. Expert-feature alignment is a separate endpoint.

**Implication for this paper:** Compare the actual tasks and SHAP variants. Do not present our TreeSHAP deletion finding as universal superiority or human validation.

### 2. Evaluating The Explainability of State-of-the-Art Machine Learning-based IoT Network Intrusion Detection Systems (2024)

**Authors/version:** A. Kumar and V. L. L. Thing. arXiv:2408.14040v1, preprint version reviewed. [Primary text](https://arxiv.org/pdf/2408.14040v1)

**Reading focus:** Sections IV-VI; online NIDS case studies and disagreement discussion.

**Finding:** TRUSTEE and SHAP can disagree for online IoT detectors; explanation quality and inductive bias vary with architecture.

**Implication for this paper:** Distinguish local ranking from global surrogate fidelity. Add a direct discussion of testbed shortcuts and limits of cross-method agreement.

### 3. Explainable AI for Forensic Analysis: A Comparative Study of SHAP and LIME in Intrusion Detection Models (2025)

**Authors/version:** P. Hermosilla, S. Berrios, and H. Allende-Cid. Applied Sciences 15(13), 7329; doi:10.3390/app15137329. [Primary text](https://publica-rest.fraunhofer.de/server/api/core/bitstreams/9e8bfb7e-97a6-4b25-ab78-4d28d87b9904/content)

**Reading focus:** Sections 3.3-3.4, 4.4, 5; Tables 8-10; pp. 12-14 and 21-26.

**Finding:** UNSW-NB15 XGBoost/TabNet comparison includes fidelity, stability and feature-set Jaccard. KernelExplainer uses a 100-record training background; LIME uses 5000 perturbations. Validation and test detector accuracies differ materially.

**Implication for this paper:** Acknowledge this close comparison; distinguish KernelSHAP from TreeSHAP and avoid comparing incompatible numerical fidelity scores.

**Access record:** Full PDF accessed through the web reader; local download failed certificate validation and is not claimed as acquired.

### 4. A versatile XAI-based framework for efficient and explainable intrusion detection systems (2025)

**Authors/version:** B. Nugraha, A. V. Jnanashree, and T. Bauschert. Annals of Telecommunications 80, 1095-1120; doi:10.1007/s12243-025-01118-9. [Primary text](https://link.springer.com/article/10.1007/s12243-025-01118-9)

**Reading focus:** Sections 3, 4.1-4.2.5 and conclusion.

**Finding:** ANOVA/SHAP feature selection and retraining reduce explanation cost on DDoS/IoT/5G traces. SHAP-LIME consistency and timing are already studied. LIME timing uses 5000 perturbations.

**Implication for this paper:** Remove any implied novelty for dual explanations, feature reduction or timing. Qualify budget and hardware dependence; overlap is not explanation ground truth.

**Access record:** Publisher full HTML read; local PDF request timed out.

### 5. L-XAIDS: A LIME-based eXplainable AI framework for Intrusion Detection Systems (2025)

**Authors/version:** A. E. Muhammad, K.-C. Yow, N. Bacanin-Dzakula, and M. A. Khan. arXiv:2508.17244v1, preprint version reviewed; a Springer journal record also exists. [Primary text](https://arxiv.org/pdf/2508.17244v1)

**Reading focus:** Sections 1.1, 5, 6; decision-tree/MLP/XGBoost and ELI5 comparisons.

**Finding:** LIME/ELI5 local/global explanations and decision-tree visualizations are established IDS combinations. The reviewed text also discusses CSE-CIC-IDS2018 and LITNET-2020 beyond its main UNSW example.

**Implication for this paper:** Do not describe prior work as visualization-only without qualification, or claim that adding LIME makes this framework new.

### 6. Dos and Don'ts of Machine Learning in Computer Security (2022)

**Authors/version:** D. Arp et al.. 31st USENIX Security Symposium, pp. 3971-3988. [Primary text](https://www.usenix.org/system/files/sec22-arp.pdf)

**Reading focus:** Section 2 pitfalls, empirical impact analysis, Section 7.

**Finding:** Sampling, labels, data snooping, spurious correlations, inadequate baselines, base rates and lab-only evaluations can inflate security conclusions.

**Implication for this paper:** Add exact feature-pattern exclusion sensitivity, preserve simple baselines, explain class-cap prevalence distortion and refuse deployment claims.

### 7. TESSERACT: Eliminating Experimental Bias in Malware Classification across Space and Time (2019)

**Authors/version:** F. Pendlebury, F. Pierazzi, R. Jordaney, J. Kinder, and L. Cavallaro. 28th USENIX Security Symposium, pp. 729-746. [Primary text](https://www.usenix.org/system/files/sec19-pendlebury.pdf)

**Reading focus:** Temporal/spatial constraints C1-C3; Section 4.2; evaluation and supplementary dataset composition.

**Finding:** Time ordering and realistic test prevalence change malware evaluation. Random splits and future information can distort measured performance.

**Implication for this paper:** State that model seeds reuse one split and do not constitute temporal generalization. Do not transfer malware-specific effect sizes to network data.

### 8. Troubleshooting an Intrusion Detection Dataset: the CICIDS2017 Case Study (2021)

**Authors/version:** G. Engelen, V. Rimmer, and W. Joosen. IEEE Security and Privacy Workshops, pp. 7-12; doi:10.1109/SPW53761.2021.00009. [Primary text](https://intrusion-detection.distrinet-research.be/WTMC2021/Resources/wtmc2021_Engelen_Troubleshooting.pdf)

**Reading focus:** Flow/label reconstruction, Section IV-B Table II, Section V.

**Finding:** Fixing traffic construction, feature extraction and labels changes class-specific results despite similar aggregate accuracy.

**Implication for this paper:** Keep source-to-cohort records and unsupported-label reporting central; explicitly discuss zero Mirai C&C recall rather than only aggregate F1.

### 9. Fooling LIME and SHAP: Adversarial Attacks on Post hoc Explanation Methods (2020)

**Authors/version:** D. Slack, S. Hilgard, E. Jia, S. Singh, and H. Lakkaraju. AIES 2020; reviewed arXiv:1911.02508v2. [Primary text](https://arxiv.org/pdf/1911.02508)

**Reading focus:** Scaffolding construction, COMPAS/credit/crime experiments, discussion.

**Finding:** A classifier can treat synthetic perturbations differently from real inputs and conceal discriminatory behavior from perturbation-based explanations.

**Implication for this paper:** Describe synthetic masking as an explicit measurement intervention. Do not imply this attack was tested here or that every TreeSHAP implementation has the same vulnerability.

### 10. The Out-of-Distribution Problem in Explainability and Search Methods for Feature Importance Explanations (2021)

**Authors/version:** P. Hase, H. Xie, and M. Bansal. NeurIPS 2021; arXiv:2106.00786. [Primary text](https://arxiv.org/pdf/2106.00786)

**Reading focus:** Sections 4-6; replacement functions and counterfactual training.

**Finding:** Feature replacement and model behavior outside training support affect deletion-style scores; language-model experiments compare five replacement functions.

**Implication for this paper:** Make masking dependence a named construct-validity limitation. The current mask-reference audit is descriptive, not proof of on-manifold validity.

### 11. A Consistent and Efficient Evaluation Strategy for Attribution Methods (2022)

**Authors/version:** Y. Rong, T. Leemann, V. Borisov, G. Kasneci, and E. Kasneci. ICML 2022; arXiv:2202.00449. [Primary text](https://arxiv.org/pdf/2202.00449)

**Reading focus:** Section 5.2, Section 6.1 and consistency curves.

**Finding:** Fixed-value image masks can reveal information through removal patterns. ROAD uses noisy linear imputation to improve consistency between removal orders.

**Implication for this paper:** Discuss removal-mechanism confounding. Do not insert image-specific ROAD interpolation into mixed categorical network features without validating it.

### 12. OpenXAI: Towards a Transparent Evaluation of Post hoc Model Explanations (2022)

**Authors/version:** C. Agarwal et al.. NeurIPS 2022 Datasets and Benchmarks. [Primary text](https://papers.neurips.cc/paper_files/paper/2022/file/65398a0eba88c9b4a1c38ae405b125ef-Paper-Datasets_and_Benchmarks.pdf)

**Reading focus:** Sections 1-3; synthetic-data ground truth and metric families.

**Finding:** A benchmark can evaluate faithfulness, stability and fairness separately. Data-generating importance is not automatically the fitted model's importance.

**Implication for this paper:** Keep model-faithfulness findings distinct from causal attack relevance; do not claim fairness evaluation or explanation ground truth.

### 13. Quantus: An Explainable AI Toolkit for Responsible Evaluation of Neural Network Explanations and Beyond (2023)

**Authors/version:** A. Hedstrom et al.. JMLR 24(34), pp. 1-11. [Primary text](https://jmlr.org/papers/volume24/22-0142/22-0142.pdf)

**Reading focus:** Sections 2-3, Fig. 1 and evaluation-category appendix.

**Finding:** Evaluation has several distinct dimensions and depends on metric parameterization, including the feature-replacement baseline.

**Implication for this paper:** Separate deletion, repeatability, neighborhood similarity and latency instead of a single unvalidated quality score.

### 14. The Many Shapley Values for Model Explanation (2020)

**Authors/version:** M. Sundararajan and A. Najmi. ICML, PMLR 119, pp. 9269-9278. [Primary text](https://proceedings.mlr.press/v119/sundararajan20b/sundararajan20b.pdf)

**Reading focus:** Sections 3-4; baseline versus conditional-expectation operationalizations.

**Finding:** Different value functions and baselines yield different Shapley explanations; uniqueness for a specified game does not imply a universal explanation.

**Implication for this paper:** Avoid calling SHAP uniquely correct. State attribution output domains and use a common prediction-probability evaluation scale.

### 15. Explaining individual predictions when features are dependent: More accurate approximations to Shapley values (2021)

**Authors/version:** K. Aas, M. Jullum, and A. Loland. Artificial Intelligence 298, 103502; doi:10.1016/j.artint.2021.103502. [Primary text](https://martinjullum.com/publication/aas-2021-explaining/aas-2021-explaining.pdf)

**Reading focus:** Sections 4.2.1-4.2.6, 5; conditional versus independent sampling.

**Finding:** Ignoring dependence can produce unrealistic feature combinations and different attributions; conditional approximations help in the evaluated settings.

**Implication for this paper:** Explicitly acknowledge correlated predictors and baseline-dependent conclusions; do not claim a conditional SHAP implementation was run.

### 16. A Benchmark for Interpretability Methods in Deep Neural Networks (2019)

**Authors/version:** S. Hooker, D. Erhan, P.-J. Kindermans, and B. Kim. NeurIPS 2019. [Primary text](https://papers.neurips.cc/paper/9167-a-benchmark-for-interpretability-methods-in-deep-neural-networks.pdf)

**Reading focus:** ROAR definition, redundancy example, Section 4 and conclusion.

**Finding:** Retraining after removal addresses a different question from a fixed-model deletion test. Some image attribution estimators do not exceed random importance under ROAR.

**Implication for this paper:** Distinguish our primary fixed-model probability drop from training-feature ablation and prior retraining-based evaluation.

### 17. The Disagreement Problem in Explainable Machine Learning: A Practitioner's Perspective (2022)

**Authors/version:** S. Krishna, T. Han, A. Gu, J. Pombra, S. Jabbari, S. Wu, and H. Lakkaraju. arXiv:2202.01602v1, preprint version reviewed. [Primary text](https://arxiv.org/pdf/2202.01602v1)

**Reading focus:** Sections 3.2, 4.2-4.3; practitioner study.

**Finding:** Top-feature overlap, order and contribution signs capture different kinds of disagreement; practitioners' resolution heuristics are not explanation validation.

**Implication for this paper:** State that top-5 overlap cannot establish fidelity and do not equate absolute-magnitude deletion with signed explanation agreement.

### 18. On the Robustness of Interpretability Methods (2018)

**Authors/version:** D. Alvarez-Melis and T. S. Jaakkola. arXiv:1806.08049, workshop/preprint text reviewed. [Primary text](https://arxiv.org/pdf/1806.08049)

**Reading focus:** Local Lipschitz robustness definition, experiments and Section 4.

**Finding:** Small input changes can cause large explanation changes, even when model predictions barely change. Repeated random sampling is a different stability question.

**Implication for this paper:** Do not call repeated LIME runs or observational neighborhood cosine an adversarial-robustness test.

### 19. Stop Explaining Black Box Machine Learning Models for High Stakes Decisions and Use Interpretable Models Instead (2019)

**Authors/version:** C. Rudin. Nature Machine Intelligence 1, pp. 206-215; doi:10.1038/s42256-019-0048-x; author preprint reviewed. [Primary text](https://arxiv.org/pdf/1811.10154)

**Reading focus:** Section 2, structured-data examples and discussion.

**Finding:** Accuracy need not require an opaque model; a post-hoc surrogate may omit behavior that matters in high-stakes use.

**Implication for this paper:** Retain the depth-5 tree baseline and acknowledge the limited practical motivation for a complex detector when a simple one nearly matches it.

### 20. Anchors: High-Precision Model-Agnostic Explanations (2018)

**Authors/version:** M. T. Ribeiro, S. Singh, and C. Guestrin. AAAI 2018. [Primary text](https://homes.cs.washington.edu/~marcotcr/aaai18.pdf)

**Reading focus:** Precision/coverage formulation, user study, realistic perturbation distribution discussion.

**Finding:** Rule precision and coverage are explicit and distinct; human simulation performance requires a participant evaluation. Realistic perturbation distributions remain a challenge.

**Implication for this paper:** Do not add Anchors solely to increase explainer count. Keep explanation coverage, classification coverage and analyst usefulness distinct.

## Recent lead excluded from the count

[A Comparative Evaluation of Shap and Lime for Explainable Machine Learning-Based Intrusion Detection](https://ieeexplore.ieee.org/abstract/document/11754383); DOI 10.1109/NMITCON70171.2026.11754383. Very recent November 2026 IEEE indexing; abstract available, full text not obtained. Excluded from the 20 full-text reviews and from detailed methodological claims.

## Limits and next scientific priority

The review strengthens positioning and measurement interpretation; it does not validate the experiments reported in other papers or establish that our protocol is the first of its kind. Numerical scores from incompatible evaluation designs are not compared as a ranking.

The strongest remaining extension is a protocol frozen before fitting on an independently captured, temporal, or scenario/device-separated holdout where the source metadata supports it. Reusing the current split with more fitting seeds does not answer that question. Human usefulness and deployment readiness require dedicated participant and operational studies respectively. Those broader claims are excluded from the present paper.
