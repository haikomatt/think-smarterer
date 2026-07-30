# Template: structure note (Map of Content)

A hand-maintained entry point into a cluster of related permanent notes.
Location: `Permanent/00-<topic>.md` (the `00-` sorts it to the top).
**Only make one once the cluster has ~5+ notes worth navigating.** Grow bottom-up.

Model to copy: any project's `00-INDEX.md` (start-here, one line of
context per link, active vs superseded clearly marked).

```markdown
# 00: <Topic> (map of content)

<One or two sentences: what this cluster is about and the through-line.>

## Start here
- [[<the single best entry-point note>]]: <why>

## <Sub-theme>
- [[<note>]]: <one line of context>
- [[<note>]]: <one line of context>

## Open threads / notes to write
- [[<stub-not-yet-written>]]: <what it will say>
```

---

## Filled example

`Permanent/00-caching-strategies.md`

```markdown
# 00: Caching strategies (map of content)

How to keep a cache correct and fast under concurrent load. Through-line: a
cache's failure modes are almost always about *when* it's wrong, not whether
it's fast.

## Start here
- [[a-cache-miss-storm-needs-a-single-flight-guard]]: the root failure mode

## Invalidation
- [[a-retry-without-backoff-amplifies-load-during-an-outage]]: related load pattern
- [[write-through-caches-trade-latency-for-consistency]]: the core tradeoff

## Open threads
- [[debounce-cache-invalidation-under-bursty-writes]]: mitigation write-up to do
```
