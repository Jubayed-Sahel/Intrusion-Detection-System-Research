"""Refresh the existing readiness report from measured research outputs."""
import json
from pathlib import Path

import pandas as pd


def main():
    root = Path("outputs/research_validation_corrected")
    summary = json.loads((root / "summary.json").read_text())
    pilot = pd.read_csv(root / "operational_pilot/timing_summary.csv")
    before = pd.read_csv(root / "operational_pilot/before_batching_observations.csv")
    after = pd.read_csv(root / "operational_pilot/observations.csv")
    matches = before.merge(after, on=["dataset", "task", "model", "source_test_index"], suffixes=("_before", "_after"))
    assert (matches.evidence_tier_before == matches.evidence_tier_after).all()
    matches.to_csv(root / "operational_pilot/before_after_comparison.csv", index=False)
    rf = matches[(matches.dataset == "CIC-IDS2017") & (matches.task == "binary") & (matches.model == "random_forest")]
    report = f'''# Publication Readiness Report

**Re-audit date:** 14 October 2026

**Status:** local correction, expanded evaluation, and independent environment reproduction completed. Submission remains conditional on dataset provenance, a specific IEEE venue, and author/supervisor review. This is an automated technical assessment, not peer review or acceptance.

## Completed research work

- Removed one CIC multiclass test feature vector that was also present in training despite a different label. The corrected test set has 24,902 rows. Re-ran both model families across all five primary seeds, the matched 40-flow explanation study, and feature ablations for this affected context.
- Regenerated the eight-context extended audits and manuscript figures. Historical primary CSVs and the manuscript remain in `outputs/before_cic_feature_overlap_correction/` locally.
- Checked feature overlap both before and after preprocessing. Hash-based screening finds zero train/test shared feature vectors in all four dataset/task partitions.
- Expanded explanations to 100 matched flows across model seeds 42, 52, and 62, with 24 model/seed contexts and no pooling of repeated flows as independent observations. Results and source snapshots are under `outputs/research_validation_corrected/`.
- Created a fresh Python 3.12 environment from the pinned requirements. All {summary['clean_predictive_contexts']} corrected seed-42 predictive contexts reproduce exactly, with maximum absolute metric difference {summary['clean_primary_seed_predictive_max_absolute_difference']:.1g}. The clean run also independently evaluated 100-flow SHAP/LIME explanations. Full package lists disclose differing transitive versions.
- Audited minority-class failures, class-dependent cleaning, and feature/label ambiguity. Validated all 16 bibliography identities through primary records or DOI registrations. Claim support and novelty still require author review.
- Repaired the paper generator's portable font handling, bibliography, limitations, and source/PDF consistency. Added expanded-validation and full-report timing findings to the six-page anonymous draft.
- Batched the alert's local masking controls, retaining 200 permutations and introducing conservative 1e-12 near-tie handling. A regression test compares batched scores against serial Random Forest predictions.
- Restored and extended the GitHub integrity workflow. Local tests and artifact checks have run; hosted GitHub CI has not run because the changes have not been uploaded.

## Expanded explanation evidence

TreeSHAP has positive mean paired fidelity differences in {summary['positive_mean_differences']}/{summary['model_seed_contexts']} contexts. In {summary['positive_ci_and_global_holm_significance']}/{summary['model_seed_contexts']}, the paired bootstrap interval is above zero and the one-sided Wilcoxon result passes Holm adjustment across all 24 comparisons. Mean differences range from {summary['mean_difference_range'][0]:.4f} to {summary['mean_difference_range'][1]:.4f} probability-drop units.

With Holm correction across all 48 top-versus-random tests, TreeSHAP passes {summary['random_control_passes_global_holm']['TreeSHAP']}/24 and LIME passes {summary['random_control_passes_global_holm']['LIME']}/24. The primary score averages deletion over k={{1,3,5,10}}; it is not a top-5-only test. These conclusions apply to the declared masking reference and selected flows, not causal or population-wide explanation validity.

## Operational pilot

The complete local report path was timed for three alerts in each of eight contexts, including model/input reads, preprocessing, prediction, SHAP, 200 local controls, benchmark-context reads, and JSON/Markdown serialization. Configuration medians range from {pilot['median'].min():.1f} to {pilot['median'].max():.1f} ms. OS caches were not flushed.

For the three matched CIC binary RF flows, median time was {rf.elapsed_ms_before.median()/1000:.2f} seconds before batching and {rf.elapsed_ms_after.median():.1f} ms after batching; evidence tiers agree for all matched before/after observations. This small pilot does not support tail percentile or sustained-throughput claims. Concurrent experiment latency is descriptive and should not be treated as an isolated service benchmark.

## Material limitations found

The original parquet mirror URLs, revisions, and transformation scripts are unavailable. Hash agreement proves file identity, not official-source equivalence. CIC has 28 selected features and no capture/session metadata; UNSW has 34 selected features. Cleaning refers to these representations and substantially changes class counts, including removing about 93.5% of Generic test rows from the mirror.

The cleaned UNSW representation aliases different attack labels for 302 test feature vectors involving 1,274 rows. These within-test cases remain in evaluation. They may represent lost discriminating information rather than incorrect labels. Full source history is needed to diagnose them.

UNSW minority performance remains weak: recorded five-seed RF DoS recall averages about 0.296, and Analysis F1 is about 0.073-0.076 across the model families. Worms has only 41 retained test rows. Improvements must use training-only validation; test-driven tuning would invalidate the held-out evaluation.

Flow bootstrap intervals may underestimate uncertainty from session/capture dependence. Three model seeds measure algorithmic variation on a fixed split. No temporal, cross-organization, human-analyst, drift, or live deployment study has been completed.

## Remaining external work

1. Recover the parquet acquisition/conversion record, or rebuild a separate official-source dataset pipeline and reevaluate. Do not backfill invented provenance.
2. Choose a specific IEEE journal or conference and use its exact template, page limit, anonymity, and disclosure requirements. The current ReportLab draft is IEEE-style, not venue-certified.
3. Have the supervisor and named authors review the experimental design, claims, references, novelty, dataset limitations, and AI-assisted contributions.
4. Restore GitHub authentication, create a reviewed versioned release, and obtain an archival DOI if appropriate. No updates have been uploaded in this work.
5. Complete any venue-required similarity and PDF compliance checks and authorship details. No such external checks or approvals are claimed here.
6. Conduct the prepared analyst study or live/drift evaluation only if the eventual paper claims those benefits. Protocols are prepared; participant or live-network evidence cannot be generated from the present files.

## Local deliverables

- Manuscript: `output/pdf/xai_ids_ieee_paper.pdf`
- Expanded validation, raw per-context evidence, source snapshots, statistical summaries, and scientific figure: `outputs/research_validation_corrected/`
- Independent environment results: `outputs/clean_reproduction/`
- Dataset and minority audits, bibliography metadata, and environment locks: `outputs/research_validation/` (its interrupted per-model directories are historical and excluded from release)
- Reproduction/provenance notes: `DATA_PROVENANCE.md`
- Follow-up study protocols: `RESEARCH_NEXT_STUDIES.md`
- IEEE requirements and draft disclosure: `IEEE_SUBMISSION_NOTES.md`
- Bibliography identity checks: `REFERENCE_VALIDATION.md`
'''
    Path("PUBLICATION_READINESS_REPORT.md").write_text(report, encoding="utf-8")
    print("Updated readiness report from completed evidence.")


if __name__ == "__main__":
    main()
