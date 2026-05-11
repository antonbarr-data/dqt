# When NOT to use dqt

This is the most honest thing we can put in the documentation.

## Use a managed service instead if:

**You need SLAs and enterprise support.** Monte Carlo, Anomalo, and Bigeye offer managed services with on-call support, SLAs, and Salesforce/ServiceNow integrations dqt won't match for years. If your data team needs a vendor to call when things break at 3am, buy a managed product.

**Your team isn't comfortable with statistics.** The causal layer will mislead more than it helps if no one on the team can interpret a p-value, understand what "conditioning on a confounder" means, or distinguish correlation from causation. The `plain_english` output is a starting point, not a substitute for statistical literacy.

**You only need declarative checks.** Great Expectations and Soda have larger communities, more connectors, and more operators familiar with them. If all you need is "column X must be non-null and in set {A, B, C}", use one of those.

**You're on a team of 1 with no time for calibration.** dqt's default thresholds are statistically principled but not tuned to your data. You'll get false alarms until you run `suggest_threshold()` on your actual distributions. That calibration step takes a few hours and pays off, but it's not zero effort.

## dqt won't help you if:

**Your data isn't time-ordered.** Time-series detectors (STL, BOCPD, ADWIN, Matrix Profile) require temporal ordering. If your tables don't have a reliable timestamp column, skip those detectors entirely.

**Your warehouse isn't connected.** dqt needs to read samples from your warehouse. If your security model prohibits read-only service accounts with SELECT on `INFORMATION_SCHEMA`, the adapters won't work.

**You want to monitor ML model performance.** dqt monitors *data* quality. For model drift (accuracy drop, prediction distribution shift), you want Evidently, WhyLogs, or Arize.

**Your pipeline runs less than once per week.** Drift detectors and time-series methods need a reference window and a scoring window. Pipelines that run once a month don't produce enough signal for statistical methods — use threshold-based checks (`volume_change_ratio`, `null_fraction`) only.

## On the causal layer specifically:

The causal discovery layer (Granger, PCMCI+) is powerful when used correctly and dangerous when misused. Specifically:

- **All discovered edges are hypotheses, not facts.** The HITL review step exists for a reason. Never act on an unreviewed edge.
- **Granger causality ≠ causal causality.** Granger says "X's past predicts Y's future beyond Y's own past." It doesn't say X causes Y in any interventional sense. For interventional claims, use do-calculus with a confirmed DAG.
- **Confounders are reported, not controlled for.** The `confounder_candidates` field flags potential shared drivers but doesn't remove their effect. A "moderate" Granger edge with confounder candidates should be treated as "weak."
- **Short time series produce unreliable edges.** N < 50 for Granger, N < 100 for PCMCI+. Below these thresholds, edge detection is essentially random.

If you're not sure whether to trust a causal result, check the `evidence_strength` field and the `adjusted_p_value`. If `evidence_strength="weak"` or the `confounder_candidates` list is non-empty, defer human review before drawing conclusions.
