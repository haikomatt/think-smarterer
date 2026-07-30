# Convention: progress log

One per project (`Projects/<x>/progress-log.md`). The **chronological record** of
what happened: not a plan, not a place to reason. Rules:

- **Append-only, newest entries at the bottom.** Never restructure old entries.
- **Every entry is dated** and self-contained (a reader shouldn't need the
  session that wrote it).
- **It grows large. That's fine.** Don't try to keep it short; keep it *ordered*.
- **Extract, don't accumulate insight here.** When an entry contains a durable,
  reusable insight, write it once as a permanent note and `[[link]]` to it: the
  log records *what happened*, the slipbox keeps *what it means*.
- Link the log from the project's `00-INDEX` as "the full chronological record".

```markdown
---
title: "<project>: progress log"
status: living
tags: [<project>, progress-log]
created: <YYYY-MM-DD>
---

## <YYYY-MM-DD>: <short session label>
- <what happened, decisions, commits, numbers>
- Insight extracted → [[<permanent-note-claim>]]

## <YYYY-MM-DD>: <next session label>
- <...>          <!-- newest entries go at the BOTTOM -->
```
