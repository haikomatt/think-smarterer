# Template: session handoff

End-of-session state so the next session (you or a fresh agent) can resume cold.
Lives in the project's folder. Filename: `session-handoff-<YYYY-MM-DD>-<topic>.md`.
Link it from the project's `00-INDEX`.

**Write it while you still know what comes next, not after you're spent.** A
handoff written three minutes before you stop is materially better than one
written at exhaustion: "I should wrap up soon" is the trigger, not "I have
nothing left to say."

```markdown
---
title: "<project>: session handoff <YYYY-MM-DD>"
status: active
tags: [<project>, handoff]
created: <YYYY-MM-DD>
related: "[[00-INDEX]]"
---

## Session handoff context (read first in a fresh session)
<The single most important paragraph: current state, the one metric/fact that
matters, where to start reading, and what is gated on what.>

## Progress
- <what got done this session, with commit hashes / file links>

## Errors / open issues
- <what's broken, flaky, or undecided, with enough detail to act>

## Next steps
1. <the ordered next actions>

## Details that will evaporate
- <flags, exact paths, magic numbers, half-formed hunches: the small
  concrete things you'd otherwise have to rediscover the hard way>
```

---

## Filled shape (abbreviated)

```markdown
---
title: "checkout-revamp: session handoff 2026-07-15 cart-merge bug"
status: active
tags: [checkout-revamp, handoff]
created: 2026-07-15
related: "[[00-INDEX]]"
---

## Session handoff context (read first in a fresh session)
p95 checkout latency = 340ms after the cache-key reframe. Start at
[[cart-merge-design]] Part 6. The rollout is gated on the load-test audit;
do not start the staged rollout until that audit confirms.

## Progress
- Cart-merge logic + cache-key scheme verified against the fixed schema (commit abc1234)

## Errors / open issues
- 4%-mismatch bug on guest-to-account cart merge still open: feeds the rollout write-up

## Next steps
1. Run the staged-rollout load-test audit
2. If clean, ship behind the existing feature flag

## Details that will evaporate
- Cache-key scheme lives in `services/cart/cache_keys.py`; the merge logic
  assumes the fixed schema, not the previous ad hoc one
```
