#!/usr/bin/env python3
"""vault-outbox: durable write-ahead queue + retry drainer for vault writes.

Solves the "rejected write dies with the session" problem. The moment a session
produces vault-bound content it ENQUEUEs it here: to durable, uncontended storage
(~/.claude/vault-outbox by default; override with VAULT_OUTBOX, e.g.
~/.cursor/vault-outbox for Cursor — NOT the volatile/contended vault). Later, DRAIN applies
pending entries to the vault via compare-and-swap and commits them to git. Because
entries live on durable storage, closing a session never loses them; the next
drain retries. Applies are idempotent, and a write whose base no longer matches is
moved to conflict/ (never dropped, never clobbered).

Store layout (default ~/.claude/vault-outbox; set VAULT_OUTBOX to relocate):
    pending/   entries awaiting apply
    applied/   successfully written to the vault
    conflict/  base changed under us: needs a human/AI merge

Commands:
    # persist-on-generate (durable immediately):
    vault-outbox.py enqueue --target Permanent/foo.md --new           < content
    vault-outbox.py enqueue --target plan.md --base-sha <SHA>         < content
    # retry loop (safe to run anytime; per-file CAS, no whole-vault lock needed):
    vault-outbox.py drain --vault ~/vault --commit
    vault-outbox.py status
    vault-outbox.py show <id>
    # retire conflicts the vault already satisfies (also run at the top of drain):
    vault-outbox.py reconcile --vault ~/vault

Exit: 0 ok · 1 drain finished with conflicts · 2 usage/IO.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

STORE = Path(os.environ.get("VAULT_OUTBOX", Path.home() / ".claude" / "vault-outbox"))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".vw-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _dirs():
    for sub in ("pending", "applied", "conflict"):
        (STORE / sub).mkdir(parents=True, exist_ok=True)
    return STORE / "pending", STORE / "applied", STORE / "conflict"


def enqueue(args) -> int:
    pending, _, _ = _dirs()
    content = sys.stdin.buffer.read()
    if args.new and args.base_sha:
        print("use either --new or --base-sha, not both", file=sys.stderr)
        return 2
    entry = {
        "id": f"{_now()}-{uuid.uuid4().hex[:8]}",
        "target": args.target,
        "expect": "absent" if args.new else "sha",
        "base_sha": None if args.new else args.base_sha,
        "content_sha": hashlib.sha256(content).hexdigest(),
        "content": content.decode("utf-8", errors="surrogateescape"),
        "created": datetime.now(timezone.utc).isoformat(),
        "note": args.note or "",
    }
    if entry["expect"] == "sha" and entry["base_sha"] is None:
        print("need --base-sha <SHA> (or --new for a new file)", file=sys.stderr)
        return 2
    out = pending / f"{entry['id']}.json"
    _atomic_write(out, json.dumps(entry, indent=2).encode())
    print(entry["id"])
    return 0


def _apply(entry: dict, vault: Path) -> str:
    target = vault / entry["target"]
    cur = _sha(target)
    data = entry["content"].encode("utf-8", errors="surrogateescape")
    csha = hashlib.sha256(data).hexdigest()
    if cur == csha:
        return "applied"  # already there (idempotent)
    if entry["expect"] == "absent":
        if cur is None:
            _atomic_write(target, data)
            return "applied"
        return "conflict"  # exists with different content
    # expect sha
    if cur == entry["base_sha"]:
        _atomic_write(target, data)
        return "applied"
    return "conflict"  # base changed under us


def _reconcile_conflicts(
    vault: Path, applied_dir: Path, conflict_dir: Path
) -> list[str]:
    """Retire conflict entries that are now no-ops: the on-disk file already
    matches the entry's content (another writer produced the same bytes, e.g. a
    double-promotion of the same note). Provably safe: nothing is written, the
    redundant entry is moved to applied/. Genuine conflicts, where the on-disk
    content still differs, are left untouched for a human/AI merge.
    """
    resolved = []
    for f in sorted(conflict_dir.glob("*.json")):
        try:
            entry = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if (
            entry.get("content_sha")
            and _sha(vault / entry["target"]) == entry["content_sha"]
        ):
            try:
                os.replace(f, applied_dir / f.name)
            except FileNotFoundError:
                continue  # another drainer grabbed it, fine
            resolved.append(entry["target"])
    return resolved


def reconcile(args) -> int:
    _, applied_dir, conflict_dir = _dirs()
    vault = Path(args.vault).expanduser().resolve()
    resolved = _reconcile_conflicts(vault, applied_dir, conflict_dir)
    for t in resolved:
        print(f"  resolved  {t}  (on-disk already matches; redundant conflict retired)")
    print(f"reconcile: {len(resolved)} redundant conflict(s) retired")
    return 0


def drain(args) -> int:
    pending, applied_dir, conflict_dir = _dirs()
    vault = Path(args.vault).expanduser().resolve()
    for t in _reconcile_conflicts(vault, applied_dir, conflict_dir):
        print(f"  resolved  {t}  (on-disk already matches; redundant conflict retired)")
    applied_targets, conflicts = [], []
    for f in sorted(pending.glob("*.json")):
        entry = json.loads(f.read_text())
        result = _apply(entry, vault)
        dest = (applied_dir if result == "applied" else conflict_dir) / f.name
        os.replace(f, dest)
        if result == "applied":
            applied_targets.append(entry["target"])
            print(f"  applied  {entry['target']}")
        else:
            conflicts.append(entry["target"])
            print(
                f"  CONFLICT {entry['target']}  (base changed; entry kept in "
                f"conflict/{f.name})",
                file=sys.stderr,
            )

    if args.commit and applied_targets and (vault / ".git").exists():
        # stage ONLY the drained files, so a commit never sweeps up other
        # sessions' unrelated uncommitted work
        subprocess.run(["git", "-C", str(vault), "add", *applied_targets], check=False)
        msg = args.message or f"vault-outbox: drain {len(applied_targets)} note(s)"
        r = subprocess.run(
            ["git", "-C", str(vault), "commit", "-q", "-m", msg],
            capture_output=True,
            text=True,
        )
        print(
            f"  committed {len(applied_targets)} file(s)"
            if r.returncode == 0
            else f"  git commit: {r.stderr.strip() or 'nothing to commit'}"
        )

    print(f"drain: {len(applied_targets)} applied, {len(conflicts)} conflict(s)")
    return 1 if conflicts else 0


def status(args) -> int:
    pending, applied_dir, conflict_dir = _dirs()
    p = sorted(pending.glob("*.json"))
    print(f"outbox: {STORE}")
    print(f"  pending:  {len(p)}")
    print(f"  applied:  {len(list(applied_dir.glob('*.json')))}")
    print(f"  conflict: {len(list(conflict_dir.glob('*.json')))}")
    for f in p:
        e = json.loads(f.read_text())
        print(f"    PENDING  {e['target']:<50} {e['created']}  ({e['id']})")
    for f in sorted(conflict_dir.glob("*.json")):
        e = json.loads(f.read_text())
        print(f"    CONFLICT {e['target']:<50} {e['created']}  ({e['id']})")
    return 0


def show(args) -> int:
    for sub in ("pending", "applied", "conflict"):
        for f in (STORE / sub).glob(f"*{args.id}*.json"):
            print(f.read_text())
            return 0
    print(f"no entry matching {args.id}", file=sys.stderr)
    return 2


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("enqueue")
    e.set_defaults(fn=enqueue)
    e.add_argument("--target", required=True, help="vault-relative path")
    e.add_argument("--base-sha", help="sha the edit was based on (existing file)")
    e.add_argument("--new", action="store_true", help="target must not yet exist")
    e.add_argument("--note", help="optional human note")
    d = sub.add_parser("drain")
    d.set_defaults(fn=drain)
    d.add_argument("--vault", required=True)
    d.add_argument("--commit", action="store_true", help="git-commit applied files")
    d.add_argument("--message", help="commit message")
    s = sub.add_parser("status")
    s.set_defaults(fn=status)
    rc = sub.add_parser("reconcile")
    rc.set_defaults(fn=reconcile)
    rc.add_argument("--vault", required=True)
    sh = sub.add_parser("show")
    sh.set_defaults(fn=show)
    sh.add_argument("id")
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
