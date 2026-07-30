---
tags: [knowledge-management, methodology]
status: living
---

# Empirical Robustness Standard

A hypothesis moving through the vault's queue (`Hypotheses/`) is graded on a
five-rung ladder: suggested, tested, robust, replicated, paper-grade. The grade
is a measure of evidence strength, kept separate from `status:` (which tracks
whether the claim is currently believed true, contested, or refuted). Each
rung's criteria are stated below in plain prose so this document stands alone;
`[[backing-note]]` links after each section are a supplementary "seen in
practice" pointer, not the definition itself. Criteria tagged `[imported]` are
standard experimental-design or statistics methods that had no vault-native
note yet when this standard was written; each is now backed by one of six
gap notes written specifically to close that hole.

Grading a claim against this ladder is a human or CC judgement call, not a
mechanical check. Automated tooling (`vault-doctor --hypotheses`) can only
confirm that the *evidence a grade requires is present* (a baseline comparison
exists, an uncertainty figure is written down, a blinding note exists): it
cannot judge whether that evidence is actually any good. Treat a passing tool
check as "the paperwork is in order," never as "the science is sound."

## Pre-registration: the price of entry, not a rung

Before a hypothesis is tested at all, four things must be written down in
advance, while the outcome is still unknown: the falsifiable claim itself, the
exact test that will be run, a numeric decision threshold fixed before running
it, and the sample size (or a power justification) that test needs to be
informative. Missing any of these before the test runs means the eventual
result cannot be graded above `suggested`, no matter how clean it looks,
because there is no way to distinguish a genuine finding from a threshold or
sample size chosen after the fact to fit the result.

## The five rungs

### 1. Suggested
One motivating observation exists and the hypothesis is pre-registered, but no
controlled test has been run yet. This is the honest label for "I have a
hunch and a plan to test it," distinct from actually having evidence.

### 2. Tested
The hypothesis has been run against a matched baseline on the same data, not
measured in isolation, and the result crosses the threshold fixed during
pre-registration. An accuracy number with nothing to compare it against does
not qualify: the comparison against a baseline is what turns a measurement
into a test.

### 3. Robust
Plausible confounds have been enumerated and ruled out one at a time. The
metric itself has been checked for validity: does it fail loudly rather than
silently, is it directional rather than symmetric, is the rubric behind it
boolean and auditable rather than a vague scale. Where a human or an LLM judge
scored the result, that evaluator was blinded to which condition it was
scoring, so the score is not contaminated by expectancy. The effect is
reported as a size plus an uncertainty figure (a confidence interval or
equivalent), not as a bare point estimate that hides how much the number could
plausibly have varied by chance.

### 4. Replicated
The result holds across seeds, models, or datasets rather than being a
one-off run. Convergent evidence comes from at least two genuinely
independent approaches, not two runs of the same approach. Controls for
artifacts (signal that comes from the data-generating process rather than the
phenomenon under study) have passed, and the claim has been checked against
real data, not only synthetic data built to be easy. Re-running your own
pipeline and getting the same number again is necessary but not sufficient at
this rung: it confirms the result is consistent, not that it is correct, since
a systematic error baked into the pipeline reproduces itself identically every
time the same pipeline is rerun.

### 5. Paper-grade
The result has been checked by independent verification rather than resting
on the original author's self-report, and is anchored to ground truth rather
than to another model's judgement. Where human labels are involved, agreement
is reported with a prevalence-robust statistic (AC1 or PABAK) rather than
kappa alone, since kappa can understate agreement badly when almost all
labels fall in one category. The claim states the limits of where it is
expected to generalize rather than implying it holds everywhere, and it has
survived a genuine, active attempt to refute it, not just further attempts to
confirm it. Finally, the number of comparisons actually run (not just the one
being reported) is disclosed, so a reader can judge whether the result would
survive correction for researcher degrees of freedom and multiple
comparisons.

## What this standard is not

It is not a form every field of which must be filled in for every hunch. A
low-stakes hypothesis can target `tested` and stop there; a paper-track claim
targets `paper-grade`. The ladder exists so that a grade, once claimed, means
the same thing every time it is used, and so a reader can tell at a glance how
much weight a claim can bear.
