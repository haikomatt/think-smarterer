# Template: project index (Map of Content for a project silo)

The hand-maintained entry point to one project's docs. Lives at the top of the
project folder as `00-INDEX.md`. Distinct from a `Permanent/00-*` structure note:
this maps *operational* project docs; that maps *permanent ideas*.

Model to copy: any project's `00-INDEX.md`.

```markdown
# 00: <Project> index (map of content)

**Maintained by hand: update when adding/retiring docs.** Last updated <date>.
Fresh session? Read [[session-handoff-<latest>]] first, then the active docs.

## Start here
- [[session-handoff-<latest>]]: **current state, phases & gates**
- [[progress-log]]: the full chronological record (large; newest at the bottom)
- **North star**: <the one-sentence thing this project is really about>

## Active
- [[<active-plan>]]: <one line of context>
- [[<active-doc>]]: <one line of context>

## Superseded (kept for provenance)
- [[<old-doc>]]: <why it was superseded / what replaced it>

## Past handoffs
- [[session-handoff-<older>]]
```

---

## Notes
- One line of context per link: the index earns its keep by telling you *why*
  you'd open each doc, not just that it exists.
- Mark superseded docs explicitly (don't delete them) so provenance survives.
- Flag suspected duplicates in-line for the user to resolve: never auto-delete.
- Keep "Start here" to the 2-3 docs a cold session actually needs first.
