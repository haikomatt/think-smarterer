---
tags: [evaluation, knowledge-management]
status: supported
---

# Blind the evaluator to condition to remove expectancy

An evaluator, human or LLM judge, who knows which condition, arm, or
hypothesis a result belongs to will score in the direction they expect,
consciously or not, so any comparison that skips blinding is contaminated by
expectancy before a single number is computed. Blinding means the person or
judge scoring an output does not know whether it came from the treatment or
the baseline, the new method or the old one, until scoring is complete. This
is the same failure mode as position bias in pairwise LLM judging and as an
evaluator that sees more history than the outcome warrants: both are
instances of the scorer having information it should not have. A
`robust`-grade result needs a description of how the evaluator was blinded,
or an explicit note that blinding was not possible and why that limits the
claim.

**Related:** [Empirical Robustness Standard](../empirical-robustness-standard.md)
**Source:** standard experimental-design / statistics methodology
