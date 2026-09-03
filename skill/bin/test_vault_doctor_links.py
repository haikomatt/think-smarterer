#!/usr/bin/env python3
"""Tests for vault-doctor broken-link resolution.

Covers two defects found on a live vault:
  1. an alias pipe escaped as `\\|` (required inside a markdown table) left a
     trailing backslash on the target, so the link never resolved;
  2. `_meta` was pruned before the resolution index was built, so a content
     note linking to a real `_meta/` note was reported broken.

Plus regressions: `_meta` must still be excluded from the scanned note set,
and genuinely dangling links must still be reported.

Self-contained: assert-based `test_*` functions plus a `__main__` runner that
prints PASS/FAIL and exits nonzero on any failure. Also pytest-collectable.
Drives the script end to end via subprocess, since the default report is built
inline in main() rather than exposed as a function.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCTOR = HERE / "vault-doctor.py"

BROKEN_LINE = re.compile(r"^- `([^`]+):(\d+)` → \[\[(.+)\]\]$")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_vault() -> Path:
    vault = Path(tempfile.mkdtemp(prefix="vault-doctor-links-"))
    (vault / ".obsidian").mkdir()

    _write(vault / "Permanent" / "target-note.md", "# Target\n\nBody.\n")
    _write(vault / "_meta" / "some-plan.md", "# Some plan\n\nTooling doc.\n")

    # 1. escaped alias pipe inside a table, and 5. plain alias + heading forms
    _write(
        vault / "Projects" / "uses-links.md",
        """# Uses links

| Thing | Where |
|---|---|
| Escaped alias in a table | [[target-note\\|Nice Name]] |

Plain alias: [[target-note|Nice Name]]
Heading link: [[target-note#Body]]
Bare link: [[target-note]]
""",
    )

    # 2. a content note pointing at a real _meta note
    _write(
        vault / "Literature" / "cites-meta.md",
        "# Cites meta\n\n## Feeds\n- [[some-plan]] carries the schema change\n",
    )

    # 3. a report inside _meta whose own links dangle: must not be scanned
    _write(
        vault / "_meta" / "old-report.md",
        "# Old report\n\n- broken once: [[definitely-missing-xyz]]\n",
    )

    # 4. a genuinely dangling link in content
    _write(
        vault / "Projects" / "really-broken.md",
        "# Really broken\n\nSee [[no-such-note-anywhere]].\n",
    )
    return vault


def _run(vault: Path) -> str:
    proc = subprocess.run(
        [sys.executable, str(DOCTOR), "--vault", str(vault), "--full"],
        capture_output=True,
        text=True,
    )
    return proc.stdout


def _broken(out: str) -> list[tuple[str, str]]:
    """Return [(relpath, target)] parsed from the Broken links section."""
    found, in_section = [], False
    for line in out.splitlines():
        if line.startswith("## Broken links"):
            in_section = True
            continue
        if in_section:
            if line.startswith("## "):
                break
            m = BROKEN_LINE.match(line.strip())
            if m:
                found.append((m.group(1), m.group(3)))
    return found


def test_escaped_alias_pipe_in_table_resolves() -> None:
    broken = _broken(_run(_make_vault()))
    offenders = [t for _p, t in broken if "target-note" in t]
    assert not offenders, f"escaped-pipe alias reported broken: {offenders}"


def test_link_into_meta_resolves() -> None:
    broken = _broken(_run(_make_vault()))
    offenders = [t for _p, t in broken if t == "some-plan"]
    assert not offenders, "link to a real _meta/ note reported broken"


def test_meta_notes_are_not_scanned() -> None:
    out = _run(_make_vault())
    broken = _broken(out)
    assert not [p for p, _t in broken if p.startswith("_meta")], (
        "links inside _meta/ must not be scanned"
    )
    assert not [t for _p, t in broken if t == "definitely-missing-xyz"], (
        "a dangling link inside a _meta report must not be reported"
    )
    # 4 content notes; the two _meta notes must not count toward the total
    m = re.search(r"- notes: (\d+)", out)
    assert m and int(m.group(1)) == 4, (
        f"expected 4 content notes, got {m and m.group(1)}"
    )


def test_genuinely_broken_link_still_reported() -> None:
    broken = _broken(_run(_make_vault()))
    assert [t for _p, t in broken if t == "no-such-note-anywhere"], (
        "a real dangling link must still be reported"
    )


def test_plain_alias_and_heading_still_resolve() -> None:
    """Guard the fix against over-reaching: normal alias/heading links."""
    vault = Path(tempfile.mkdtemp(prefix="vault-doctor-links-plain-"))
    (vault / ".obsidian").mkdir()
    _write(vault / "a.md", "# A\n\n## Body\n")
    _write(vault / "b.md", "[[a|Alias]] and [[a#Body]] and [[a]]\n")
    assert not _broken(_run(vault)), "plain alias/heading links must resolve"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except AssertionError as e:
                failures += 1
                print(f"FAIL  {name}: {e}")
    print(f"\n{failures} failure(s)")
    raise SystemExit(1 if failures else 0)
