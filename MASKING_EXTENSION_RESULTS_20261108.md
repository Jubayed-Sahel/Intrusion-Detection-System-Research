# Replacement sensitivity results — 8 November 2026

The new paired analysis evaluates all 100 saved diagnostic records in each of the
eight seed-42 model contexts. The [protocol](MASKING_EXTENSION_PROTOCOL_20261108.md)
was written before execution. This is exploratory follow-up to already observed
primary results, not prospective preregistration or independent replication.
The original source files, classifiers, explanations and primary results are unchanged.

## Main finding

**The advantage measured for TreeSHAP depends strongly on the replacement scheme.**
All eight mean TreeSHAP-minus-LIME group differences remain positive with all
three schemes. With empirical joint donors the differences range from 0.0696 to
0.2030; with nearest donors selected using retained features they range from
0.0023 to 0.2013. The GeNIS differences shrink substantially under the nearest-donor
scheme. This supports a bounded ranking comparison under specified interventions,
not a universal statement that one explainer is more faithful or useful.

Original median/mode probability drops reproduce with maximum absolute difference
3.33 × 10^-16 across all eight contexts. The new analysis averages 32 donor
probabilities for each donor-based intervention, uses the same empirical donor
draws for paired explainers, and retains the original four masking budgets.

## Separate exploratory inference

The exact two-sided sign tests receive Holm correction over all 24 context/scheme
comparisons. Median/mode and empirical joint replacement each have 8/8 comparisons
with a significant positive direction frequency. Nearest-retained-feature donors
have **4/8**. No corrected test favors LIME. Each pointwise bootstrap interval
targets the **mean** connection difference; the sign test instead targets how
often a non-tied connection difference is positive. Their conclusions can differ.

For nearest-retained-feature donors:

- **GeNIS binary, RF:** mean 0.002319, pointwise 95% interval [-0.001808,
  0.007858]; 19 positive, 5 negative, **69 tied** groups; corrected sign p=0.0331.
- **GeNIS binary, XGBoost:** mean 0.004920, interval [-0.000783, 0.011691];
  58 positive, 21 negative, 14 tied; corrected sign p=0.000263.
- **GeNIS multiclass, RF:** mean 0.003441, interval [-0.004369, 0.011643];
  26 positive, 13 negative, **56 tied**; corrected sign p=0.1598.
- **GeNIS multiclass, XGBoost:** mean 0.010929, interval [0.002189, 0.022721];
  51 positive, 36 negative, 8 tied; corrected sign p=0.2658.
- **Gotham binary, RF:** mean 0.032684, interval [0.017312, 0.050312];
  38 positive, 19 negative, no ties; corrected sign p=0.0654.
- **Gotham binary, XGBoost:** mean 0.011341, interval [0.001344, 0.023184];
  30 positive, 27 negative, no ties; corrected sign p=0.7914.
- **Gotham multiclass, RF:** mean 0.196128, interval [0.160836, 0.235452];
  57 positive, 6 negative, no ties; corrected sign p=2.46 × 10^-10.
- **Gotham multiclass, XGBoost:** mean 0.201273, interval [0.159263, 0.241510];
  55 positive, 8 negative, no ties; corrected sign p=1.27 × 10^-8.

Only **5/8 nearest-donor mean intervals exclude zero**, while 4/8 sign tests
have significant positive direction frequency. Those are distinct summaries and
must not be combined into a claim of 8/8 statistically established advantages.
Ties exclude differences with absolute value at most 10^-12 from the sign test.
The small non-tied samples in GeNIS RF contexts matter for interpretation.

## Interpretation and limits

Empirical donors preserve observed combinations among removed predictors.
Nearest donors additionally match retained predictors under a training-scaled
distance. Such replacement may reveal redundancy that median/mode masking breaks,
but this experiment does not identify a uniquely correct removal mechanism.
Neither donor method guarantees that the combined retained/removed values describe
a physically valid network event. The nearest scheme is an approximate conditioning
sensitivity rather than a learned or validated conditional distribution.

This analysis uses one fitted seed, selected diagnostic records, a finite donor
pool and fixed donor counts. Bootstrap intervals are pointwise and condition on
these choices. They do not incorporate source campaign dependence, uncertainty
over donor-pool construction or independent dataset sampling. Results neither
replace the original directional Wilcoxon family nor establish causal importance,
analyst usefulness, temporal transfer or deployment readiness.

## Artifacts and checks

- [24 comparisons](outputs/masking_extension_20261108/paired_comparisons.csv)
- [Connection differences](outputs/masking_extension_20261108/group_differences.csv)
- [Complete manifest](outputs/masking_extension_20261108/manifest.json), with all
  input, code, protocol and output hashes; execution package versions; protocol
  snapshots; and per-context reference reproduction errors.
- Eight context CSVs retain per-record/budget/explainer drops, original predicted
  targets, removed features, exact training-row donor identities, donor probability
  dispersion, and nearest-donor retained-feature distance.

Reproduce with `.venv-reproduction/Scripts/python.exe run_masking_extension.py`.
Audit saved results with the same command plus `--verify`. Five focused unit tests
are in `tests/test_masking_extension.py`.
