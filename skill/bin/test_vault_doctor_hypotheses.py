#!/usr/bin/env python3
"""Tests for vault-doctor --hypotheses (stale + grade-integrity checks).

Self-contained: assert-based `test_*` functions plus a `__main__` runner that
prints PASS/FAIL and exits nonzero on any failure. Also pytest-collectable.
Imports the function under test from the sibling vault-doctor.py via importlib
(that file has no .py-importable name, hence the dashes).
"""
from __future__ import annotations

import importlib.util
import shutil
import tempfile
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("vault_doctor", HERE / "vault-doctor.py")
vault_doctor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vault_doctor)

REFERENCE_DATE = date(2026, 7, 30)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_vault() -> Path:
    vault = Path(tempfile.mkdtemp(prefix="vault-doctor-hyp-"))
    (vault / ".obsidian").mkdir()

    # 1. clean `tested` dossier: [[link]] in ## Experiment + "baseline" token
    #    present in the body -> must NOT be flagged (stale or grade-integrity).
    _write(vault / "Hypotheses" / "clean-tested-dossier.md", f"""---
status: hypothesis
grade: tested
target_grade: tested
type: hypothesis
created: {REFERENCE_DATE.isoformat()}
---

# Clean tested claim

## Pre-registration
- **Test:** run the probe on held-out data
- **Threshold:** AUROC >= 0.8
- **Refutes if:** AUROC below 0.8

## Experiment
- [[some-run]] - the scoped run.

## Evidence and grading
Beats the text-only baseline by 0.09 AUROC.

## Verdict
Still open.
""")

    # 2. `robust` dossier with confounds enumerated but NO uncertainty token
    #    -> expect a grade-integrity flag.
    _write(vault / "Hypotheses" / "robust-missing-uncertainty.md", f"""---
status: hypothesis
grade: robust
target_grade: robust
type: hypothesis
created: {REFERENCE_DATE.isoformat()}
---

# Robust claim with confounds ruled out but no error bars reported

## Pre-registration
- **Test:** run the comparison
- **Threshold:** effect > 0
- **Refutes if:** no effect

## Experiment
- [[some-run]] - the scoped run.

## Evidence and grading
Confounds enumerated and ruled out: order effects, prompt length.

## Verdict
Still open.
""")

    # 3. old `suggested` dossier, created 60 days before the reference date,
    #    no experiment link -> expect a stale flag.
    old_date = REFERENCE_DATE - timedelta(days=60)
    _write(vault / "Hypotheses" / "old-suggested-no-link.md", f"""---
status: hypothesis
grade: suggested
target_grade: tested
type: hypothesis
created: {old_date.isoformat()}
---

# Old suggested claim with no experiment link

## Pre-registration
- **Test:** run a comparison eventually
- **Threshold:** to be decided
- **Refutes if:** no improvement observed

## Experiment
Not yet scoped.

## Evidence and grading
Not yet run.

## Verdict
Still open.
""")

    # 4. clean recent dossier -> expect no flags at all.
    _write(vault / "Hypotheses" / "clean-recent-dossier.md", f"""---
status: hypothesis
grade: suggested
target_grade: tested
type: hypothesis
created: {REFERENCE_DATE.isoformat()}
---

# Clean recent suggested claim

## Pre-registration
- **Test:** run the probe and text-only judge on the same held-out set
- **Threshold:** probe AUROC >= text-only AUROC + 0.05
- **Refutes if:** probe AUROC within 0.05 of baseline or below it

## Experiment
- [[future-run]] - the scoped run comparing both.

## Evidence and grading
Not yet run.

## Verdict
Still open.
""")

    # 5. resolved `supported` dossier, well-formed (confound + uncertainty
    #    tokens present) -> must appear in resolved, NOT in open, and must NOT
    #    be spuriously flagged stale/integrity.
    _write(vault / "Hypotheses" / "resolved-supported-dossier.md", f"""---
status: supported
grade: robust
target_grade: robust
type: hypothesis
created: {REFERENCE_DATE.isoformat()}
---

# A resolved supported claim

## Pre-registration
- **Test:** run the comparison
- **Threshold:** effect > 0
- **Refutes if:** no effect

## Experiment
- [[some-run]] - the scoped run.

## Evidence and grading
Confounds enumerated and ruled out: order effects, prompt length.
Effect size reported with a 95% CI: 0.85-0.95.

## Verdict
Supported at grade robust.
""")

    # 6. resolved `mixed` dossier (supported part + refuted part), well-formed
    #    -> must appear in resolved as status "mixed", NOT in open, and must
    #    NOT be spuriously flagged stale/integrity.
    _write(vault / "Hypotheses" / "resolved-mixed-dossier.md", f"""---
status: mixed
grade: robust
target_grade: paper-grade
type: hypothesis
created: {REFERENCE_DATE.isoformat()}
---

# A claim that resolved mixed: one sub-claim supported, another refuted

## Pre-registration
- **Test:** run the comparison
- **Threshold:** effect > 0
- **Refutes if:** no effect

## Experiment
- [[some-run]] - the scoped run.

## Evidence and grading
Confounds enumerated and ruled out: order effects, prompt length.
Effect size reported with a 95% CI: 0.85-0.95.

## Verdict
Supported part at grade robust; the stronger, beyond-scope part is refuted.
""")

    # index file (00-* prefix) must NOT be picked up as a dossier.
    _write(vault / "Hypotheses" / "00-INDEX.md", """---
type: project-index
---

# Hypotheses index
""")

    return vault


def test_clean_tested_dossier_not_flagged():
    vault = _make_vault()
    try:
        findings = vault_doctor._hypothesis_findings(vault, 21, REFERENCE_DATE)
        stale_paths = {p for p, *_ in findings["stale"]}
        integrity_paths = {p for p, *_ in findings["integrity"]}
        assert "Hypotheses/clean-tested-dossier.md" not in stale_paths
        assert "Hypotheses/clean-tested-dossier.md" not in integrity_paths
    finally:
        shutil.rmtree(vault)


def test_robust_dossier_missing_uncertainty_flagged():
    vault = _make_vault()
    try:
        findings = vault_doctor._hypothesis_findings(vault, 21, REFERENCE_DATE)
        integrity = {p: missing for p, _grade, missing in findings["integrity"]}
        path = "Hypotheses/robust-missing-uncertainty.md"
        assert path in integrity, f"expected grade-integrity flag for {path}, got {integrity}"
        assert any("uncertainty" in m.lower() or "interval" in m.lower() or "ci" in m.lower()
                   for m in integrity[path]), integrity[path]
    finally:
        shutil.rmtree(vault)


def test_old_suggested_no_link_is_stale():
    vault = _make_vault()
    try:
        findings = vault_doctor._hypothesis_findings(vault, 21, REFERENCE_DATE)
        stale = {p: (age, reasons) for p, age, reasons in findings["stale"]}
        path = "Hypotheses/old-suggested-no-link.md"
        assert path in stale, f"expected stale flag for {path}, got {stale}"
        age, reasons = stale[path]
        assert age == 60, age
        assert reasons
    finally:
        shutil.rmtree(vault)


def test_clean_recent_dossier_has_no_flags():
    vault = _make_vault()
    try:
        findings = vault_doctor._hypothesis_findings(vault, 21, REFERENCE_DATE)
        stale_paths = {p for p, *_ in findings["stale"]}
        integrity_paths = {p for p, *_ in findings["integrity"]}
        assert "Hypotheses/clean-recent-dossier.md" not in stale_paths
        assert "Hypotheses/clean-recent-dossier.md" not in integrity_paths
    finally:
        shutil.rmtree(vault)


def test_index_file_excluded_from_dossiers():
    vault = _make_vault()
    try:
        findings = vault_doctor._hypothesis_findings(vault, 21, REFERENCE_DATE)
        all_paths = {p for p, *_ in findings["open"]}
        assert not any("00-INDEX" in p for p in all_paths), all_paths
    finally:
        shutil.rmtree(vault)


def test_resolved_supported_dossier_in_resolved_not_open():
    vault = _make_vault()
    try:
        findings = vault_doctor._hypothesis_findings(vault, 21, REFERENCE_DATE)
        resolved = {p: (status, grade) for p, status, grade in findings["resolved"]}
        open_paths = {p for p, *_ in findings["open"]}
        stale_paths = {p for p, *_ in findings["stale"]}
        integrity_paths = {p for p, *_ in findings["integrity"]}
        path = "Hypotheses/resolved-supported-dossier.md"
        assert path in resolved, f"expected {path} in resolved, got {resolved}"
        assert resolved[path][0] == "supported", resolved[path]
        assert path not in open_paths
        assert path not in stale_paths
        assert path not in integrity_paths
    finally:
        shutil.rmtree(vault)


def test_resolved_mixed_dossier_in_resolved_not_open_and_clean():
    vault = _make_vault()
    try:
        findings = vault_doctor._hypothesis_findings(vault, 21, REFERENCE_DATE)
        resolved = {p: (status, grade) for p, status, grade in findings["resolved"]}
        open_paths = {p for p, *_ in findings["open"]}
        stale_paths = {p for p, *_ in findings["stale"]}
        integrity_paths = {p for p, *_ in findings["integrity"]}
        path = "Hypotheses/resolved-mixed-dossier.md"
        assert path in resolved, f"expected {path} in resolved, got {resolved}"
        assert resolved[path][0] == "mixed", resolved[path]
        assert path not in open_paths, "mixed dossier must not count as open"
        assert path not in stale_paths
        assert path not in integrity_paths
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
