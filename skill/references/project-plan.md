# Template: project plan

A scoped piece of work with a definition of done. Lives in the project's folder.
Filename: `<short-description>-plan.md` or `<SUBTASK-KEY>-<short-description>.md`.

```markdown
---
title: "<project>: <phase / thing being planned>"
status: draft            # draft -> ready to execute -> active -> complete
tags: [<project>, plan]
created: <YYYY-MM-DD>
parent_plan: "[[<parent-plan>]]"    # optional
depends_on: "[[<prerequisite>]]"    # optional
---

## Goal
<One paragraph: what "done" achieves and why it's worth doing now.>

## Context
<What a fresh reader needs: current state, prior decisions, links to the index.
Name the prior notes the kickoff search (see SKILL.md "Starting a project")
turned up, or state plainly that the search was run and found nothing.>

## Build order
1. <ordered, independently-checkable steps>
2. ...

## Files to Touch
- `path/to/file`: <what changes>

## Exit criteria
- [ ] <observable, testable condition>
- [ ] <...>

## Risks
- <risk>: <mitigation>

## CC Prompt (handoff)
> <ready-to-paste brief for the Claude Code session that will execute this:
> what to read first, the task, the constraints, and the definition of done.>
```

---

## Notes
- Keep **status** current: it's how other sessions (and you) know whether to act.
- When this plan replaces an earlier one, add `supersedes: "[[old-plan]]"` and
  mark the old plan in the project's `00-INDEX`.
- The `## CC Prompt (handoff)` block is the house convention for handing a plan to
  an execution session: always include it on an executable plan.
- If a step surfaces a *reusable* insight (true beyond this project), extract it to
  `Permanent/` and `[[link]]` it here: don't let it live only inside the plan.
