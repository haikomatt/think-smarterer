# Template: permanent note

Filename: kebab-case of the claim. No dates, no version numbers.
Location: `Permanent/`.

If you're an agent promoting a fresh finding or hypothesis for the vault owner
to review, add `#digest` to `tags:`; it marks the note as created-but-not-yet-
understood and lights it up in the graph until the tag is stripped. See
SKILL.md "The digest frontier".

```markdown
---
tags: [<topic>, <topic>]

# Optional grade-binding invariant (see SKILL.md "Claim status"): grade_binding is
# authored once by hand at grading time; grade_binding_result/grade_binding_checked
# are written only by `vault-grade-record.py` when you record an experiment's outcome.
# grade_binding: "<invariant, one line>"
# grade_binding_result: pass          # pass | fail   (written by vault-grade-record.py)
# grade_binding_checked: <YYYY-MM-DD>                 (written by vault-grade-record.py)
---

# <The claim, as a full sentence you could agree or disagree with>

<2-5 sentences in your own words. State the idea, then the "so what".
Self-contained: a reader in five years with zero context should get it.
One idea only: if you write "and also...", split into a second note.>

**Related:** [[<another-permanent-note>]] . [[<another>]]
**Source:** [[<literature-note>]] (or: project note it was extracted from)
```

---

## Filled example

`Permanent/a-retry-without-backoff-amplifies-load-during-an-outage.md`

```markdown
---
tags: [reliability, distributed-systems]
---

# A retry without backoff amplifies load during an outage

When a downstream dependency starts failing, a client that retries
immediately (no delay, no backoff) multiplies the request rate right at the
moment the dependency is least able to absorb it, turning a transient blip
into a sustained outage. The fix is exponential backoff with jitter, plus a
cap on total retries, so retrying clients spread out rather than
synchronising on the same retry instant. Directly relevant to any service
client: a naive retry loop is a load amplifier, not a safety net.

**Related:** [[exponential-backoff-with-jitter-avoids-synchronised-retries]]
**Source:** [[some-source]]
```

Notice: title is a claim (not "retry storms"); one idea; own words; links out.
