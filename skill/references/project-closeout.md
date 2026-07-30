# Template: project close-out (closing or shelving)

Project end is exactly when "don't bury a reusable idea in a log" gets
violated: the log gets archived with the insight still trapped inside it.
Two paths, pick one. Neither deletes anything.

## Path A: Closing (actually finished)

1. **Final insight extraction**: reread the progress log end to end, promote
   anything reusable to `Permanent/`, link back.
2. **Post-mortem**: append to the progress log: what worked, what didn't,
   what to change next time.
3. Set `status: complete` on the project's docs; mark it in the `00-INDEX`.
4. Move the project folder to `_Archive/`: **keep every inbound link**, mark
   it `(archived)` wherever it's referenced.

## Path B: Shelving (stalled, not finished)

Stalled ≠ finished. Don't archive a merely-dormant project the same way as a
closed one: a status note first is what makes it resumable cold.

```markdown
---
title: "<project>: status note <YYYY-MM-DD>"
status: dormant
tags: [<project>, handoff]
created: <YYYY-MM-DD>
related: "[[00-INDEX]]"
---

## Why this stalled
<The honest reason: deprioritized, blocked, budget spent, interest moved on.>

## Current state
<What exists, what's committed, what's half-done. Assume zero memory.>

## What would restart it
<The concrete trigger or first action a future session would need.>
```

Set the project's `status: dormant` (not `complete`, not a stale `active`).
Leave the folder where it is: dormant projects aren't archived, only closed
ones are.

---

## Notes
- A project can move `dormant` → `active` again later; `complete` is terminal.
- If a status note already exists ad hoc (a handoff that says "banked" or
  "closed (banked)"), that counts: just make sure `status: dormant` is set
  and it's linked from `00-INDEX`.
