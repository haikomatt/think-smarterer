---
name: smart-notes
version: 2.3.0
description: >
  The operating manual and structure spec for an Obsidian vault, the
  single source of truth for how notes are written, so a session never has to
  rescan the vault to match its conventions. Covers BOTH layers: operational notes
  (plans, session-handoffs, progress logs, project indexes, outlines) and thinking
  notes (fleeting, literature, permanent, structure/MOC); the frontmatter + status
  schema; concurrency-safe writing (compare-and-swap via vault-write); and
  vault-doctor health checks. Invoke when writing ANY note to the vault: planning
  work, handing off a session, logging progress, capturing or promoting an idea,
  or auditing health.
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Grep
  - Glob
  - AskUserQuestion
triggers:
  - smart notes
  - add this to my vault
  - write a plan
  - session handoff
  - process my inbox
  - make a permanent note
  - promote this to a note
  - tidy my vault
  - vault health
  - vault doctor
  - add this as a hypothesis
  - queue this for testing
  - distill this hypothesis
---

<!-- Source of truth: this repo's skill/ dir. -->
<!-- Install this dir (or symlink it) into ~/.claude/skills/smart-notes/ so edits -->
<!-- are live immediately. No deploy step; never cp onto a symlink target (that -->
<!-- writes back through the link). git revert in the vault rolls back the live -->
<!-- skill too, if you keep the skill dir inside the vault repo. -->
<!-- Vault root: your Obsidian vault -->

# /smart-notes: vault operating manual

This skill **is the structure spec for the vault**. Classify what you're writing
with the routing table, then write from the matching template. **Do not re-scan
the vault to reverse-engineer its conventions each session**: they're all here.

The vault has two layers:

- **Operational** (most of the vault): plans, session-handoffs, progress logs,
  project indexes, outlines. Living work, folder-organised per project, archived
  when the project ends.
- **Thinking** (the slipbox): fleeting → literature → permanent → structure. Ideas
  that outlive any single project.

## Routing table: what am I writing?

| If the content is… | Type | Folder | Template |
|---|---|---|---|
| scoped work with steps / a definition of done | **project-plan** | the project's folder | `references/project-plan.md` |
| end-of-session state for the next session | **session-handoff** | the project's folder | `references/session-handoff.md` |
| the running chronological record of a project | **progress-log** | the project's folder | `references/progress-log.md` |
| a hand-maintained map of a project's docs | **project-index** (MOC) | project folder, `00-INDEX.md` | `references/project-index.md` |
| a paper/article draft with numbered sections | **outline** | the project's folder | freeform; keep the `§1…§5` shape |
| a raw thought, quote, or capture | **fleeting** | `00-Inbox/` | `references/fleeting-capture.md` |
| your distillation of a source | **literature** | `Literature/` | `references/literature-note.md` |
| one reusable idea, in your own words | **permanent** | `Permanent/` | `references/permanent-note.md` |
| a map of a permanent-note cluster | **structure/MOC** | `Permanent/00-*.md` | `references/structure-note.md` |
| a testable claim you will run an experiment on | **hypothesis** (dossier) | `Hypotheses/` | `references/hypothesis-dossier.md` |

**Outline guidance:** an outline's first pass is `[[links]]` to existing notes
grouped under headings, before any prose is written: an archipelago of
stepping stones you write between, not a blank page.

Two rules keep the layers healthy:
- **Don't atomize operational notes.** A plan / log / handoff stays whole.
- **Don't bury ideas in logs.** When an operational note throws off a *reusable*
  insight, extract it once to `Permanent/` and `[[link]]` back. This is the one
  behaviour that makes insight compound.

## Frontmatter & status schema (canonical, use these, don't invent)

Operational notes carry:

```yaml
---
title: "<human title>"
status: <draft | ready to execute | active | complete | dormant | living>
tags: [<project>, <kind>]
type: <permanent | literature | plan | handoff | progress-log | project-index | hypothesis | fleeting | structure>   # OKF-compatible; new notes carry it
created: <YYYY-MM-DD>
parent_plan: "[[<parent-plan>]]"    # optional: stacked plans / subtasks
depends_on: "[[<prerequisite>]]"    # optional
supersedes: "[[<old-version>]]"     # optional: when replacing a prior doc
---
```

`type:` aligns the vault with OKF v0.1 (the only field OKF requires); new
notes carry it, existing notes are not retrofitted. Hypothesis dossiers
additionally carry `grade:` and `target_grade:` (see "Hypotheses" below).

Hypothesis dossiers and graded permanent notes carry `status:` from a
**separate epistemic enum**, `hypothesis | supported | contested | refuted |
mixed | superseded` (see "Claim status" below), not the operational lifecycle
enum above. `mixed` is a resolved dossier that split into a supported part and
a refuted part (different sub-claims, different resolutions); this is
distinct from `contested`, which is one claim with ambiguous evidence.

Status lifecycle: `draft` → `ready to execute` → `active` → `complete`.
`complete` is terminal; `living` is an evergreen doc that never reaches one.
`dormant` is the honest state for a project that is banked but unfinished:
shelved, not shipped. It sits alongside `active` and can return to it at any
time, and it requires a status note (see "Closing or shelving a project"
below). Keep the status line honest and current: a stale status is the single
biggest thing that makes a vault hard to trust. When a doc replaces another,
set `supersedes:` and mark the old one in the project index rather than
deleting it.

## Starting a project: search before you write

Enforce search-before-write for the vault the same way you would for code
("Extend Before Create"): a promoted permanent note that quietly duplicates
one written months ago is a live failure mode. Before writing a new project
plan:

1. **Dump current thinking first**: a messy brainstorm note in the project
   folder: what I know, what I need to find out, the goal, who to ask, what to
   read. Don't polish it; it's a stepping stone, not a deliverable.
2. **Browse for prior work**: `Permanent/`, sibling `Projects/*`, `_Archive/`.
   A relevant idea is as likely to sit in another project's silo as your own.
3. **Grep the whole vault** for related terms: valuable notes turn up in
   unexpected folders; folder-browsing alone misses them.
4. **Link what you find into the plan's `## Context` section.** A plan that
   cites zero prior notes out of a 100+-note slipbox is a signal the search
   was skipped, not that nothing existed.

Then write the plan itself per `references/project-plan.md`.

## Closing or shelving a project

The skill handles `supersedes:` and `_Archive/` but never says what "done"
means. Project end is exactly when "don't bury a reusable idea in a log" gets
violated: the log gets archived with the insight still trapped inside it.

**Closing (the project is actually finished):**
1. **Final insight extraction**: reread the progress log, promote anything
   reusable to `Permanent/`, link back.
2. **Post-mortem into the progress log**: what worked, what didn't, what to
   change next time.
3. Set `status: complete`, mark it in the project's `00-INDEX`.
4. Move to `_Archive/`: **keep every inbound link**, mark it `(archived)`.

**Shelving (stalled, not finished):** write a status note (current state, why
it stalled, what would restart it) and set `status: dormant`, not `complete`
or a stale `active`. **Leave the folder where it is.** Only closed projects go
to `_Archive/`; keeping `_Archive/` to mean "settled" is what makes it worth
having. This is already done ad hoc when a project is banked rather than
shipped; the status value makes it a rule, not a habit.

Template for both: `references/project-closeout.md`.

## Operational notes

### project-plan
Sections, use what applies: **Goal · Context · Build order / Steps · Files to
Touch · Exit criteria / Acceptance · Risks · Estimated timeline · Scope
boundaries**, and end with a **`## CC Prompt (handoff)`** block: the ready-to-
paste brief for the Claude Code session that will execute it. Template:
`references/project-plan.md`.

### session-handoff
Filename `session-handoff-<YYYY-MM-DD>-<topic>.md`. Lead with **`## Session
handoff context (read first in a fresh session)`** (current state, where to
start, what's gated), then **Progress**, **Errors / open issues**, **Next steps**,
**Details that will evaporate** (flags, paths, magic numbers, half-formed
hunches, distinct from status/next-steps, and the thing that actually costs a
fresh session the most time to rediscover). Link it from the project's
`00-INDEX`. Template: `references/session-handoff.md`.

Write it while you still know what comes next, not after you're spent: a
handoff written three minutes before you stop is materially better than one
written at exhaustion. Treat "I should wrap up" as the trigger to write it,
not "I've run out of things to say."

### progress-log
One per project, append-only, **newest entries at the bottom**, each dated. It is
the chronological record, not a plan: don't restructure it; pull durable
insights out to `Permanent/` rather than letting them rot in the log. Template:
`references/progress-log.md`.

### project-index (MOC)
The hand-maintained entry point to a project's docs, `Projects/<x>/00-INDEX.md`.
Model: any project's `00-INDEX.md`. Sections: **Start here · Active ·
Superseded (kept for provenance) · Past handoffs**, one line of context per link,
superseded docs clearly marked. Template: `references/project-index.md`.

## Thinking notes (the slipbox)

- **Fleeting** → `00-Inbox/`, fast capture, processed then deleted.
  Template: `references/fleeting-capture.md`.
- **Literature** → `Literature/`, one per source, your distillation, ends with a
  `Feeds:` list linking the permanent notes it produces.
  Template: `references/literature-note.md`.
- **Structure / MOC** → `Permanent/00-*.md`, grows bottom-up once a cluster has
  ~5+ notes. Template: `references/structure-note.md`.

### Permanent-note rules (the heart)
- **One idea.** If it joins two ideas with "and" / "also", split it.
- **Title is a claim** you could agree or disagree with:
  `llm-judges-favour-the-first-response-shown`, not `judge-biases`.
- **Own words, self-contained**: understandable in five years with zero context.
- **Connect before "done":** link to >=1 existing note.
- **Short** (< ~300 words) and **no dates/version numbers in the filename**.

Template: `references/permanent-note.md`.

## Claim status: is the note actually supported?

A permanent note is a claim, not a fact. Give each an epistemic `status:` in
frontmatter so an untested idea isn't mistaken for a proven one:

- `hypothesis`: asserted from reasoning/experience; not tested (the honest default)
- `supported`: a linked experiment/result or established literature backs it
- `contested`: evidence is mixed (one claim, ambiguous evidence)
- `mixed`: resolved into both a supported part and a refuted part (different
  sub-claims, different resolutions, not the same as `contested`)
- `refuted`: evidence contradicts it (keep the note, flag it)
- `superseded`: replaced by a better claim (link the replacement)

- Add an **`## Evidence`** section linking the experiment(s)/result(s) that support or
  refute it, with the verdict (`- supports: [[experiment-results]]`).
- For anything **not `supported`**, put a callout at the top so validity shows on open:
  `> [!note] Status: hypothesis, ...` / `> [!warning] Status: contested` / `> [!danger] Status: refuted by [[...]]`.
- **Check staleness:** `"$BIN"/vault-doctor.py --vault . --claims` lists notes by status and flags
  untested claims, refuted/superseded to revisit, notes whose Source doc is *newer*
  than the note (new evidence may have landed; review and update the status), and any
  declared `grade_binding` invariant that's broken, overdue past `--claims-stale-days`
  (default 30), or never verified.

A companion `grade:` field records evidence strength on the ladder
`suggested → tested → robust → replicated → paper-grade`, kept separate from
`status:` (which tracks direction: open, supported, refuted). `grade` lives
on both the hypothesis dossier and the permanent note it distils into; full
criteria per rung are in [[empirical-robustness-standard]].

Optionally, a permanent note's grade can be bound to an external invariant:
`grade_binding` is a one-line, human-authored description written once, at
grading time, of the invariant the grade depends on. An optional
`grade_binding_id` (a stable machine-readable slug) lets the external writer
find which notes it owns by id rather than by matching the prose, which is
free to be reworded; a note that declares `grade_binding` but no
`grade_binding_id` is never auto-written to and simply stays `unverified`.
`grade_binding_result` (`pass`/`fail`) and `grade_binding_checked`
(`YYYY-MM-DD`) are written back by whatever external system owns the check
(for example a CI job), never by hand and never by vault-doctor. vault-doctor
only ever *reads* these fields back: it never executes anything from
frontmatter, deliberately, since the vault is multi-writer and an executable
field would be an arbitrary-code-execution sink. A note with no
`grade_binding` is unaffected.

## Hypotheses (the testing pipeline)

A testable claim moves open-questions → hypothesis dossier → verified
permanent note. The dossier lives in `Hypotheses/<claim-slug>.md`
(`references/hypothesis-dossier.md`); its `## Pre-registration` block (the
exact test, the threshold, what would refute it) is mandatory at creation,
the anti-HARKing lock, written before the result is known. `target_grade`
scales rigor to consequence: a decision-grade hunch may target `tested`, a
paper-track claim targets `paper-grade`. Ladder: `suggested → tested →
robust → replicated → paper-grade`, full criteria in
[[empirical-robustness-standard]].

- **"add this as a hypothesis" / "queue this for testing"** → create the
  dossier (force the pre-registration block), add an entry under the right
  project header in `Hypotheses/00-INDEX.md`, link the origin note.
- **"distill this hypothesis"** → graduate it. Supported at `target_grade`:
  write/update a lean permanent note (`status: supported`, `grade:` set,
  `## Evidence` linking the dossier), move the index entry to `## Graduated`.
  Refuted: record the verdict in the dossier, optionally write a permanent
  note of the refutation, archive the dossier to `_Archive/` (never delete),
  mark the index entry `(refuted)`. **Mixed** (a claim that split into a
  supported part and a refuted part): distil the supported part to its
  permanent note exactly as above, AND record the refuted part in the
  dossier's `## Verdict` (optionally its own refutation permanent note); move
  the index entry to `## Resolved`, annotated with both outcomes.
- **Check integrity:** `"$BIN"/vault-doctor.py --vault . --hypotheses` flags stale
  dossiers (queued too long, no experiment linked or grade still `suggested`) and
  grade-integrity leaks (a claimed grade whose evidence markers aren't present).
  It also prints a **`## Resolved (by grade)`** view: every dossier that has
  already resolved (`supported` / `refuted` / `mixed` / `contested` /
  `superseded`), grouped by grade, so resolved claims stay visible without
  cluttering the open queue.

## Writing safely under concurrency

Other Claude sessions and Obsidian write this vault at the same time. To avoid
silently clobbering a concurrent change, **write notes with compare-and-swap**,
never blind overwrite:

```bash
BIN=~/vault/Harness/Skills/smart-notes/bin
# 1. read the current hash (empty string if the file is new)
sha=$("$BIN"/vault-write.py --print-sha PATH)
# 2. ...read PATH, produce the edited content into $new...
# 3. write only if it hasn't changed underneath you
printf '%s' "$new" | "$BIN"/vault-write.py PATH --expect-sha "$sha"
#    new file instead:  ... | "$BIN"/vault-write.py PATH --expect-absent
```

Exit **3 = CONFLICT** (someone edited it first) → re-read and retry. Writes are
atomic (temp-file + rename), so a reader never sees a half-written note. This is
optimistic concurrency: **detect + retry, never clobber.**

**Git is the backstop.** The vault is a git repo: commit after each batch of
changes. Even if a non-skill writer clobbers something, every state is
recoverable. For a **bulk restructure**, still run it only when the vault is
quiet and `git status` before/after: CAS protects a single write, not a whole reorg.

## Durability: never lose an unsaved write

The guard and CAS stop *clobbering*, but a write that can't land (vault busy, a
conflict, a filesystem glitch) must not die with the session. So **persist to the
outbox the moment vault-bound content exists**, before attempting the vault:

```bash
BIN=~/vault/Harness/Skills/smart-notes/bin
# new note:
printf '%s' "$content" | "$BIN"/vault-outbox.py enqueue --target Permanent/foo.md --new
# update (base on the sha you read):
printf '%s' "$content" | "$BIN"/vault-outbox.py enqueue --target plan.md --base-sha "$sha"
```

The outbox lives on durable, uncontended storage (`~/.claude/vault-outbox/`), so
the enqueue always succeeds and **survives session close**. Then drain it into the
vault (safe anytime, per-file CAS, no whole-vault lock needed):

```bash
"$BIN"/vault-outbox.py drain --vault ~/vault --commit   # apply + git-commit
"$BIN"/vault-outbox.py status                            # pending / applied / conflict
```

- **Drain on every `/smart-notes` invocation** and after finishing a batch of
  writes, so nothing lingers pending.
- Conflicts (the base changed under you) go to `~/.claude/vault-outbox/conflict/`:
  never dropped, never clobbered; resolve by re-reading and re-enqueuing.
  A conflict that turns out redundant (someone else wrote the *same* bytes, e.g.
  a double-promotion) is retired automatically: `drain` reconciles it, or run
  `"$BIN"/vault-outbox.py reconcile --vault .`: content-sha matches on-disk, so
  it's a pure no-op. Only genuinely divergent conflicts need a manual merge.
- `SessionStart` / `SessionEnd` hooks in `~/.claude/settings.json` drain
  automatically; the enqueue-on-generate discipline is what puts work there to be
  drained.

**Rule of thumb:** routine note/plan writes never need a quiet vault: enqueue +
drain (per-file CAS) handles concurrency. Only a *bulk restructure* needs the
whole vault quiet.

## Graph & tags: keeping the vault connected

Obsidian's graph is built from `[[links]]` (including frontmatter wikilinks like
`parent_plan`) and, with tag-nodes on, from shared tags. A weak graph = too few
cross-silo links. Keep it connected:

- **Every note gets >=1 link before you close it** (the permanent-note rule, everywhere).
- **Link across silos via `Permanent/`**: a project insight promoted to a permanent
  note and linked back is what connects projects to each other.
- **Maintain the hubs:** `Permanent/00-home.md` links every silo; each project has a
  `00-INDEX.md`. When you add a project, link its index from `00-home`.
- **Colour groups** live in `.obsidian/graph.json` (git-tracked): layer + theme
  colours; `#needs-link` marks the orphan backlog and `#digest` the review
  frontier (see below). Reopen Graph View after edits.
- **Measure it:** `"$BIN"/vault-doctor.py --vault . --graph` reports islands, isolated notes,
  and per-folder cross-silo links (0 = an island to bridge).
- **Provenance is bidirectional:** a permanent note's `**Source:**` cites the *exact* origin (doc + section/date); the source doc carries an `## Insights extracted` footer listing the notes it produced. Do both when promoting insights from a silo: the loop stays visible and adds source→slipbox edges.

### Tags: a controlled vocabulary
Tags drive graph grouping/colour, so keep them consistent: **lowercase-kebab**, from
this canonical set (extend deliberately, don't invent one-offs):
- **theme/project:** `#project-alpha` `#project-beta` (replace with your own project tags)
- **type:** `#permanent` `#literature` `#plan` `#handoff` `#progress-log` `#experiment` `#poc` `#strategy`
- **domain:** `#ai-safety` `#evaluation` `#agent-auditing` `#optimization` `#engineering` `#knowledge-management`
- **`#needs-link`**: an idea-orphan you intend to connect (pops in the graph).
- **`#digest`**: a finding created but not yet understood by you (the review
  frontier, see below; pops in the graph in its own colour).

### The digest frontier
`status:` asks *is the claim backed?* (a property of the note). `#digest` asks
a different question: *have you internalised this yet?* (a property of your
attention). The two are orthogonal: a `supported` finding can still be unread.
This is the signal that keeps a new insight from vanishing as just another node.

- **Born tagged.** When a session creates a finding, hypothesis, or insight for
  you to review (typically promoting experiment output to a permanent or
  literature note), give it `#digest` at creation. That is the only moment the
  "you haven't seen this" state is reliably knowable.
- **Stripped when understood.** You remove `#digest` once you've read and
  grasped the note; it then recedes into the settled corpus. The tagged set is
  therefore self-maintaining ≈ "recent and undigested": no time channel needed.
- **Two views** (both driven by the `.obsidian/graph.json` colour group):
  the graph with `#digest` lit up shows the frontier *in context* against the
  web it connects to; the graph search filter `tag:#digest` collapses to just
  the queue. Don't blanket-tag: only what genuinely needs your eyes.
- **Leak check:** `"$BIN"/vault-doctor.py --vault . --digest` flags findings
  created recently in small (non-bulk) commits that were never tagged `#digest`:
  a finding that slipped in without self-marking. Candidates, not errors:
  ignore your own settled notes, tag the ones that need your eyes. It reads
  git for authored-date, so bulk restructures are filtered out by commit size.

## Maintenance: vault-doctor

```bash
BIN=~/vault/Harness/Skills/smart-notes/bin
"$BIN"/vault-doctor.py --vault ~/vault   # add --full for untruncated lists
```

Other reports: `--claims` (epistemic status + staleness, plus grade-binding
invariants; `--claims-stale-days` sets the horizon, default 30), `--graph`
(connectivity), `--digest` (review-frontier leaks), `--hypotheses`
(hypothesis-pipeline open queue, stale + grade-integrity, and a
Resolved-by-grade view, see "Hypotheses" above).

Read it as: **broken links** (fix, or intentional stubs) · **idea-bearing
orphans** (link/promote/accept) · **oversized idea notes** (split only if an
idea, not a log) · **version-duplicate clusters** (archive the superseded).

**Gate for any restructuring:** a change must **not increase** the broken-link
count. Run before and after.

**Moving a note** (path links break on filesystem moves): find inbound links,
rewrite them in the same change, `git mv`, re-run vault-doctor, count unchanged.
**Never delete**: superseded files go to `_Archive/`; confirm before removing.

### The sweep
`vault-doctor.py` checks machine health; nothing schedules the human processing
that keeps `00-Inbox/` from silting up. Every 3-7 days:
1. `"$BIN"/vault-outbox.py drain`: nothing should be left pending.
2. **Process `00-Inbox/`** (**shallow on purpose**): give each note an
   informative title, file it where it belongs, delete the fleeting original.
   Do *not* distil, summarise, or chase every connection here: that work
   belongs to the moment you actually have a use for the note. Check each item
   against `Permanent/00-open-questions.md` on the way past: a capture that
   answers a standing question is worth linking even at sweep speed.
3. `"$BIN"/vault-doctor.py`: read broken links / orphans / oversized notes.

The shallowness rule is counterintuitive but it's the reason inbox processing
stays cheap enough to actually happen every week instead of becoming a chore
that gets deferred until the inbox is unmanageable.

## What NOT to do
- Don't atomize operational notes (plans / logs / handoffs / CVs / lessons).
- Don't bury a reusable idea in a log: extract to `Permanent/` and link.
- Don't invent status values or frontmatter fields: use the schema above.
- Don't blind-overwrite a vault file: use `vault-write.py` (CAS).
- **Archiving preserves reachability**: a file in `_Archive/` is still linkable via `[[basename]]` (resolves wherever it lives); keep the link and mark it `(archived)`, never strip a link to still-useful content.
- No Luhmann numeric IDs; don't chase orphan count to zero.

## Quick reference
| Task | Where |
|---|---|
| Plan / handoff / progress / index | `references/project-plan.md` · `session-handoff.md` · `progress-log.md` · `project-index.md` |
| Permanent / literature / structure / fleeting | `references/permanent-note.md` · `literature-note.md` · `structure-note.md` · `fleeting-capture.md` |
| Hypothesis dossier + rubric | `references/hypothesis-dossier.md` · `methodology/empirical-robustness-standard.md` |
| Concurrency-safe write | `bin/vault-write.py` |
| Durable write + retry (outbox) | `bin/vault-outbox.py` (enqueue / drain) |
| Health check / gate | `bin/vault-doctor.py` |
