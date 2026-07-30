# Template: hypothesis dossier

The operational record of one testable claim moving through `Hypotheses/`:
pre-registration, then experiment, then a graded verdict. Filename:
kebab-case of the claim, no dates (like permanent notes). Location:
`Hypotheses/`.

A hypothesis dossier is a source note for empirical evidence, the way a
literature note is a source note for reading: both feed permanent notes,
neither duplicates the other. Once the claim reaches its `target_grade`,
distil it into a lean permanent note (see SKILL.md "Hypotheses (the testing
pipeline)").

```markdown
---
status: hypothesis
grade: suggested
target_grade: <suggested | tested | robust | replicated | paper-grade>
type: hypothesis
tags: [<project>, hypothesis]
created: <YYYY-MM-DD>
related: "[[<origin>]]"
---

# <The falsifiable claim, as a sentence you could disagree with>

## Origin
<Link to the 00-open-questions entry, fleeting note, or result this arose
from, plus one sentence of context.>

## Pre-registration
<Write this BEFORE running anything - mandatory at creation, the
anti-HARKing lock.>
- **Test:** <the exact test to be run>
- **Threshold:** <the numeric decision threshold, fixed in advance>
- **Refutes if:** <the result that would refute the claim>
- **Target grade:** <target_grade, and why this claim needs that rung>

## Experiment
- [[<project-plan-or-run>]]: <one line of context>

## Evidence and grading
<Results, plus which rubric criteria for the current grade are met, each
linked. See [[empirical-robustness-standard]] for the criteria per rung.>

## Verdict
<Supported at grade X / refuted at grade X / still open.>
```

---

## Filled example

`Hypotheses/adding-a-redis-cache-reduces-p99-latency-below-100ms.md`

```markdown
---
status: hypothesis
grade: suggested
target_grade: tested
type: hypothesis
tags: [project-alpha, hypothesis]
created: 2026-07-30
related: "[[00-open-questions]]"
---

# Adding a Redis cache in front of the product-lookup service reduces p99 latency below 100ms

## Origin
Surfaced in [[00-open-questions]] under "where does a cache
actually pay for itself": the open piece was never run as a controlled
comparison against the current DB-only path.

## Pre-registration
- **Test:** run the product-lookup endpoint with and without the Redis
  cache in front of it, against the same replayed production traffic sample.
- **Threshold:** p99 latency with cache <= 100ms.
- **Refutes if:** p99 latency with cache stays above 100ms, or the cache
  hit rate is too low (<80%) for the comparison to be meaningful.
- **Target grade:** tested, since this gates a build decision (add the
  cache to the service), not a paper claim.

## Experiment
- [[product-lookup-cache-benchmark-runbook]]: the scoped run comparing both.

## Evidence and grading
Not yet run.

## Verdict
Still open.
```

Notice: the Pre-registration block is written before the experiment runs;
`target_grade` scales rigor to the decision the claim gates, not to how
important the claim feels.
