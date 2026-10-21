# Current manuscript reference and claim audit

**Checked:** 21 October 2026. **Scope:** `src/xai_ids/recent_paper.py` and the rebuilt `output/pdf/xai_ids_recent2025_paper.pdf`. The historical CIC/UNSW manuscript is outside the full claim audit; its existing DOI records were refreshed separately.

The current bibliography has **20 entries**, all cited, numbered in first-appearance order. All **14 DOI references** resolve through Crossref or DataCite and their titles match after punctuation/case normalization, including publisher-supplied subtitles. The six remaining entries use official proceedings, journal, or archival records. Resolution establishes bibliographic identity, not universal scientific correctness or author approval.

## Corrections made

- Corrected the Gaspar comparison using the published full text, especially Sections IV and V: their detector consumes ADFA-LD-derived system-call sequences, and their perturbation experiments include randomly selected replacement calls. These are distinguished from our randomly permuted feature rankings. The manuscript no longer implies they have no randomized experiment.
- Clarified that Gaspar's survey concerns perceived interpretability; it does not establish operational alert cost, attack coverage, adversarial safety, or our project's analyst usefulness.
- Checked E-XAI's Section VI-A: descriptive-accuracy curves remove ranked predictors from training and evaluation and report classification accuracy. The current project instead measures prediction-probability changes in a fixed fitted model.
- Removed an unnecessary negative assertion about Mane and Rao lacking a particular evaluation protocol. Their documented methods and NSL-KDD application are sufficient for the comparison.
- Reconciled differences between catalogue names and printed originals. The final Yeh entry uses A. S. Suggala and P. Ravikumar as printed; the Covert entry includes I. C. Covert. Omitted an unconfirmed NeurIPS page range rather than relying on a secondary bibliography.
- Added official proceedings links for SHAP, Yeh, and Adebayo, and version/date details for the two arXiv citations.
- Added six directly relevant original sources: Random Forest, XGBoost, removal-based explanation, bootstrap, signed-rank testing, and Holm adjustment. Renumbered every in-text citation and bibliography entry together.

## Reference identities and support

1. **Silva et al., GeNIS author dataset, version 1.0.0 (2025).** DOI `10.5281/zenodo.14919237`; [official record](https://zenodo.org/records/14919237). Supports release identity and supplied traffic formats, not this project's measured model performance.
2. **Silva et al., GeNIS data article (2025).** DOI `10.1016/j.dib.2025.111487`; *Data in Brief* 60, article 111487. Authors/title/volume/article/date checked against publisher registration and the [original article](https://pmc.ncbi.nlm.nih.gov/articles/PMC11986601/).
3. **Belarbi et al., device-level Gotham author dataset, version v1 (2025).** DOI `10.5281/zenodo.14502760`; [official record](https://zenodo.org/records/14502760). Supports source identity and distributed 78-device capture design.
4. **Belarbi et al., Gotham Dataset 2025 preprint.** DOI `10.48550/arXiv.2502.03134`; [arXiv version 1](https://arxiv.org/abs/2502.03134v1), 5 February 2025. Local full text checked. Explicitly cited as a preprint, not a journal publication.
5. **Breiman, Random Forests (2001).** DOI `10.1023/A:1010933404324`; *Machine Learning* 45(1), 5-32. [Publisher record](https://link.springer.com/article/10.1023/A:1010933404324) and original author-hosted manuscript checked. Establishes the model's origin, not a guarantee of the project's accuracy.
6. **Chen and Guestrin, XGBoost (2016).** DOI `10.1145/2939672.2939785`; KDD, 785-794. Publisher title/subtitle and [author preprint](https://arxiv.org/abs/1603.02754) checked.
7. **Lundberg and Lee, SHAP (2017).** [Official NeurIPS proceedings](https://proceedings.neurips.cc/paper/2017/hash/8a20a8621978632d76c43dfd28b67767-Abstract.html), volume 30. Official BibTeX and full text checked. Supports additive feature attribution; does not establish real-world attack causality.
8. **Lundberg et al., tree explanations (2020).** DOI `10.1038/s42256-019-0138-9`; *Nature Machine Intelligence* 2, 56-67. Publisher registration checked; the 2019 component of the DOI does not change its 2020 publication year.
9. **Ribeiro, Singh, and Guestrin, LIME (2016).** DOI `10.1145/2939672.2939778`; KDD, 1135-1144. Publisher title/subtitle/author/page metadata checked. Supports local-surrogate methodology.
10. **Yeh et al., explanation infidelity and sensitivity (2019).** [Official NeurIPS proceedings](https://proceedings.neurips.cc/paper/2019/hash/a7471fdc77b3435276507cc8f2dc2569-Abstract.html), volume 32. Official BibTeX and full text checked. Its perturbation-defined metric differs from this study's deletion endpoint.
11. **Adebayo et al., Sanity Checks for Saliency Maps (2018).** [Official NeurIPS proceedings](https://proceedings.neurips.cc/paper/2018/hash/294a8ed24b1ad22ec2e7efea049b8737-Abstract.html), volume 31. Official BibTeX and full text checked. Supports caution about visual plausibility; the experiments are not this project's tree-based IDS validation.
12. **Neupane et al., X-IDS survey (2022).** DOI `10.1109/ACCESS.2022.3216617`; *IEEE Access* 10, 112392-112415. Registration and [author preprint](https://arxiv.org/abs/2207.06236) checked. Supports stakeholder-specific evaluation recommendations.
13. **Mane and Rao, explainable IDS framework (2021).** DOI `10.48550/arXiv.2103.07110`; [arXiv version 1](https://arxiv.org/abs/2103.07110v1), 12 March 2021. Full text checked for NSL-KDD and the stated explanation methods. Retained as a preprint citation.
14. **Gaspar, Silva, and Silva (2024).** DOI `10.1109/ACCESS.2024.3368377`; *IEEE Access* 12, 30164-30175. [Published article](https://ieeexplore.ieee.org/document/10440604/) downloaded from IEEE. Supports the corrected system-call, randomized-replacement, and perceived-interpretability statements.
15. **Warnecke et al. (2020).** DOI `10.1109/EuroSP48549.2020.00018`; EuroS&P, 158-174. [Author-hosted full text](https://www.mlsec.org/docs/2020-eurosp.pdf) and registration checked. Supports security explanation criteria and malware/vulnerability task scope. The similar DOI ending in `00021` belongs to a different paper and is not used.
16. **Arreche et al., E-XAI (2024).** DOI `10.1109/ACCESS.2024.3365140`; *IEEE Access* 12, 23954-23988. [Published article](https://ieeexplore.ieee.org/document/10433134/) downloaded from IEEE. Full text checked for the six metrics, three datasets, Wilcoxon analysis, and feature-removal experiment.
17. **Covert, Lundberg, and Lee (2021).** [Official JMLR article and BibTeX](https://jmlr.org/papers/v22/20-1316.html), 22(209), 1-90. Full text checked. Supports distinguishing removal mechanism, model behavior, and influence summary; it does not validate our specific masks.
18. **Efron (1979).** DOI `10.1214/aos/1176344552`; *Annals of Statistics* 7(1), 1-26. Original publisher DOI registration and the original article scan were checked. The second pass obtained the 27-page scan (archive cover plus 26 article pages) from the University of Washington statistics reading collection. Cited for bootstrap resampling generally, not as validation of this dataset's group-independence assumptions.
19. **Wilcoxon (1945).** *Biometrics Bulletin* 1(6), 80-83; [JSTOR 3001968](https://www.jstor.org/stable/3001968). Original article scan downloaded from the University of Granada research collection and inspected. Cited for the signed-rank procedure, not for the implementation's numerical-tie behavior.
20. **Holm (1979).** *Scandinavian Journal of Statistics* 6(2), 65-70; [JSTOR 4615733](https://www.jstor.org/stable/4615733). Original article scan inspected. Cited for sequential familywise adjustment. Uses a stable archival link rather than inventing a resolvable Crossref DOI.

## Evidence and repeatable checks

- `outputs/recent2025/reference_metadata.json`: freshly retrieved records for all 14 current-manuscript DOI entries.
- `outputs/recent2025/reference_audit.json`: all 20 bibliography entries, checked identities, source URLs, downloaded-file hashes, and verification scope.
- `data/reference_papers/`: 15 locally downloaded PDFs plus four official BibTeX files and an acquisition ledger. This ignored local-data folder is not redistributed on GitHub. The public audit record retains URLs/hashes so sources can be located independently.
- `python verify_references.py --offline`: checks complete citation coverage, contiguous labels, unique bibliography numbers, and first-citation order without network access.
- `python verify_references.py`: additionally refreshes DOI metadata and fails if any DOI cannot be resolved. DOI identity checking does not automatically validate scientific claims.
- Three reference tests cover the actual bibliography, invalid/missing/duplicate/out-of-order citations, and DOI extraction. All 26 project tests pass.
- The rebuilt seven-page PDF was rendered and every page visually inspected, including all 20 references. Existing research-artifact verification passes. The original experimental results were not changed.

## Limits and author review

External citations support the methods and comparisons identified above. The project's 40 fits, explanation scores, control tests, dataset exclusions, and group counts are supported by its own verified artifacts, not borrowed from those papers. This audit does not establish novelty, plagiarism clearance, publication acceptance, analyst benefit, or generalization. Author/supervisor approval, adaptation to a selected venue, similarity checks, and any required PDF certification remain outstanding.

## Independent second pass, 21 October 2026

Fresh complete publisher/registry responses were retrieved for all 14 DOI entries. Author surnames, available volume/issue/page fields, and the original first-page author lines were cross-checked. The six non-DOI citations retain their official proceedings/journal/archive identities. Small author-name and title-punctuation refinements were made; the Gotham preprint now lists all six authors.

The final PDF itself was checked separately from the editable source: all 20 printed entries match the source, all reference hyperlink targets match, every entry is cited, and first-use order is exactly 1 through 20. These assertions and the final PDF SHA-256 are saved under `second_pass` in `outputs/recent2025/reference_audit.json`. The original Efron article is now available locally, removing the earlier full-text availability limitation. No new DOI, volume, issue, page-range, or cited-claim contradiction was found in this pass.

## IEEE conference formatting, 21 October 2026

The manuscript now compiles with the official IEEEtran conference class. The seven-page US Letter PDF uses two columns and the template-defined 10-point body, headings, captions, and bibliography. All 20 printed references and their hyperlink targets were checked again after conversion; the PDF hash above was refreshed. Both figure axis titles fit, all pages were rendered for inspection, and compilation reports no overfull boxes. The editable project is `paper/ieee/main.tex`. This generic IEEE conference template does not certify compliance with a particular venue. All 26 tests pass.
