#!/usr/bin/env python3
"""vault-grade-record: record a pass/fail grade-binding verdict onto a note.

The write half of grade-binding (see vault-doctor.py's `_grade_binding_state`
for the read half). A human runs an external experiment on their own time,
then records the outcome here. This tool never discovers, matches, or runs
anything itself -- it only splices two frontmatter fields onto a note that
already declares a `grade_binding`.

Usage:
    vault-grade-record.py <note-path> --result pass|fail [--today YYYY-MM-DD]

Writes are compare-and-swap via the sibling vault-write.py (never a blind
overwrite): reads the note, computes its sha256, splices in memory, then
hands the new text to vault-write.py with --expect-sha. A CAS conflict (the
note changed under you) is surfaced as a retryable error, never --force'd.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from datetime import date
from pathlib import Path

VALID_RESULTS = ("pass", "fail")

FENCE_MARKER = "---"


def _fence_closing_index(lines: list[str]) -> int:
    """Return the index of the leading fence's own closing '---' line.

    `lines` must be `text.splitlines(keepends=True)`. Raises ValueError if
    `lines[0]` is not itself a `---` fence-opening line, or no closing `---`
    line is found afterward. Scans line-by-line (never a single regex over
    the whole document) so a `---` horizontal rule or a field-lookalike line
    in the BODY is never mistaken for the fence.
    """
    if not lines or lines[0].rstrip("\r\n") != FENCE_MARKER:
        raise ValueError("text has no leading '---' frontmatter fence")

    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == FENCE_MARKER:
            return i

    raise ValueError("text has no closing '---' for the leading frontmatter fence")


def set_grade_binding_result(text: str, result: str, checked: date) -> str:
    """Byte-preserving splice of grade_binding_result/_checked into frontmatter.

    - `result` must be one of "pass" or "fail"; anything else raises
      ValueError.
    - `text` must have a leading `---`-delimited YAML frontmatter fence; if
      it does not, raise ValueError.
    - Sets two fields inside the leading frontmatter fence only:
      `grade_binding_result: <result>` and
      `grade_binding_checked: <checked.isoformat()>` (YYYY-MM-DD).
    - If a field is already present in the fence, replace its line in place
      (same position). If a field is absent, append a new line for it
      immediately before the closing `---` fence line (i.e. at the current
      end of the frontmatter block). When both are absent, they are
      appended in canonical order: `grade_binding_result` first, then
      `grade_binding_checked`. When only one is absent, only that field's
      line is appended at the end -- its position relative to the other,
      already-present field is not otherwise adjusted.
    - Every other frontmatter line, the entire body, and the trailing-
      newline state of `text` (present or absent) are preserved exactly.
    - Line-oriented string edit only, never a YAML round-trip. Idempotent.
    """
    if result not in VALID_RESULTS:
        raise ValueError(f"result must be one of {VALID_RESULTS!r}, got {result!r}")

    lines = text.splitlines(keepends=True)
    closing_idx = _fence_closing_index(lines)

    new_values = (
        ("grade_binding_result", result),
        ("grade_binding_checked", checked.isoformat()),
    )

    for field, value in new_values:
        prefix = f"{field}:"
        new_line = f"{field}: {value}\n"
        found_idx = None
        for i in range(1, closing_idx):
            if lines[i].startswith(prefix):
                found_idx = i
                break
        if found_idx is not None:
            lines[found_idx] = new_line
        else:
            lines.insert(closing_idx, new_line)
            closing_idx += 1

    return "".join(lines)


def record_verdict(text: str, result: str, checked: date) -> str:
    """Record a verdict on a note that already declares a `grade_binding`.

    Looks for a `grade_binding` field scoped strictly to the note's leading
    `---` frontmatter fence (never the body). Detection is line-based
    (newline-safe): an empty `grade_binding:` value can't bleed into
    matching a later line, since each fence line is checked independently.
    If no `grade_binding` field is present in the fence, raises ValueError:
    there is nothing to verify, so recording a verdict is refused. Otherwise
    delegates to `set_grade_binding_result(text, result, checked)`.
    """
    lines = text.splitlines(keepends=True)
    closing_idx = _fence_closing_index(lines)

    has_binding = any(
        lines[i].startswith("grade_binding:") for i in range(1, closing_idx)
    )
    if not has_binding:
        raise ValueError(
            "note has no grade_binding field; nothing to verify, refusing to record"
        )

    return set_grade_binding_result(text, result, checked)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vault-grade-record.py",
        description="Record a pass/fail grade-binding verdict onto an already-bound note.",
    )
    parser.add_argument("note_path", help="path to the note to update")
    parser.add_argument(
        "--result", required=True, choices=list(VALID_RESULTS), help="verdict to record"
    )
    parser.add_argument(
        "--today",
        default=None,
        help="override today's date as YYYY-MM-DD (default: the real date)",
    )
    args = parser.parse_args(argv)

    checked = date.fromisoformat(args.today) if args.today else date.today()
    note_path = Path(args.note_path)

    try:
        raw = note_path.read_bytes()
    except OSError as e:
        print(f"error: cannot read {note_path}: {e}", file=sys.stderr)
        return 2

    base_sha = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8")

    try:
        new_text = record_verdict(text, args.result, checked)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    vault_write = Path(__file__).resolve().parent / "vault-write.py"
    proc = subprocess.run(
        [sys.executable, str(vault_write), "--expect-sha", base_sha, str(note_path)],
        input=new_text.encode("utf-8"),
        capture_output=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr.decode("utf-8", errors="replace"))
        print(
            f"error: could not write {note_path} (CAS conflict -- the note "
            "changed under you); re-read and re-run to retry",
            file=sys.stderr,
        )
        return proc.returncode

    print(
        f"recorded grade_binding_result={args.result} grade_binding_checked={checked.isoformat()} on {note_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
