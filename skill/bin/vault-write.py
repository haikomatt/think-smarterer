#!/usr/bin/env python3
"""vault-write: concurrency-safe (compare-and-swap) atomic writer for vault notes.

Optimistic concurrency: you pass the sha256 you based your edit on; the write
succeeds only if the file on disk still has that sha. If another writer changed
it first, the write is refused (exit 3) so you can re-read and retry instead of
silently clobbering their change. Writes go via a temp file + atomic rename, so a
reader never sees a half-written note.

Read side (get the precondition hash; prints empty string if the file is absent):
    vault-write.py --print-sha PATH

Write side (new content on stdin):
    ... | vault-write.py PATH --expect-sha SHA     # safe update of existing file
    ... | vault-write.py PATH --expect-absent      # safe create of a new file
    ... | vault-write.py PATH --force              # last-writer-wins (discouraged)

Exit codes: 0 ok (including an idempotent no-op) · 2 usage/IO error ·
3 CONFLICT (sha mismatch, or file exists/absent when the opposite was required).

Note: there is a small time-of-check/time-of-use window between the CAS check and
the rename. For a cooperative, low-contention personal vault that window is tiny,
and git makes every state recoverable regardless, so CAS + git is sufficient
without a lock. Add flock only if real write contention shows up.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
from pathlib import Path


def sha256_of(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--print-sha", action="store_true",
                    help="print current sha256 (empty if absent) and exit")
    ap.add_argument("--expect-sha", help="require this current sha before writing")
    ap.add_argument("--expect-absent", action="store_true",
                    help="require the file NOT to exist before writing")
    ap.add_argument("--force", action="store_true",
                    help="write regardless of current state (last-writer-wins)")
    args = ap.parse_args()
    path = Path(args.path)

    if args.print_sha:
        print(sha256_of(path) or "")
        return 0

    current = sha256_of(path)  # None if absent

    # --- compare-and-swap precondition ---
    if not args.force:
        if args.expect_absent:
            if current is not None:
                print(f"CONFLICT: {path} already exists (sha {current})", file=sys.stderr)
                return 3
        elif args.expect_sha is not None:
            if current != args.expect_sha:
                print(f"CONFLICT: {path} changed under you (expected "
                      f"{args.expect_sha or 'absent'}, found {current or 'absent'}); "
                      f"re-read and retry", file=sys.stderr)
                return 3
        else:
            print("usage: pass --expect-sha SHA, --expect-absent, or --force",
                  file=sys.stderr)
            return 2

    data = sys.stdin.buffer.read()

    # idempotent no-op: identical content already on disk
    if current is not None and hashlib.sha256(data).hexdigest() == current:
        print(f"unchanged (idempotent) {path}")
        return 0

    # atomic write: temp file in the same dir, fsync, then replace
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".vw-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)  # atomic on POSIX
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    print(hashlib.sha256(data).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
