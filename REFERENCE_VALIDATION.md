# Reference validation, 14 October 2026

Eleven DOI-bearing references resolve against Crossref registration metadata. The raw identity, author, venue, and page/article records are saved in `outputs/research_validation/reference_metadata.json`. Registration checks establish bibliographic identity, not whether a citation supports a particular manuscript sentence.

The remaining five references were checked against primary records:

- [6] Lundberg and Lee, SHAP, NeurIPS 2017: https://proceedings.neurips.cc/paper_files/paper/2017/hash/8a20a8621978632d76c43dfd28b67767-Abstract.html
- [8] Mane and Rao, arXiv 2021: https://arxiv.org/abs/2103.07110
- [11] Pedregosa et al., JMLR 2011: https://www.jmlr.org/papers/v12/pedregosa11a.html
- [12] Yeh et al., NeurIPS 2019: https://proceedings.neurips.cc/paper_files/paper/2019/hash/a7471fdc77b3435276507cc8f2dc2569-Abstract.html
- [16] Adebayo et al., NeurIPS 2018: https://proceedings.neurips.cc/paper/2018/hash/294a8ed24b1ad22ec2e7efea049b8737-Abstract.html

Related-work positioning: Gaspar et al. already perform SHAP/LIME perturbation comparisons and a participant survey (https://doi.org/10.1109/ACCESS.2024.3368377). This project therefore must not claim SHAP/LIME use, perturbation validation, or analyst evaluation as new ideas. Its proposed contribution is the combined evaluation protocol and rejectable alert evidence. The present project has no participant study.

The distinction between model-path SHAP values and real conditional expectations is important. SHAP 0.47 uses tree-path-dependent attribution when no background is supplied; XGBoost raw output is a margin, whereas RF raw output is class probability. Only feature rankings and downstream probability changes are compared across explainers. See https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html .

Full claim-by-claim citation review by the authors and any venue-required similarity check remain pending. No automated bibliography check can certify novelty or plagiarism clearance.
