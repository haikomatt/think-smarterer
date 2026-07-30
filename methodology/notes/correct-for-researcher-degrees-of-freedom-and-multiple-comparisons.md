---
tags: [evaluation, knowledge-management]
status: supported
---

# Correct for researcher degrees of freedom and multiple comparisons

Every unconstrained choice made after seeing the data (which metric to
report, which subgroup to slice, which threshold to use, which of several
tests to run) inflates the true false-positive rate above the nominal one,
even when each individual test looks properly powered on its own. Multiple
comparisons correction (Bonferroni, false discovery rate control, or simply
committing to one pre-registered primary metric) exists because running
enough tests will eventually turn up a "significant" result by chance alone,
with no real effect behind it. A `paper-grade` claim must state how
many comparisons were actually run, not just the one that is reported, and
how the reported significance accounts for that; otherwise it should be
caveated as exploratory rather than confirmatory.

**Related:** [Empirical Robustness Standard](../empirical-robustness-standard.md)
**Source:** standard experimental-design / statistics methodology
