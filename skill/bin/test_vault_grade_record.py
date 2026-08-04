#!/usr/bin/env python3
"""Tests for vault-grade-record (the grade-binding verdict-recording splice).

Self-contained: assert-based `test_*` functions plus a `__main__` runner that
prints PASS/FAIL and exits nonzero on any failure. Also pytest-collectable.
Imports the functions under test from the sibling vault-grade-record.py via
importlib (that file has no .py-importable name, hence the dashes).

Pure string tests: no filesystem, no temp vaults, no wall clock -- `checked`
is always injected as an explicit `date`.
"""

from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "vault_grade_record", HERE / "vault-grade-record.py"
)
vault_grade_record = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vault_grade_record)

REFERENCE_DATE = date(2026, 8, 4)


# --- set_grade_binding_result ------------------------------------------------


def test_insert_both_fields_when_absent():
    text = (
        "---\n"
        'title: "Example note"\n'
        "status: hypothesis\n"
        "---\n"
        "\n"
        "# Heading\n"
        "\n"
        "Body text unaffected.\n"
    )
    result = vault_grade_record.set_grade_binding_result(text, "pass", REFERENCE_DATE)
    expected = (
        "---\n"
        'title: "Example note"\n'
        "status: hypothesis\n"
        "grade_binding_result: pass\n"
        "grade_binding_checked: 2026-08-04\n"
        "---\n"
        "\n"
        "# Heading\n"
        "\n"
        "Body text unaffected.\n"
    )
    assert result == expected, result


def test_replace_both_fields_in_place_when_present():
    text = (
        "---\n"
        'title: "Example note"\n'
        'grade_binding: "external checker stays green"\n'
        "grade_binding_result: fail\n"
        "grade_binding_checked: 2026-01-01\n"
        "status: hypothesis\n"
        "---\n"
        "\n"
        "Body text.\n"
    )
    result = vault_grade_record.set_grade_binding_result(text, "pass", REFERENCE_DATE)
    expected = (
        "---\n"
        'title: "Example note"\n'
        'grade_binding: "external checker stays green"\n'
        "grade_binding_result: pass\n"
        "grade_binding_checked: 2026-08-04\n"
        "status: hypothesis\n"
        "---\n"
        "\n"
        "Body text.\n"
    )
    assert result == expected, result


def test_one_field_present_one_absent_result_present():
    # grade_binding_result already present, grade_binding_checked absent ->
    # result replaced in place, checked appended at the end of the fence.
    text = (
        "---\n"
        'grade_binding: "x"\n'
        "grade_binding_result: fail\n"
        "status: hypothesis\n"
        "---\n"
        "\n"
        "Body.\n"
    )
    result = vault_grade_record.set_grade_binding_result(text, "pass", REFERENCE_DATE)
    expected = (
        "---\n"
        'grade_binding: "x"\n'
        "grade_binding_result: pass\n"
        "status: hypothesis\n"
        "grade_binding_checked: 2026-08-04\n"
        "---\n"
        "\n"
        "Body.\n"
    )
    assert result == expected, result
    assert result.count("grade_binding_result:") == 1, result
    assert result.count("grade_binding_checked:") == 1, result


def test_one_field_present_one_absent_checked_present():
    # grade_binding_checked already present, grade_binding_result absent ->
    # checked replaced in place, result appended at the end of the fence.
    text = (
        "---\n"
        'grade_binding: "x"\n'
        "grade_binding_checked: 2026-01-01\n"
        "status: hypothesis\n"
        "---\n"
        "\n"
        "Body.\n"
    )
    result = vault_grade_record.set_grade_binding_result(text, "pass", REFERENCE_DATE)
    expected = (
        "---\n"
        'grade_binding: "x"\n'
        "grade_binding_checked: 2026-08-04\n"
        "status: hypothesis\n"
        "grade_binding_result: pass\n"
        "---\n"
        "\n"
        "Body.\n"
    )
    assert result == expected, result
    assert result.count("grade_binding_result:") == 1, result
    assert result.count("grade_binding_checked:") == 1, result


def test_idempotent_apply_twice_equals_apply_once():
    text = '---\ntitle: "Example note"\nstatus: hypothesis\n---\n\nBody text.\n'
    once = vault_grade_record.set_grade_binding_result(text, "pass", REFERENCE_DATE)
    twice = vault_grade_record.set_grade_binding_result(once, "pass", REFERENCE_DATE)
    assert twice == once, (once, twice)


def test_body_lookalikes_untouched():
    # The body contains a line that looks exactly like a frontmatter field,
    # plus a '---' horizontal rule. Only the leading fence may be touched.
    text = (
        "---\n"
        'title: "Example note"\n'
        "status: hypothesis\n"
        "---\n"
        "\n"
        "# Notes\n"
        "\n"
        "grade_binding_result: something\n"
        "\n"
        "---\n"
        "\n"
        "More body after a horizontal rule.\n"
    )
    result = vault_grade_record.set_grade_binding_result(text, "pass", REFERENCE_DATE)
    expected = (
        "---\n"
        'title: "Example note"\n'
        "status: hypothesis\n"
        "grade_binding_result: pass\n"
        "grade_binding_checked: 2026-08-04\n"
        "---\n"
        "\n"
        "# Notes\n"
        "\n"
        "grade_binding_result: something\n"
        "\n"
        "---\n"
        "\n"
        "More body after a horizontal rule.\n"
    )
    assert result == expected, result
    assert result.count("grade_binding_result: something") == 1, result
    assert result.count("grade_binding_result: pass") == 1, result


def test_trailing_newline_preserved_when_present():
    text = "---\nstatus: hypothesis\n---\n\nBody.\n"
    result = vault_grade_record.set_grade_binding_result(text, "pass", REFERENCE_DATE)
    expected = (
        "---\n"
        "status: hypothesis\n"
        "grade_binding_result: pass\n"
        "grade_binding_checked: 2026-08-04\n"
        "---\n"
        "\n"
        "Body.\n"
    )
    assert result == expected, repr(result)


def test_trailing_newline_preserved_when_absent():
    text = "---\nstatus: hypothesis\n---\n\nBody."
    result = vault_grade_record.set_grade_binding_result(text, "pass", REFERENCE_DATE)
    expected = (
        "---\n"
        "status: hypothesis\n"
        "grade_binding_result: pass\n"
        "grade_binding_checked: 2026-08-04\n"
        "---\n"
        "\n"
        "Body."
    )
    assert result == expected, repr(result)


def test_bad_result_raises_value_error():
    text = "---\nstatus: hypothesis\n---\n\nBody.\n"
    raised = None
    try:
        vault_grade_record.set_grade_binding_result(text, "error", REFERENCE_DATE)
    except Exception as e:  # noqa: BLE001 - we assert the type below
        raised = e
    assert isinstance(raised, ValueError), f"expected ValueError, got {raised!r}"


def test_no_frontmatter_fence_raises_value_error():
    text = "# Just a heading\n\nNo frontmatter here.\n"
    raised = None
    try:
        vault_grade_record.set_grade_binding_result(text, "pass", REFERENCE_DATE)
    except Exception as e:  # noqa: BLE001 - we assert the type below
        raised = e
    assert isinstance(raised, ValueError), f"expected ValueError, got {raised!r}"


def test_checked_date_renders_iso_format():
    text = "---\nstatus: hypothesis\n---\n\nBody.\n"
    result = vault_grade_record.set_grade_binding_result(text, "pass", date(2026, 8, 4))
    assert "grade_binding_checked: 2026-08-04" in result, result


# --- record_verdict -----------------------------------------------------------


def test_record_verdict_delegates_when_bound():
    text = (
        "---\n"
        'grade_binding: "external checker stays green"\n'
        "status: hypothesis\n"
        "---\n"
        "\n"
        "Body.\n"
    )
    result = vault_grade_record.record_verdict(text, "pass", REFERENCE_DATE)
    assert "grade_binding_result: pass" in result, result
    assert "grade_binding_checked: 2026-08-04" in result, result


def test_record_verdict_refuses_unbound_note():
    text = "---\nstatus: hypothesis\n---\n\nBody.\n"
    raised = None
    try:
        vault_grade_record.record_verdict(text, "pass", REFERENCE_DATE)
    except Exception as e:  # noqa: BLE001 - we assert the type below
        raised = e
    assert isinstance(raised, ValueError), f"expected ValueError, got {raised!r}"


def _run_all() -> int:
    tests = [
        (name, fn)
        for name, fn in sorted(globals().items())
        if name.startswith("test_") and callable(fn)
    ]
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
