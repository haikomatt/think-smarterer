#!/usr/bin/env python3
"""vault-doctor: health report for an Obsidian vault.

Run before and after every restructure batch. The gate is simple:
**a batch must not increase the broken-link count.**

Usage:
    vault-doctor.py [--vault PATH] [--json] [--full]
    vault-doctor.py --digest [--digest-days N]   # #digest review-frontier leaks
    vault-doctor.py --hypotheses [--hyp-stale-days N]  # hypothesis-pipeline integrity

    --vault PATH   vault root (default: $SMART_NOTES_VAULT, else auto-detect
                   the nearest ancestor containing .obsidian, else cwd)
    --json         print a machine-readable summary block (for diffing batches)
    --full         do not truncate the broken-link / orphan / oversized lists
    --digest       findings created recently but never tagged #digest (git-based)
    --digest-days  window for --digest (default 14)
    --hypotheses   open hypotheses by grade, stale dossiers, grade-integrity
                   presence check (advisory, never gates); default N=21 days

Resolution mirrors Obsidian: [[target]] links are matched case-insensitively;
targets with a "/" resolve by vault-relative path, others by basename
(shortest-path). Alias (|) and heading (#) suffixes are stripped. Pure
"[[#heading]]" in-note links are ignored.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

IGNORE_DIRS = {
    ".obsidian",
    ".trash",
    ".git",
    "_meta",
}  # _meta = tooling/reports, not content
# Folders whose notes are exempt from the "orphan" and "oversized" nags
# (they are meant to be standalone / long): logs, archives, reference material.
QUIET_ORPHAN_HINTS = ("_archive", "career/", "clients/", "learning/japanese", "people/")
OVERSIZED_WORDS = 3000
# --digest: an ADD commit introducing more .md files than this is a bulk
# import/restructure, not a per-finding promotion: its notes are not leaks.
DIGEST_BULK_ADD = 6
# --claims: default staleness horizon (days) for a pushed grade_binding check.
GRADE_BINDING_MAX_AGE = 30
WIKILINK = re.compile(r"(!?)\[\[([^\]\n]+?)\]\]")
INLINE_CODE = re.compile(r"`[^`]*`")
FENCE = re.compile(r"^\s*(```|~~~)")
VERSION_TOKEN = re.compile(r"[ _-]*[vV]\d+(?:\.\d+)?(?:_[a-z]+)?$")


def find_vault(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("SMART_NOTES_VAULT")
    if env:
        return Path(env).expanduser().resolve()
    here = Path.cwd().resolve()
    for cand in [here, *here.parents]:
        if (cand / ".obsidian").is_dir():
            return cand
    return here


def iter_files(vault: Path):
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            yield Path(root) / f


def norm(s: str) -> str:
    return s.strip().lstrip("./").lower()


def _resolve_note(target, by_rel, by_base):
    """Resolve a wikilink target to a single note (first match), or None.

    Obsidian-style: alias (|) and heading (#) suffixes are stripped; a slashed
    link matches by vault-relative path or path suffix; a bare name matches by
    basename. Value-agnostic (returns whatever the index stores). Shared by the
    --claims and --graph reports, which consider md notes only and take the
    first match.
    """
    t = target.split("|", 1)[0].split("#", 1)[0].strip().lstrip("./").lower()
    parts = [p for p in t.split("/") if p not in ("", ".", "..")]
    t = "/".join(parts)
    if not t:
        return None
    if len(parts) > 1:
        for key in (t, t + ".md"):
            if key in by_rel:
                return by_rel[key]
        for rel, val in by_rel.items():
            if rel.endswith("/" + t) or rel.endswith("/" + t + ".md"):
                return val
        return None
    stem = t[:-3] if t.endswith(".md") else t
    cands = by_base.get(stem) or []
    return cands[0] if cands else None


def _resolve_link(target, by_relpath, by_basename, by_fullname):
    """Resolve a wikilink for broken-link detection.

    Returns (resolved?, unique_target_or_None): a link counts as resolved if it
    matches any file, but the concrete target is only returned when the match is
    unique (mirroring Obsidian). Slashed links match by vault-relative path or
    path suffix; bare names match by basename (note) or full filename
    (attachment). Used by the default report's scan.
    """
    t = norm(target)
    if not t:  # pure "#heading" in-note link
        return True, None
    parts = [p for p in t.split("/") if p not in ("", ".", "..")]
    t = "/".join(parts)
    if len(parts) > 1:  # slashed link: path or suffix match
        cands = set()
        for key in (t, f"{t}.md"):
            if key in by_relpath:
                cands.add(by_relpath[key])
        for rel, f in by_relpath.items():
            if rel.endswith(f"/{t}") or rel.endswith(f"/{t}.md"):
                cands.add(f)
        hit = next(iter(cands)) if len(cands) == 1 else None
        return bool(cands), hit
    # bare name: basename (note) or full filename (attachment)
    stem = t[:-3] if t.endswith(".md") else t
    cands = by_basename.get(stem) or by_fullname.get(t) or []
    hit = cands[0] if len(cands) == 1 else None
    return bool(cands), hit


def claims_report(vault, stale_days):
    """Epistemic-status + staleness report for permanent (claim) notes."""
    today = date.today()
    md_files = [f for f in iter_files(vault) if f.suffix.lower() == ".md"]
    by_relpath = {}
    by_basename = defaultdict(list)
    for f in md_files:
        rel_path = str(f.relative_to(vault)).lower()
        by_relpath[rel_path] = f
        by_relpath[rel_path[:-3]] = f
        by_basename[f.stem.lower()].append(f)
    notes = [
        f
        for f in md_files
        if "permanent/" in str(f.relative_to(vault)).lower()
        and not f.name.startswith("00-")
        and f.name.lower() != "readme.md"
    ]
    status_re = re.compile(r"^status:\s*([a-z]+)", re.M)
    source_re = re.compile(r"\*\*Source:\*\*\s*\[\[([^\]]+?)\]\]")
    evidence_re = re.compile(r"^## Evidence", re.M)
    by_status = Counter()
    no_status = []
    untested = []
    revisit = []
    stale = []
    grade_binding_flagged = []
    for f in notes:
        text = f.read_text(encoding="utf-8", errors="replace")
        fm_match = FM_BLOCK.match(text)
        fm_block = fm_match.group(1) if fm_match else ""
        binding_state = _grade_binding_state(fm_block, today, stale_days)
        if binding_state is not None:
            grade_binding_flagged.append((f, binding_state))
        status_match = status_re.search(text)
        status = status_match.group(1) if status_match else None
        if status:
            by_status[status] += 1
        else:
            no_status.append(f)
        has_evidence = bool(evidence_re.search(text))
        if (status in (None, "hypothesis")) and not has_evidence:
            untested.append(f)
        if status in ("refuted", "superseded"):
            revisit.append((f, status))
        source_match = source_re.search(text)
        if source_match:
            source_note = _resolve_note(source_match.group(1), by_relpath, by_basename)
            if (
                source_note is not None
                and source_note.exists()
                and source_note.stat().st_mtime > f.stat().st_mtime
            ):
                stale.append((f, source_note))
    rel = lambda f: str(f.relative_to(vault))
    print(f"# vault-doctor --claims  {vault}")
    print(f"claim notes: {len(notes)}")
    for status_name, count in by_status.most_common():
        print(f"  {status_name:<12} {count}")
    if no_status:
        print(f"  {'(no status)':<12} {len(no_status)}")

    def dump(title, items, fmt):
        print(f"\n## {title} ({len(items)})")
        for item in items[:40]:
            print("  " + fmt(item))

    dump(
        "Untested (hypothesis / no status, no Evidence): validate or link evidence",
        untested,
        rel,
    )
    dump(
        "Revisit (refuted / superseded)",
        revisit,
        lambda entry: f"[{entry[1]}] {rel(entry[0])}",
    )
    dump(
        "Potentially STALE: source doc is newer than the note (new evidence may exist)",
        stale,
        lambda entry: f"{rel(entry[0])}  <-  {rel(entry[1])}",
    )
    dump(
        "Grade-binding invariant (broken / stale / unverified): a declared check needs a human look",
        grade_binding_flagged,
        lambda entry: f"[{entry[1]}] {rel(entry[0])}",
    )
    return 0


def graph_report(vault):
    """Graph connectivity: components (islands), isolated notes, cross-silo edges."""
    relpaths = [
        str(f.relative_to(vault))
        for f in iter_files(vault)
        if f.suffix.lower() == ".md"
    ]
    by_relpath = {}
    by_basename = defaultdict(list)
    for rel in relpaths:
        key = rel.lower()
        by_relpath[key] = rel
        by_relpath[key[:-3]] = rel
        by_basename[os.path.basename(rel)[:-3].lower()].append(rel)
    adjacency = defaultdict(set)
    for rel in relpaths:
        in_fence = False
        for line in (
            (vault / rel).read_text(encoding="utf-8", errors="replace").splitlines()
        ):
            if FENCE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for _embed, raw in WIKILINK.findall(INLINE_CODE.sub("", line)):
                resolved = _resolve_note(raw, by_relpath, by_basename)
                if resolved and resolved != rel:
                    adjacency[rel].add(resolved)
                    adjacency[resolved].add(rel)
    top = lambda path: path.split("/")[0] if "/" in path else "(root)"
    seen = set()
    components = []
    for rel in relpaths:
        if rel in seen:
            continue
        stack = [rel]
        component = []
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            component.append(node)
            stack += [
                neighbour for neighbour in adjacency[node] if neighbour not in seen
            ]
        components.append(component)
    components.sort(key=len, reverse=True)
    isolated = sum(1 for component in components if len(component) == 1)
    cross_degree = defaultdict(int)
    notes_by_folder = defaultdict(int)
    for rel in relpaths:
        notes_by_folder[top(rel)] += 1
    for rel, neighbours in adjacency.items():
        for neighbour in neighbours:
            if top(rel) != top(neighbour):
                cross_degree[top(rel)] += 1
    print(f"# vault-doctor --graph  {vault}")
    print(
        f"nodes: {len(relpaths)}   components (islands): {len(components)}   isolated singles: {isolated}"
    )
    print(f"largest cluster: {len(components[0]) if components else 0}")
    print("\nmulti-note islands (not the main cluster):")
    for component in components[1:9]:
        if len(component) < 2:
            break
        folder_counts = defaultdict(int)
        for rel in component:
            folder_counts[top(rel)] += 1
        print(
            "  "
            + str(len(component))
            + "  "
            + ", ".join(
                f"{folder}:{count}"
                for folder, count in sorted(
                    folder_counts.items(), key=lambda item: -item[1]
                )[:3]
            )
        )
    print("\nper top-folder cross-silo links (0 = island):")
    for folder in sorted(notes_by_folder):
        print(
            f"  {folder:<16} notes:{notes_by_folder[folder]:<4} cross:{cross_degree[folder]}"
        )
    return 0


def digest_report(vault, window_days):
    """Digest-frontier leak check.

    A finding created recently but never tagged `#digest` may have slipped into
    the vault without self-marking (see SKILL.md "The digest frontier"). Flag
    finding notes (Permanent/, Literature/) that are currently untagged, were
    added within the window, and have NO `#digest` anywhere in their git history,
    i.e. never in the frontier, as opposed to tagged-then-stripped (already
    digested). Creation dates come from git, so a git repo is required.
    """
    import subprocess, time

    def git(*a):
        return subprocess.run(
            ["git", "-C", str(vault), *a], capture_output=True, text=True
        )

    if git("rev-parse", "--is-inside-work-tree").returncode != 0:
        print("# vault-doctor --digest")
        print("needs a git repo: creation dates come from git history; none found.")
        return 0

    fm_re = re.compile(r"^---\n(.*?)\n---", re.S)

    def has_digest(txt: str) -> bool:
        if re.search(r"(?<![\w#])#digest\b", txt):  # inline #digest
            return True
        m = fm_re.match(txt)
        if not m:
            return False
        block = m.group(1)
        for inline in re.findall(r"^tags:\s*\[([^\]]*)\]", block, re.M):
            if any(
                t.strip().strip("\"'").lstrip("#") == "digest"
                for t in inline.split(",")
            ):
                return True
        ml = re.search(r"^tags:\s*\n((?:\s*-\s*.+\n?)+)", block, re.M)
        if ml and any(
            l.strip().lstrip("-").strip().strip("\"'").lstrip("#") == "digest"
            for l in ml.group(1).splitlines()
        ):
            return True
        return False

    def is_finding(f: Path) -> bool:
        rel = str(f.relative_to(vault)).lower()
        return (
            ("permanent/" in rel or "literature/" in rel)
            and not f.name.startswith("00-")
            and f.name.lower() != "readme.md"
        )

    findings = [
        f for f in iter_files(vault) if f.suffix.lower() == ".md" and is_finding(f)
    ]

    # group git ADD history into commits (newest first), then record for each
    # path its most-recent add: (timestamp, #md-files that commit added). The
    # file count lets us drop bulk imports/restructures, whose add-date is not
    # the finding's authored-date.
    commits: list[tuple[int, list[str]]] = []
    cur_ts = None
    cur_files: list[str] = []
    for line in git(
        "log", "--diff-filter=A", "--pretty=format:@%ct", "--name-only"
    ).stdout.splitlines():
        line = line.strip()
        if line.startswith("@") and line[1:].isdigit():
            if cur_ts is not None:
                commits.append((cur_ts, cur_files))
            cur_ts, cur_files = int(line[1:]), []
        elif line.endswith(".md"):
            cur_files.append(line)
    if cur_ts is not None:
        commits.append((cur_ts, cur_files))
    add_info: dict[str, tuple[int, int]] = {}  # path -> (ts, commit md count)
    for ts, files in commits:  # newest first → first seen wins
        n = len(files)
        for p in files:
            add_info.setdefault(p, (ts, n))

    now = time.time()
    cutoff = now - window_days * 86400
    leaks: list[tuple[Path, int]] = []
    uncommitted: list[Path] = []
    for f in findings:
        txt = f.read_text(encoding="utf-8", errors="replace")
        if has_digest(txt):
            continue  # in the frontier now, fine
        rel = str(f.relative_to(vault))
        info = add_info.get(rel)
        if info is None:
            uncommitted.append(f)  # not yet an Add, or renamed
            continue
        ct, csize = info
        if ct < cutoff:
            continue  # old & untagged → settled, not a leak
        if csize > DIGEST_BULK_ADD:
            continue  # bulk import/restructure, not a finding
        if git("log", "-S#digest", "--format=%H", "--", rel).stdout.strip():
            continue  # had #digest once → stripped = digested
        leaks.append((f, ct))

    rel = lambda f: str(f.relative_to(vault))
    days = lambda ct: int((now - ct) // 86400)
    leaks.sort(key=lambda x: -x[1])
    print(f"# vault-doctor --digest  {vault}")
    print(
        f"finding notes: {len(findings)}   window: last {window_days} days   "
        f"(bulk-add commits >{DIGEST_BULK_ADD} md files excluded)"
    )
    print(f"\n## Digest leaks: recent findings never tagged #digest ({len(leaks)})")
    print("   tag #digest if it needs your attention; ignore your own settled notes")
    for f, ct in leaks:
        print(f"  {days(ct):>3}d  {rel(f)}")
    if uncommitted:
        print(f"\n## New / uncommitted findings: no git Add yet ({len(uncommitted)})")
        print("   brand-new or renamed; confirm whether each needs #digest")
        for f in uncommitted:
            print(f"  {rel(f)}")
    return 0


FM_BLOCK = re.compile(r"^---\n(.*?)\n---", re.S)
HYP_TEST_RE = re.compile(r"-\s*\*\*Test:\*\*\s*(.+)", re.I)
HYP_THRESHOLD_RE = re.compile(r"-\s*\*\*Threshold:\*\*\s*(.+)", re.I)
HYP_REFUTES_RE = re.compile(r"-\s*\*\*Refutes if:\*\*\s*(.+)", re.I)
PLACEHOLDER_STUB = re.compile(r"^<[^<>]*>$")
UNCERTAINTY_RE = re.compile(
    r"(CI|confidence interval|\binterval\b|uncertainty|standard error|\bstd\b|±)", re.I
)
REPLICATED_RE = re.compile(
    r"(replicat|across (seeds|models|datasets)|independent approach|\bseeds\b)", re.I
)
PAPER_GRADE_RE = re.compile(
    r"(independent verification|independently verified|independent check|\bexternal\b)",
    re.I,
)
CREATED_RE = re.compile(r'^created:\s*"?(\d{4}-\d{2}-\d{2})"?', re.M)


def _frontmatter_field(fm_block: str, field: str) -> str | None:
    m = re.search(rf"^{field}:\s*(.+)$", fm_block, re.M)
    if not m:
        return None
    return m.group(1).strip().strip("\"'") or None


def _grade_binding_state(fm_block: str, today: date, stale_days: int) -> str | None:
    """Grade-binding invariant state for a permanent (claim) note.

    Read-only PUSH-model check: an external owner (for example a CI job)
    writes grade_binding_result / grade_binding_checked into the note's
    frontmatter; this function only ever reads those two fields back, never
    executes anything. grade_binding_result is normalised (stripped,
    lowercased) before comparison, since the writer is an external system in
    another repo whose casing convention nothing on this side enforces: "Fail" /
    "FAIL" and "Pass" / "PASS" must be read the same as their lowercase
    forms, on both the fail path and the pass/staleness path. Precedence:
      - no grade_binding field -> None (strict no-op)
      - normalised result == "fail" -> "broken" (wins over everything,
        including a grade_binding_checked far past the staleness horizon,
        even if checked itself is missing)
      - either of grade_binding_result / grade_binding_checked present
        without the other, or both absent -> "unverified" (a half-landed
        write-back is not a trustworthy verification)
      - normalised result present and recognised as neither "fail" nor
        "pass" (e.g. "error", "passed") -> "unverified": we have no evidence
        of failure, so "broken" would overclaim, and silently returning None
        would hide a check we can't actually read, so it fails closed toward
        asking a human
      - normalised result == "pass" and checked strictly older than
        stale_days before today -> "stale" (checked == today - stale_days is
        NOT stale)
      - normalised result == "pass" and fresh -> None
    A malformed/unparseable grade_binding_checked is treated as "unverified"
    rather than raising, since the vault is multi-writer and a bad value must
    never crash a health check.
    """
    grade_binding = _frontmatter_field(fm_block, "grade_binding")
    if grade_binding is None:
        return None

    result = _frontmatter_field(fm_block, "grade_binding_result")
    checked = _frontmatter_field(fm_block, "grade_binding_checked")
    normalized_result = result.strip().lower() if result is not None else None

    if normalized_result == "fail":
        return "broken"

    if result is None or checked is None:
        return "unverified"

    if normalized_result != "pass":
        return "unverified"

    try:
        checked_date = date.fromisoformat(checked)
    except ValueError:
        return "unverified"

    if (today - checked_date).days > stale_days:
        return "stale"

    return None


def _get_section(body: str, heading: str) -> str:
    """Text under '## {heading}' up to the next '## ' heading or EOF."""
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$", body, re.M)
    if not m:
        return ""
    start = m.end()
    nxt = re.search(r"^##\s+", body[start:], re.M)
    return body[start : start + nxt.start()] if nxt else body[start:]


def _is_dossier(f: Path, vault: Path, fm_block: str) -> bool:
    rel = str(f.relative_to(vault)).lower()
    if rel.startswith("hypotheses/") and not f.name.startswith("00-"):
        return True
    return _frontmatter_field(fm_block, "type") == "hypothesis"


def _is_graded_permanent(f: Path, vault: Path, fm_block: str) -> bool:
    rel = str(f.relative_to(vault)).lower()
    if (
        "permanent/" not in rel
        or f.name.startswith("00-")
        or f.name.lower() == "readme.md"
    ):
        return False
    return _frontmatter_field(fm_block, "grade") is not None


def _is_placeholder(value: str) -> bool:
    return bool(PLACEHOLDER_STUB.match(value.strip()))


def _preregistration_missing(body: str) -> list[str]:
    sec = _get_section(body, "Pre-registration")
    if not sec.strip():
        return ["## Pre-registration section"]
    missing = []
    for label, rx in (
        ("Test", HYP_TEST_RE),
        ("Threshold", HYP_THRESHOLD_RE),
        ("Refutes if", HYP_REFUTES_RE),
    ):
        m = rx.search(sec)
        value = m.group(1).strip() if m else ""
        if not value or _is_placeholder(value):
            missing.append(f"{label} filled in Pre-registration")
    return missing


def _grade_markers_missing(grade: str, body: str) -> list[str]:
    """Presence-only heuristic: flag evidence markers claimed grade requires
    but the body doesn't contain. Never judges whether evidence is good."""
    g = (grade or "").strip().lower()
    if g == "suggested":
        return _preregistration_missing(body)
    if g == "tested":
        missing = []
        if not re.search(r"\[\[([^\]\n]+?)\]\]", _get_section(body, "Experiment")):
            missing.append("[[link]] inside ## Experiment")
        if not re.search(r"\bbaseline\b", body, re.I):
            missing.append("token 'baseline'")
        return missing
    if g == "robust":
        missing = []
        if not re.search(r"\bconfound", body, re.I):
            missing.append("token 'confound'")
        if not UNCERTAINTY_RE.search(body):
            missing.append(
                "an uncertainty token (CI/interval/uncertainty/standard error/std/±)"
            )
        return missing
    if g == "replicated":
        return (
            []
            if REPLICATED_RE.search(body)
            else [
                "a replication token (replicat.../across seeds|models|datasets/independent approach/seeds)"
            ]
        )
    if g == "paper-grade":
        return (
            [] if PAPER_GRADE_RE.search(body) else ["an independent-verification token"]
        )
    return []


def _hypothesis_findings(vault: Path, stale_days: int, today: date) -> dict:
    """Structured findings for --hypotheses, shared by the report and its tests.

    Returns {"open": [(rel, grade, target_grade)], "stale": [(rel, age_days,
    [reasons])], "integrity": [(rel, grade, [missing markers])], "resolved":
    [(rel, status, grade)]}.

    A dossier is "open" iff status == "hypothesis"; any other terminal status
    (supported / refuted / mixed / contested / superseded) is "resolved".
    """
    md = [f for f in iter_files(vault) if f.suffix.lower() == ".md"]
    open_list: list[tuple[str, str | None, str | None]] = []
    stale_list: list[tuple[str, int, list[str]]] = []
    integrity_list: list[tuple[str, str, list[str]]] = []
    resolved_list: list[tuple[str, str, str | None]] = []

    for f in md:
        text = f.read_text(encoding="utf-8", errors="replace")
        fm_match = FM_BLOCK.match(text)
        fm_block = fm_match.group(1) if fm_match else ""
        body = text[fm_match.end() :] if fm_match else text

        is_dossier = _is_dossier(f, vault, fm_block)
        is_graded_permanent = (not is_dossier) and _is_graded_permanent(
            f, vault, fm_block
        )
        if not is_dossier and not is_graded_permanent:
            continue

        rel = str(f.relative_to(vault))
        status = _frontmatter_field(fm_block, "status")
        grade = _frontmatter_field(fm_block, "grade")
        target_grade = _frontmatter_field(fm_block, "target_grade")

        if is_dossier and status == "hypothesis":
            open_list.append((rel, grade, target_grade))

        if is_dossier and status and status != "hypothesis":
            resolved_list.append((rel, status, grade))

        if is_dossier:
            created = None
            cm = CREATED_RE.search(fm_block)
            if cm:
                try:
                    created = date.fromisoformat(cm.group(1))
                except ValueError:
                    created = None
            if created is not None:
                age = (today - created).days
                if age > stale_days:
                    exp = _get_section(body, "Experiment")
                    reasons = []
                    if not re.search(r"\[\[([^\]\n]+?)\]\]", exp):
                        reasons.append("no experiment linked")
                    if (grade or "").strip().lower() == "suggested":
                        reasons.append("grade still suggested")
                    if reasons:
                        stale_list.append((rel, age, reasons))

        if grade:
            missing = _grade_markers_missing(grade, body)
            if missing:
                integrity_list.append((rel, grade, missing))

    return {
        "open": open_list,
        "stale": stale_list,
        "integrity": integrity_list,
        "resolved": resolved_list,
    }


def hypotheses_report(vault: Path, stale_days: int) -> int:
    """Hypothesis-pipeline integrity report (advisory, never gates).

    Scans Hypotheses/*.md dossiers (excluding 00-* index files, or any note
    tagged type: hypothesis) plus Permanent/*.md notes carrying a grade:
    field. Reports the open queue by grade, stale dossiers, and a grade-
    integrity presence check (never judges whether evidence is *good*).
    """
    from collections import defaultdict

    findings = _hypothesis_findings(vault, stale_days, date.today())

    print(f"# vault-doctor --hypotheses  {vault}")
    print(f"stale window: {stale_days} days")

    by_grade: dict[str, list[tuple[str, str | None]]] = defaultdict(list)
    for rel, grade, target in findings["open"]:
        by_grade[grade or "(no grade)"].append((rel, target))
    print(f"\n## Open hypotheses by grade ({len(findings['open'])})")
    for grade in sorted(by_grade):
        print(f"  {grade}")
        for rel, target in sorted(by_grade[grade]):
            print(f"    {rel}  ->  {target or '(no target_grade)'}")

    stale = findings["stale"]
    print(f"\n## Stale ({len(stale)})")
    for rel, age, reasons in sorted(stale, key=lambda x: -x[1]):
        print(f"  {age:>3}d  {rel}  ({', '.join(reasons)})")

    integrity = findings["integrity"]
    print(f"\n## Grade-integrity ({len(integrity)})")
    for rel, grade, missing in sorted(integrity):
        print(f"  {rel}: claims grade `{grade}` but missing: {', '.join(missing)}")

    resolved = findings["resolved"]
    by_resolved_grade: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for rel, status, grade in resolved:
        by_resolved_grade[grade or "(no grade)"].append((status, rel))
    print(f"\n## Resolved (by grade) ({len(resolved)})")
    for grade in sorted(by_resolved_grade):
        print(f"  {grade}")
        for status, rel in sorted(by_resolved_grade[grade], key=lambda x: x[1]):
            print(f"    {rel}  [{status}]")

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Health report for an Obsidian vault (broken links, orphans, claims, graph)."
    )
    ap.add_argument(
        "--vault",
        help="vault root (default: $SMART_NOTES_VAULT, else nearest .obsidian ancestor, else cwd)",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="print a machine-readable summary block (for diffing batches)",
    )
    ap.add_argument(
        "--full",
        action="store_true",
        help="do not truncate broken-link / orphan / oversized lists",
    )
    ap.add_argument("--graph", action="store_true", help="graph connectivity report")
    ap.add_argument(
        "--claims", action="store_true", help="epistemic-status + staleness report"
    )
    ap.add_argument(
        "--claims-stale-days",
        type=int,
        default=GRADE_BINDING_MAX_AGE,
        help=f"staleness window for a pushed grade_binding check (default {GRADE_BINDING_MAX_AGE})",
    )
    ap.add_argument(
        "--digest", action="store_true", help="#digest review-frontier leak check"
    )
    ap.add_argument(
        "--digest-days", type=int, default=14, help="window for --digest (default 14)"
    )
    ap.add_argument(
        "--hypotheses",
        action="store_true",
        help="hypothesis-pipeline report: open queue, stale dossiers, grade-integrity",
    )
    ap.add_argument(
        "--hyp-stale-days",
        type=int,
        default=21,
        help="staleness window for --hypotheses (default 21)",
    )
    args = ap.parse_args()

    vault = find_vault(args.vault)
    if not vault.is_dir():
        print(f"vault not found: {vault}", file=sys.stderr)
        return 2

    if args.graph:
        return graph_report(vault)

    if args.claims:
        return claims_report(vault, args.claims_stale_days)

    if args.digest:
        return digest_report(vault, args.digest_days)

    if args.hypotheses:
        return hypotheses_report(vault, args.hyp_stale_days)

    all_files = list(iter_files(vault))
    md_files = [f for f in all_files if f.suffix.lower() == ".md"]

    # ---- build resolution indexes (all lowercased) --------------------------
    by_relpath: dict[str, Path] = {}  # "projects/x" and "projects/x.md"
    by_basename: dict[str, list[Path]] = {}  # "x" -> [paths] (md only)
    by_fullname: dict[str, list[Path]] = {}  # "x.png" -> [paths] (all files)
    for f in all_files:
        rel = norm(str(f.relative_to(vault)))
        by_relpath[rel] = f
        if rel.endswith(".md"):
            by_relpath[rel[:-3]] = f
        by_fullname.setdefault(f.name.lower(), []).append(f)
        if f.suffix.lower() == ".md":
            by_basename.setdefault(f.stem.lower(), []).append(f)

    # ---- scan notes ---------------------------------------------------------
    broken: list[tuple[str, int, str]] = []
    inbound: dict[Path, int] = {f: 0 for f in md_files}
    outbound: dict[Path, int] = {f: 0 for f in md_files}
    words: dict[Path, int] = {}
    path_links = filename_links = 0

    for f in md_files:
        text = f.read_text(encoding="utf-8", errors="replace")
        words[f] = len(text.split())
        in_fence = False
        for lineno, line in enumerate(text.splitlines(), 1):
            if FENCE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for _embed, raw in WIKILINK.findall(INLINE_CODE.sub("", line)):
                target = raw.split("|", 1)[0].split("#", 1)[0].strip()
                if not target:
                    continue
                outbound[f] += 1
                if "/" in target:
                    path_links += 1
                else:
                    filename_links += 1
                ok, hit = _resolve_link(target, by_relpath, by_basename, by_fullname)
                if ok:
                    if hit in inbound:
                        inbound[hit] += 1
                else:
                    broken.append((str(f.relative_to(vault)), lineno, target))

    # ---- derived views ------------------------------------------------------
    def is_quiet(f: Path) -> bool:
        rel = norm(str(f.relative_to(vault)))
        return any(h in rel for h in QUIET_ORPHAN_HINTS)

    orphans = [f for f in md_files if outbound[f] == 0 and inbound[f] == 0]
    idea_orphans = [f for f in orphans if not is_quiet(f)]
    oversized = [f for f in md_files if words[f] > OVERSIZED_WORDS and not is_quiet(f)]

    # version-duplicate clusters
    clusters: dict[str, list[Path]] = {}
    for f in md_files:
        m = VERSION_TOKEN.search(f.stem)
        if m:
            stem = VERSION_TOKEN.sub("", f.stem).strip(" _-")
            key = norm(str(f.parent.relative_to(vault)) + "/" + stem)
            clusters.setdefault(key, []).append(f)
    dup_clusters = {k: v for k, v in clusters.items() if len(v) > 1}

    wc = sorted(words.values())
    n = len(wc) or 1
    by_folder: dict[str, int] = {}
    for f in md_files:
        top = f.relative_to(vault).parts[0]
        by_folder[top] = by_folder.get(top, 0) + 1

    # ---- print report -------------------------------------------------------
    cap = None if args.full else 25
    p = print
    p(f"# vault-doctor: {vault}")
    p("")
    p("## Summary")
    p(f"- notes: {len(md_files)}   |   attachments: {len(all_files) - len(md_files)}")
    p(
        f"- words: total {sum(wc):,}   median {wc[n // 2]:,}   "
        f"p90 {wc[int(n * 0.9)]:,}   max {wc[-1]:,}"
    )
    p(
        f"- links: {path_links + filename_links} "
        f"({path_links} path-based, {filename_links} filename-only)"
    )
    p(f"- **broken links: {len(broken)}**")
    p(
        f"- orphans: {len(orphans)} total, **{len(idea_orphans)} idea-bearing** "
        f"(non-log/reference)"
    )
    p(f"- oversized idea notes (>{OVERSIZED_WORDS}w): {len(oversized)}")
    p(f"- version-duplicate clusters: {len(dup_clusters)}")
    p("")
    p("## Notes by top-level folder")
    for k, v in sorted(by_folder.items(), key=lambda kv: -kv[1]):
        p(f"- {v:>4}  {k}")

    def dump(title: str, items, fmt):
        p("")
        p(f"## {title} ({len(items)})")
        shown = items if cap is None else items[:cap]
        for it in shown:
            p(f"- {fmt(it)}")
        if cap is not None and len(items) > cap:
            p(f"- … +{len(items) - cap} more (use --full)")

    dump("Broken links", broken, lambda b: f"`{b[0]}:{b[1]}` → [[{b[2]}]]")
    dump(
        "Idea-bearing orphans (candidates to link or promote)",
        idea_orphans,
        lambda f: str(f.relative_to(vault)),
    )
    dump(
        "Oversized idea notes (candidates to split, only if idea, not log)",
        sorted(oversized, key=lambda f: -words[f]),
        lambda f: f"{words[f]:>6,}w  {f.relative_to(vault)}",
    )
    dump(
        "Version-duplicate clusters (archive superseded)",
        sorted(dup_clusters.items()),
        lambda kv: f"{kv[0]}  →  {', '.join(sorted(x.name for x in kv[1]))}",
    )

    if args.json:
        p("")
        p("## JSON")
        p(
            json.dumps(
                {
                    "notes": len(md_files),
                    "broken_links": len(broken),
                    "orphans_total": len(orphans),
                    "idea_orphans": len(idea_orphans),
                    "oversized": len(oversized),
                    "dup_clusters": len(dup_clusters),
                    "links_total": path_links + filename_links,
                },
                indent=2,
            )
        )

    # non-zero exit if broken links exist, so it can gate a batch in CI/scripts
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
