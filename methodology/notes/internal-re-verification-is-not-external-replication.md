---
tags: [evaluation, knowledge-management]
status: supported
---

# Internal re-verification is not external replication

Re-running your own test, on your own data, with your own pipeline, and
getting the same answer again confirms the result was not a fluke of that one
run, but it cannot rule out a systematic error baked into the pipeline itself
(a bug, a leaked label, a biased dataset), because that kind of error
reproduces itself identically every time the same pipeline runs. External
replication, an independent implementation, a different dataset, or a
different team checking the claim, is the only test that can catch that
class of error. A `replicated` or `paper-grade` grade requires at
least one independent check outside your own re-run loop; internal
re-verification alone caps a claim at `robust`.

**Related:** [Empirical Robustness Standard](../empirical-robustness-standard.md)
**Source:** standard experimental-design / statistics methodology
