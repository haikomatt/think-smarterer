# Template: fleeting capture

The point is speed. Don't format, don't organise, don't title it well. Just get
the thought into `00-Inbox/` before it's gone. It will be processed (promoted,
folded, or binned) and the inbox emptied: nothing here is meant to last.

**Worth capturing?** Is it *surprising*, *useful*, *personal*, or *inspiring*?
Shannon's test is the sharpest: information is what surprises you; if you
weren't surprised, you already knew it. Ceiling of ~10% of any one source; a
capture pile that grows faster than that is noise, not signal.

Filename: whatever's fastest (`<yyyy-mm-dd>-<few-words>.md` is plenty).

```markdown
<the raw thought: a sentence or three, or a pasted quote + where it's from>

<optional: why it caught you / what it might connect to>
```

---

## Filled example

`00-Inbox/2026-07-22-cache-stampede-idea.md`

```markdown
Noticed the cache layer refetches from the DB on every concurrent miss for the
same key instead of letting one request populate it. Cache stampede? Check
whether the read-through cache has a single-flight guard.
```

When processed: this becomes the permanent note
`a-cache-miss-storm-needs-a-single-flight-guard`, linked into
`00-caching-strategies`, and this fleeting note is deleted.
