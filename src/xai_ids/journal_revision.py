"""Journal-only prose and citation refinements from the 23 November source audit.

Keep the historical extended report and frozen experimental sources intact.
These edits change reporting and attribution, not recorded experiment results.
"""


def revise_paragraph(content):
    if content.startswith("An explanation ranking can appear effective "):
        return (
            "This study examines two choices in evaluating explainable intrusion detectors: "
            "which values replace a removed feature, and which traffic sources are kept out of training. "
            "We use GeNIS [1], [2] and Gotham [3], [4], two author-published 2025 datasets with "
            "different traffic representations. We trace their preparation, compare explanations on "
            "matched records, and test whether detector results persist under source separation."
        )
    if content.startswith("We compare Random Forest (RF) "):
        return (
            "Random Forest (RF) [5] and XGBoost (XGB) [6] perform binary and multiclass detection. "
            "TreeSHAP and LIME rank predictors for the same selected test records within each fitted "
            "context. The evaluation concerns these rankings and the detectors' transfer failures; "
            "it does not measure analyst decisions."
        )
    if content.startswith("Neupane <i>et al.</i> survey "):
        return (
            "Prior IDS studies evaluate several aspects of explanations. Neupane <i>et al.</i> "
            "organize X-IDS methods around stakeholder needs and evaluation challenges [12]. "
            "Mane and Rao demonstrate SHAP and LIME explanations for a deep detector on NSL-KDD [13]. "
            "Gaspar <i>et al.</i> explain a multilayer perceptron trained on ADFA-LD-derived system-call "
            "sequences, perturb selected calls and survey perceived interpretability [14]. Their "
            "random replacement calls change input values; our random control changes the feature "
            "ranking while holding the replacement rule fixed. Warnecke <i>et al.</i> examine "
            "descriptive accuracy, completeness, efficiency and robustness in malware and vulnerability "
            "tasks [15]. Arreche <i>et al.</i>'s E-XAI evaluates six explanation metrics on NSL-KDD, "
            "CIC-IDS2017 and RoEduNet-SIMARGL2021 [16]. Its descriptive-accuracy curves remove ranked "
            "predictors from training and evaluation. Its Wilcoxon analysis compares detector accuracy "
            "scores, whereas our paired tests compare explanation-induced probability drops in "
            "already fitted models."
        )
    if content.startswith("This paper does not claim SHAP/LIME use, "):
        return (
            "Our evaluation keeps the fitted detector, explained record and masking budget matched "
            "between explainers. It then varies the replacement distribution and separates source "
            "files to examine which findings persist. Member hashes, connection-group exclusions "
            "and class-support records make those comparisons traceable. This combination supplies "
            "an empirical audit on GeNIS and Gotham, rather than a new explanation algorithm."
        )
    if content.startswith("Recent comparisons further narrow "):
        return (
            "Several recent comparisons are especially relevant. Kalakoti <i>et al.</i> explain "
            "LSTM-based prioritization of real SOC alerts and compare attributions with analyst-selected "
            "features [17]. Their SHAP implementation is DeepExplainer, and the target is alert priority. "
            "Kumar and Thing compare TRUSTEE and SHAP for online IoT detectors and test for inductive "
            "bias [18]. Hermosilla <i>et al.</i> evaluate SHAP/LIME fidelity, stability and feature "
            "agreement for XGBoost and TabNet on UNSW-NB15 [19]. Nugraha <i>et al.</i> combine "
            "statistical and SHAP feature selection with refitting and local explanations on DDoS, "
            "IoT and 5G traces [20]. These studies establish close precedents for quantitative IDS "
            "explanation comparisons. Differences in tasks, SHAP implementations, sampling budgets "
            "and endpoints prevent a direct numerical ranking against our deletion results."
        )
    if content.startswith("The refreshed evidence addresses "):
        return (
            "Source verification begins at the provider's exported files. The saved metadata, "
            "hashes and transformation code identify the inputs and preparation used here; they "
            "do not verify the underlying packet generation or supply independent replication. "
            "Gotham's per-member checks cover the consumed CSVs, while the complete archive's "
            "publisher checksum remains unverified. CRC32 detects transfer or extraction errors "
            "and does not establish cryptographic authenticity."
        )
    if content.startswith("The directional TreeSHAP-greater test permits "):
        return content.replace(
            "Bootstrap intervals are per context and are not simultaneous confidence intervals, "
            "whereas Holm controls the reported hypothesis families.",
            "The signed-rank tests and bootstrap mean intervals summarize different properties "
            "of the paired differences. Intervals are pointwise for each context; Holm adjustment "
            "applies to the specified hypothesis families, not to interval coverage."
        )
    return content


def revise_reference(reference):
    overrides = {
        17: r'\bibitem{ref17} R. Kalakoti, R. Vaarandi, H. Bahsi, and S. Nomm, '
            r'"Evaluating explainable AI for deep learning-based network intrusion detection system '
            r'alert classification," in \emph{Proc. 11th Int. Conf. Information Systems Security '
            r'and Privacy (ICISSP)}, vol. 1, 2025, pp. 47--58, doi: '
            r'\href{https://doi.org/10.5220/0013180700003899}{10.5220/0013180700003899}. '
            r'[Online]. Accepted version: \href{https://arxiv.org/abs/2506.07882v1}{arXiv:2506.07882v1}.',
        29: r'\bibitem{ref29} C. Agarwal \emph{et al.}, "OpenXAI: Towards a transparent evaluation '
            r'of model explanations," in \emph{Advances in Neural Information Processing Systems}, '
            r'vol. 35, 2022. [Online]. Available: '
            r'\href{https://papers.neurips.cc/paper_files/paper/2022/hash/65398a0eba88c9b4a1c38ae405b125ef-Abstract-Datasets_and_Benchmarks.html}{NeurIPS proceedings}.',
    }
    for number, replacement in overrides.items():
        if reference.startswith(r'\bibitem{ref' + str(number) + '}'):
            return replacement
    if reference.startswith(r'\bibitem{ref26}'):
        return reference.replace('https://arxiv.org/abs/2106.00786',
            'https://proceedings.neurips.cc/paper_files/paper/2021/hash/1def1713ebf17722cbe300cfc1c88558-Abstract.html').replace('Author preprint', 'NeurIPS proceedings')
    if reference.startswith(r'\bibitem{ref31}'):
        return reference.replace('https://arxiv.org/abs/1806.10758',
            'https://proceedings.neurips.cc/paper_files/paper/2019/hash/fe4b8556000d0f0cae99daa5c5c5a410-Abstract.html').replace('Author preprint', 'NeurIPS proceedings')
    if reference.startswith(r'\bibitem{ref27}'):
        return reference.replace('A. Loland', r'A. L{\o}land')
    if reference.startswith(r'\bibitem{ref37}'):
        return reference.replace('Zenodo, 2025,', 'IEEE DataPort, 2025,') + (
            r' [Online]. Mirror: \href{https://zenodo.org/records/14887131}{Zenodo record 14887131}.')
    for doi in ('10.1145/357830.357849', '10.5281/zenodo.16943481'):
        if 'doi: ' + doi in reference:
            reference = reference.replace('doi: ' + doi, r'doi: \href{https://doi.org/' + doi + '}{' + doi + '}')
    return reference
