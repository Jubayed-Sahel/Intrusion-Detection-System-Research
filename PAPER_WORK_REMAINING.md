# Remaining paper work

**Updated:** 14 October 2026

The GeNIS/Gotham 2025 experiments and local integrity checks are complete. The current manuscript is a six-page anonymous IEEE-style PDF. The items below cover the remaining writing, author review, formatting, and submission work.

## Already completed

- [x] Acquire official datasets and document source identity, checksums, conversion, sampling, exclusions, and group separation.
- [x] Complete 40 predictive model fits, 24 paired explanation comparisons, 48 control comparisons, and eight sensitivity-audit contexts.
- [x] Verify raw sources, prepared inputs, frozen code, metrics, statistical calculations, and all 17 unit tests.
- [x] Generate and visually inspect all six manuscript pages, including searchable text and embedded fonts.

Evidence: [current manuscript](output/pdf/xai_ids_recent2025_paper.pdf), [readiness report](PUBLICATION_READINESS_REPORT.md), [dataset provenance](RECENT_DATASET_PROVENANCE.md), and [experiment summary](outputs/recent2025/summary.json).

## 1. Finish the related work and contribution argument

**Can be completed by Codex, followed by supervisor review.**

- [ ] Review relevant quantitative XAI-for-IDS research and add a substantive related-work comparison. The current seven references cover dataset sources and foundational explainer methods; they do not establish the paper's position against existing IDS/XAI evaluation studies.
- [ ] Explain the contribution in relation to the closest prior work: traceable source preparation, matched explanation records, connection-group inference, corrected controls, and explicit limitations. Support any novelty statement with the literature review.
- [ ] Check every factual and comparative claim against its cited primary source. Create a reference-validation and claim-support record for this recent study; the existing historical bibliography checks are separate.
- [ ] Finish a full editorial pass for terminology, equations, metric definitions, figure/table references, abstract, and conclusions. Keep the claims consistent with the sampled testbed cohorts and measured masking protocol.

## 2. Choose the exact submission destination

**Needs the user or supervisor's decision; Codex can research and apply the requirements.**

- [ ] Select the specific IEEE journal or conference and article category. “IEEE” alone does not determine the submission format.
- [ ] Record the official template, page/word limits, anonymity rules, submission instructions, and any required supplementary files.
- [ ] Decide whether the current study scope is sufficient for that venue or whether a particular additional experiment is necessary.

## 3. Finalize author information and disclosures

**Needs factual information and approval from the authors.**

- [ ] Confirm the final title, author names and order, affiliations, corresponding author, email addresses, and ORCID identifiers where required.
- [ ] Confirm contributions, funding, acknowledgments, conflicts of interest, and any applicable ethics statements. Supply only verified information.
- [ ] Review and finalize the AI-assistance disclosure against the actual tool-use history and the chosen venue's rules.
- [ ] Make the recent manuscript generator read the approved metadata and apply the venue's anonymity rules. It currently hardcodes the title and anonymous author block; changing the older `paper_metadata.yaml` alone will not update the recent PDF.

## 4. Prepare the final manuscript and supplementary package

**Codex can complete this after the venue and metadata decisions.**

- [ ] Convert the manuscript into the venue's editable LaTeX or Word template and supply its source files. The current editable builder is Python/ReportLab; no venue-template `.tex` or `.docx` manuscript has been prepared.
- [ ] Prepare any required supplementary methods, full per-class results, statistical tables, configuration, environment record, and reproduction instructions.
- [ ] Include explicit class coverage, the `Unknown` exclusion, training-only CoAP Amplification, changed class priors, and the scope of Gotham member checksum verification.
- [ ] Rebuild after the final text/formatting changes, check all numerical claims against the verified artifacts, and inspect every rendered page again.

## 5. Complete scientific and submission checks

**Requires supervisor/coauthor review and access to any venue-required services.**

- [ ] Obtain supervisor/coauthor review of the methods, novelty, references, results, limitations, and approved contribution/disclosure statements.
- [ ] Resolve their comments and obtain all authors' approval of the final manuscript.
- [ ] Complete any required similarity screening and address attribution or overlap findings. No similarity-screening result is currently available.
- [ ] Complete the venue's PDF compliance checks, including PDF eXpress if applicable. Local rendering/font checks are already complete; venue certification remains outstanding.

## 6. Prepare the release and submit

**Codex can prepare the files; account access and author authorization are needed for publication actions.**

- [ ] Assemble a versioned release with the approved manuscript sources, code, configuration, verified results, provenance, and reproduction instructions. Confirm licensing and dataset attribution.
- [x] Publish the research update to the user's GitHub. The code, artifacts, manuscript, and checklist were uploaded on 14 October 2026 in [commit 6579189](https://github.com/Jubayed-Sahel/Intrusion-Detection-System-Research/commit/6579189a241cf8e7eeab8792f1b988bef08d5586).
- [x] Confirm hosted verification. The [research-integrity run](https://github.com/Jubayed-Sahel/Intrusion-Detection-System-Research/actions/runs/38556657111) passed on 14 October 2026, including all 17 unit tests and published research-artifact checks.
- [ ] Obtain an archival DOI if required or chosen for the release, and add the approved availability statement/link while respecting anonymity rules.
- [ ] Prepare the venue-required cover letter, submission metadata, supplementary uploads, and declarations. Confirm claims about prior publication or concurrent submission with the authors.
- [ ] Submit through the selected venue's portal after final author authorization. Complete copyright/licensing and camera-ready steps at the applicable stage.

## Additional experiments: conditional on the intended claims

These are possible extensions, rather than unfinished computations in the current protocol:

- [ ] Temporal, separate-capture, device, or cross-organization evaluation if claiming broader generalization.
- [ ] Human-analyst evaluation if claiming improved analyst decisions or usability.
- [ ] Live, drift, isolated latency, or throughput experiments if claiming operational deployment benefits.
- [ ] A second independent recent-study retraining if claiming independent reproduction. Use a fresh output directory; resuming completed checkpoints is not another retraining.

## Completion condition

The paper package is complete when the related-work and editorial review is finished, the approved authors and venue are specified, the venue-format source/PDF/supplement are ready, and all required author and submission checks are satisfied. Submission and acceptance are separate statuses and should be recorded only when they occur.
