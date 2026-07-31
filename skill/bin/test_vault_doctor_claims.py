#!/usr/bin/env python3
"""Tests for vault-doctor --claims grade-binding invariant.

Self-contained: assert-based `test_*` functions plus a `__main__` runner that
prints PASS/FAIL and exits nonzero on any failure. Also pytest-collectable.
Imports the function under test from the sibling vault-doctor.py via importlib
(that file has no .py-importable name, hence the dashes).

Mostly pure-function tests: `_grade_binding_state(fm_block, today, stale_days)`
takes a raw frontmatter block, an injected reference date, and a staleness
horizon in days, with no filesystem, no temp vaults, no wall clock, for every
test above the integration test at the bottom. That last test is the one
exception: it builds a temp vault (same `_make_vault()` /
`tempfile.mkdtemp` / `shutil.rmtree` pattern as test_vault_doctor_hypotheses.py)
to exercise `claims_report()`'s actual display path end to end. The unit
tests above only ever assert on `_grade_binding_state`'s return value, so a
wiring bug in the report itself (wrong section, wrong filter, wrong label)
would otherwise be invisible: against a small vault the section always prints
count 0 by default, so nothing would otherwise exercise it.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import shutil
import tempfile
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("vault_doctor", HERE / "vault-doctor.py")
vault_doctor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vault_doctor)

REFERENCE_DATE = date(2026, 7, 31)
STALE_DAYS = 30

GRADE_BINDING = (
    "adapter-canary: >=1 known anchor event appears across any >=20-session "
    "batch (zero across the whole batch = dead parser, not a quiet corpus)"
)


def test_no_grade_binding_field_returns_none():
    # Strict no-op: a note with no grade_binding field at all must behave
    # exactly as today: every existing Permanent note has no such field.
    fm_block = """status: supported
grade: robust
target_grade: robust
type: permanent
created: 2026-07-01
"""
    result = vault_doctor._grade_binding_state(fm_block, REFERENCE_DATE, STALE_DAYS)
    assert result is None, f"expected None for absent grade_binding, got {result!r}"


def test_grade_binding_result_fail_is_broken():
    fm_block = f"""status: supported
grade: robust
target_grade: robust
type: permanent
created: 2026-07-01
grade_binding: "{GRADE_BINDING}"
grade_binding_result: fail
grade_binding_checked: 2026-07-30
"""
    result = vault_doctor._grade_binding_state(fm_block, REFERENCE_DATE, STALE_DAYS)
    assert result == "broken", (
        f"expected 'broken' for grade_binding_result: fail, got {result!r}"
    )


def test_pass_result_with_old_checked_date_is_stale():
    old_checked = (REFERENCE_DATE - timedelta(days=STALE_DAYS + 1)).isoformat()
    fm_block = f"""status: supported
grade: robust
target_grade: robust
type: permanent
created: 2026-01-01
grade_binding: "{GRADE_BINDING}"
grade_binding_result: pass
grade_binding_checked: {old_checked}
"""
    result = vault_doctor._grade_binding_state(fm_block, REFERENCE_DATE, STALE_DAYS)
    assert result == "stale", (
        f"expected 'stale' for pass result checked {STALE_DAYS + 1} days ago, got {result!r}"
    )


def test_grade_binding_present_but_never_checked_is_unverified():
    # grade_binding declared at grading time, but the owning system's
    # write-back hasn't landed yet: neither _result nor _checked has ever
    # been written.
    fm_block = f"""status: supported
grade: robust
target_grade: robust
type: permanent
created: 2026-07-01
grade_binding: "{GRADE_BINDING}"
"""
    result = vault_doctor._grade_binding_state(fm_block, REFERENCE_DATE, STALE_DAYS)
    assert result == "unverified", (
        f"expected 'unverified' for grade_binding with no result/checked, got {result!r}"
    )


def test_pass_result_with_fresh_checked_date_returns_none():
    fresh_checked = (REFERENCE_DATE - timedelta(days=1)).isoformat()
    fm_block = f"""status: supported
grade: robust
target_grade: robust
type: permanent
created: 2026-01-01
grade_binding: "{GRADE_BINDING}"
grade_binding_result: pass
grade_binding_checked: {fresh_checked}
"""
    result = vault_doctor._grade_binding_state(fm_block, REFERENCE_DATE, STALE_DAYS)
    assert result is None, f"expected None for fresh pass result, got {result!r}"


def test_checked_exactly_at_horizon_is_not_yet_stale():
    # Boundary pin: "stale" means strictly older than stale_days, not
    # older-than-or-equal-to. checked == today - stale_days must NOT be stale.
    boundary_checked = (REFERENCE_DATE - timedelta(days=STALE_DAYS)).isoformat()
    fm_block = f"""status: supported
grade: robust
target_grade: robust
type: permanent
created: 2026-01-01
grade_binding: "{GRADE_BINDING}"
grade_binding_result: pass
grade_binding_checked: {boundary_checked}
"""
    result = vault_doctor._grade_binding_state(fm_block, REFERENCE_DATE, STALE_DAYS)
    assert result is None, (
        f"expected None (not stale) for checked exactly {STALE_DAYS} days ago, got {result!r}"
    )


def test_fail_result_wins_over_stale_checked_date():
    # Precedence pin: "broken" beats "stale". A known failure is strictly
    # worse news than an overdue re-check, so a fail result must report
    # "broken" even when grade_binding_checked is itself far past the
    # staleness horizon: staleness is only a meaningful question once the
    # last known result was a pass.
    old_checked = (REFERENCE_DATE - timedelta(days=STALE_DAYS + 40)).isoformat()
    fm_block = f"""status: supported
grade: robust
target_grade: robust
type: permanent
created: 2026-01-01
grade_binding: "{GRADE_BINDING}"
grade_binding_result: fail
grade_binding_checked: {old_checked}
"""
    result = vault_doctor._grade_binding_state(fm_block, REFERENCE_DATE, STALE_DAYS)
    assert result == "broken", (
        f"expected 'broken' to win over 'stale' when result is fail, got {result!r}"
    )


def test_partial_writeback_result_only_is_unverified():
    # The owning system writes grade_binding_result and grade_binding_checked
    # together, but not necessarily as one atomic CAS write: a session crash
    # or a lost race between the two field writes can leave only one landed.
    # A result with no checked date is a half-landed write, not a
    # trustworthy verification, so it must read as unverified rather than
    # being taken at face value.
    fm_block = f"""status: supported
grade: robust
target_grade: robust
type: permanent
created: 2026-01-01
grade_binding: "{GRADE_BINDING}"
grade_binding_result: pass
"""
    result = vault_doctor._grade_binding_state(fm_block, REFERENCE_DATE, STALE_DAYS)
    assert result == "unverified", (
        f"expected 'unverified' for grade_binding_result with no _checked, got {result!r}"
    )


def test_partial_writeback_checked_only_is_unverified():
    # Mirror of the above in the other direction: a checked date with no
    # result is equally a half-landed write and must not be trusted: there
    # is no result to trust in the first place, pass or fail.
    fresh_checked = (REFERENCE_DATE - timedelta(days=1)).isoformat()
    fm_block = f"""status: supported
grade: robust
target_grade: robust
type: permanent
created: 2026-01-01
grade_binding: "{GRADE_BINDING}"
grade_binding_checked: {fresh_checked}
"""
    result = vault_doctor._grade_binding_state(fm_block, REFERENCE_DATE, STALE_DAYS)
    assert result == "unverified", (
        f"expected 'unverified' for grade_binding_checked with no _result, got {result!r}"
    )


def _fm_with_result(result_value: str, checked: str) -> str:
    return f"""status: supported
grade: robust
target_grade: robust
type: permanent
created: 2026-01-01
grade_binding: "{GRADE_BINDING}"
grade_binding_result: {result_value}
grade_binding_checked: {checked}
"""


def test_uppercase_fail_variants_are_broken():
    # Actual reported defect: the writer is an external system in another
    # repo whose result-string casing nothing on this side enforces.
    # Comparing with == "fail" fails open on "Fail"/"FAIL": it falls through
    # every branch and silently returns None, i.e. reports no problem for a
    # note whose invariant actually broke. Case-insensitive comparison
    # (after stripping whitespace) closes that gap.
    fresh_checked = (REFERENCE_DATE - timedelta(days=1)).isoformat()
    for result_value in ("Fail", "FAIL"):
        fm_block = _fm_with_result(result_value, fresh_checked)
        result = vault_doctor._grade_binding_state(fm_block, REFERENCE_DATE, STALE_DAYS)
        assert result == "broken", (
            f"expected 'broken' for grade_binding_result: {result_value!r} "
            f"(case-insensitive fail), got {result!r}"
        )


def test_uppercase_pass_with_fresh_checked_returns_none():
    # Case-insensitivity must apply on the pass/staleness path too, not just
    # the fail path: the writer's casing convention is unenforced either way.
    fresh_checked = (REFERENCE_DATE - timedelta(days=1)).isoformat()
    fm_block = _fm_with_result("PASS", fresh_checked)
    result = vault_doctor._grade_binding_state(fm_block, REFERENCE_DATE, STALE_DAYS)
    assert result is None, (
        f"expected None for grade_binding_result: PASS (fresh), got {result!r}"
    )


def test_uppercase_pass_with_old_checked_is_stale():
    # Same case-insensitivity requirement, on the stale branch specifically:
    # "Pass" past the horizon must still reach "stale", not fall through to
    # unverified or None just because the literal string isn't lowercase.
    old_checked = (REFERENCE_DATE - timedelta(days=STALE_DAYS + 1)).isoformat()
    fm_block = _fm_with_result("Pass", old_checked)
    result = vault_doctor._grade_binding_state(fm_block, REFERENCE_DATE, STALE_DAYS)
    assert result == "stale", (
        f"expected 'stale' for grade_binding_result: Pass (old), got {result!r}"
    )


def test_unrecognised_result_values_are_unverified():
    # A result value that is present but not recognisably pass or fail is not
    # a verification at all. "passed" is the nasty case: it reads like a
    # pass to a human skimming frontmatter, but a strict/case-insensitive
    # match against "pass" correctly rejects it: the safe direction here is
    # to ask a human (unverified), never to silently claim clean (None) or to
    # claim a failure we have no evidence of ("broken").
    fresh_checked = (REFERENCE_DATE - timedelta(days=1)).isoformat()
    for result_value in ("error", "passed"):
        fm_block = _fm_with_result(result_value, fresh_checked)
        result = vault_doctor._grade_binding_state(fm_block, REFERENCE_DATE, STALE_DAYS)
        assert result == "unverified", (
            f"expected 'unverified' for unrecognised grade_binding_result: "
            f"{result_value!r}, got {result!r}"
        )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_claims_vault(stale_days: int) -> Path:
    """Temp vault exercising claims_report()'s grade-binding section end to end.

    claims_report() itself calls date.today() internally (unlike
    _grade_binding_state, its date isn't injectable), so these fixtures are
    built relative to the real today rather than a fixed REFERENCE_DATE.
    """
    vault = Path(tempfile.mkdtemp(prefix="vault-doctor-claims-"))
    (vault / ".obsidian").mkdir()
    today = date.today()
    old_checked = (today - timedelta(days=stale_days + 5)).isoformat()
    fresh_checked = (today - timedelta(days=1)).isoformat()

    # broken: pushed result disagrees outright.
    _write(vault / "Permanent" / "broken-grade-binding-note.md", f"""---
status: supported
grade: robust
type: permanent
created: 2026-07-01
grade_binding: "{GRADE_BINDING}"
grade_binding_result: fail
grade_binding_checked: {fresh_checked}
---

# A note whose grade-binding check came back failing

Body text, not exercised by this report.
""")

    # stale: last known result was a pass, but it's overdue for re-check.
    _write(vault / "Permanent" / "stale-grade-binding-note.md", f"""---
status: supported
grade: robust
type: permanent
created: 2026-01-01
grade_binding: "{GRADE_BINDING}"
grade_binding_result: pass
grade_binding_checked: {old_checked}
---

# A note whose grade-binding check is overdue for re-verification

Body text, not exercised by this report.
""")

    # unverified: declared at grading time, write-back never landed.
    _write(vault / "Permanent" / "unverified-grade-binding-note.md", f"""---
status: supported
grade: robust
type: permanent
created: 2026-07-01
grade_binding: "{GRADE_BINDING}"
---

# A note with a declared grade-binding invariant never checked

Body text, not exercised by this report.
""")

    # clean: bound, checked, passing, fresh: must NOT appear in the section.
    _write(vault / "Permanent" / "clean-grade-binding-note.md", f"""---
status: supported
grade: robust
type: permanent
created: 2026-07-01
grade_binding: "{GRADE_BINDING}"
grade_binding_result: pass
grade_binding_checked: {fresh_checked}
---

# A note whose grade-binding check is passing and fresh

Body text, not exercised by this report.
""")

    # unbound: no grade_binding field at all: the common case, strict no-op.
    _write(vault / "Permanent" / "plain-note-no-grade-binding.md", """---
status: supported
grade: robust
type: permanent
created: 2026-07-01
---

# A plain permanent note with no grade-binding invariant declared

Body text, not exercised by this report.
""")

    return vault


def _grade_binding_section_items(output: str) -> list[str]:
    """Indented item lines from the '## Grade-binding invariant...' dump()
    block: the section is claims_report()'s last dump() call, so it runs to
    the end of the captured output."""
    idx = output.index("## Grade-binding invariant")
    lines = output[idx:].splitlines()[1:]
    items = []
    for line in lines:
        if line.startswith("## "):
            break
        if line.strip():
            items.append(line.strip())
    return items


def test_claims_report_grade_binding_section_against_real_vault():
    stale_days = STALE_DAYS
    vault = _make_claims_vault(stale_days)
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exit_code = vault_doctor.claims_report(vault, stale_days)
        # Advisory only, by explicit product decision: a broken/stale/
        # unverified grade-binding invariant must never change
        # claims_report's exit code.
        assert exit_code == 0, (
            f"expected claims_report to always exit 0 (advisory), got {exit_code!r}"
        )

        items = _grade_binding_section_items(buf.getvalue())
        assert len(items) == 3, f"expected exactly 3 flagged notes, got {items!r}"
        assert "[broken] Permanent/broken-grade-binding-note.md" in items
        assert "[stale] Permanent/stale-grade-binding-note.md" in items
        assert "[unverified] Permanent/unverified-grade-binding-note.md" in items
        joined = "\n".join(items)
        assert "clean-grade-binding-note.md" not in joined, (
            "a passing, fresh grade_binding check must not appear in the section"
        )
        assert "plain-note-no-grade-binding.md" not in joined, (
            "a note with no grade_binding field at all must not appear in the section"
        )
    finally:
        shutil.rmtree(vault)


def _run_all() -> int:
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith("test_") and callable(fn)]
    failures = []
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except AssertionError as e:
            print(f"FAIL {name}: {e}")
            failures.append(name)
        except Exception as e:  # noqa: BLE001 - surface any import/runtime error as a failure
            print(f"ERROR {name}: {e!r}")
            failures.append(name)
    print(f"\n{len(tests) - len(failures)}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
