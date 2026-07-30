# think-smarterer

A portable, plain-markdown knowledge and research-methodology system for
Obsidian and AI coding agents. No runtime, no SDK, no lock-in: everything here
is markdown files, frontmatter conventions, and a handful of small Python
scripts that operate on plain text files.

It originated as one person's Obsidian vault methodology, refined over real
use.

## What's in here

```
skill/
  SKILL.md                 the operating manual / structure spec
  references/               one template per note type
  bin/                       vault-doctor, vault-write, vault-outbox + tests
methodology/
  empirical-robustness-standard.md   the five-rung evidence-grading ladder
  notes/                     six backing notes for the standard's imported criteria
```

`skill/` is a Claude Code skill: the note-taking and research-hygiene system
an AI agent (or you) uses when writing into an Obsidian vault. `methodology/`
is the standalone evidence-grading standard the skill's hypothesis pipeline
grades claims against. You can use either half without the other: the skill
works with any grading standard, and the standard is a general-purpose
research-rigor rubric you can apply outside Obsidian entirely.

## Why plain markdown

The vault is not a database and the skill is not an app. Every note is a
`.md` file with YAML frontmatter, readable and editable with any text editor,
diffable in git, and greppable. Frontmatter follows the [Open Knowledge Format
(OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
`type:` convention where applicable, an open standard from Google Cloud for
representing knowledge as plain markdown files, so notes stay portable across
tools rather than locked into one vault's plugin config.

## Installing the skill

Copy (or symlink) `skill/` into your agent's skills directory, e.g. for
Claude Code:

```bash
ln -s /path/to/think-smarterer/skill ~/.claude/skills/smart-notes
```

Symlinking rather than copying means edits to the skill (or `git revert` in
this repo) stay live without a separate deploy step. Set `SMART_NOTES_VAULT`
or pass `--vault` to point the `bin/` tools at your actual Obsidian vault
(referred to as `~/vault` throughout the docs; substitute your real path).

## The note types

The vault has two layers. **Operational** notes are living work: project
plans, session handoffs, progress logs, project indexes. They're
folder-organised per project and archived when the project ends.
**Thinking** notes are the slipbox: ideas that outlive any single project,
moving through four stages:

- **fleeting**: a raw capture in `00-Inbox/`, processed then deleted
- **literature**: your distillation of one external source
- **permanent**: one reusable idea, in your own words, titled as a claim
- **structure**: a hand-maintained map of content once a cluster has ~5+ notes

Templates for all note types live in `skill/references/`. Read `skill/SKILL.md`
first: it's the routing table that tells you which template to use for what
you're about to write, and the full frontmatter/status schema.

## The hypothesis pipeline

A testable claim moves through three stages:

```
00-open-questions  ->  hypothesis dossier  ->  verified permanent note
```

The dossier (`skill/references/hypothesis-dossier.md`) is created with a
mandatory **pre-registration block** written before any result is known: the
exact test, the numeric threshold, and the result that would refute the
claim. This is the anti-HARKing lock (Hypothesizing After the Results are
Known); writing the threshold down before you see the data is what keeps a
result honest.

Once evidence is in, the claim is graded on a five-rung ladder defined in
`methodology/empirical-robustness-standard.md`:

| Grade | What it means |
|---|---|
| suggested | pre-registered, no controlled test run yet |
| tested | run against a matched baseline, crosses the pre-registered threshold |
| robust | confounds ruled out, evaluator blinded, effect size + uncertainty reported |
| replicated | holds across seeds/models/datasets, via genuinely independent approaches |
| paper-grade | independently verified, limits of generalization stated, comparisons disclosed |

`target_grade` scales rigor to consequence: a decision-grade hunch might only
need `tested`; a paper-track claim needs `paper-grade`. Grading is a human (or
agent) judgement call; automated tooling can only confirm the paperwork for a
grade is present, never that the underlying evidence is actually good.

## vault-doctor

`skill/bin/vault-doctor.py` is the health-check and gating tool for a vault.
All commands accept `--vault PATH` (or `$SMART_NOTES_VAULT`, or auto-detect
via the nearest `.obsidian` ancestor).

```bash
vault-doctor.py --vault ~/vault              # broken links, orphans, oversized notes, duplicates
vault-doctor.py --vault ~/vault --claims     # epistemic status + staleness (source doc newer than note)
vault-doctor.py --vault ~/vault --graph      # connectivity: islands, isolated notes, cross-silo links
vault-doctor.py --vault ~/vault --digest     # #digest review-frontier leaks (git-based)
vault-doctor.py --vault ~/vault --hypotheses # open queue by grade, stale dossiers, grade-integrity
```

The hard gate for any restructuring: a batch of changes must **not increase**
the broken-link count. Run `vault-doctor.py` before and after.

Two companion tools handle safe writes under concurrency (useful when
multiple agent sessions or a human editor might touch the same vault at
once):

- `vault-write.py`: compare-and-swap atomic writer. Read the current sha,
  write only if it hasn't changed underneath you, exit 3 on conflict.
- `vault-outbox.py`: a durable write-ahead queue. Enqueue vault-bound
  content the moment it exists, so a rejected or interrupted write survives
  session close; drain it into the vault later (safe anytime, per-file CAS).

## Note

This repo is the generalized methodology and tooling, not a working vault. It
ships templates, not populated notes, and the scripts operate on whatever
Obsidian vault you point them at.

## Credits and influences

The note-taking layer stands on established knowledge-management work and
synthesizes it into one operational toolkit:

- **Niklas Luhmann** originated the Zettelkasten (slipbox): atomic, linked notes
  from which structure emerges rather than being imposed up front.
- **Sönke Ahrens, _How to Take Smart Notes_ (2017)** operationalized the slipbox
  for modern use. The note-type vocabulary here (fleeting, literature, permanent,
  structure), the "smart notes" name, and the principle that writing an idea in
  your own words is the test of understanding it all come from this book.
- **Tiago Forte, _Building a Second Brain_ (2022)** contributes the CODE and PARA
  framing, progressive summarization, the Hemingway Bridge (the basis for the
  session-handoff practice), the capture criteria, the weekly review (the
  "sweep"), the standing-questions idea ("12 Favorite Problems"), and the
  Archipelago of Ideas.

The **empirical-robustness standard** and the **hypothesis pipeline** are
original additions, drawing on standard open-science practice (pre-registration,
and avoiding HARKing) rather than on the books above.
