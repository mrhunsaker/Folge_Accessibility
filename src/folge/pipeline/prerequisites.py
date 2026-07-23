"""Prerequisite checking for the Folge Vision Pipeline."""

import subprocess
from pathlib import Path
from typing import Tuple, List

from folge.pipeline.progress import ProgressCallback, banner, ok, warn, error


def check(on_progress: ProgressCallback = None) -> Tuple[bool, List[str]]:
    """Verify all required external tools are available.

    Returns:
        (ok, issues) where ok is True if all critical tools are present,
        and issues is a list of human-readable status messages.
    """
    banner(on_progress, "CHECKING PREREQUISITES")
    issues = []
    all_ok = True

    checks = [
        ("uv", "uv --version"),
        ("Python (via uv)", "uv run python --version"),
        ("Pandoc", "pandoc --version"),
    ]

    for name, cmd in checks:
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                ver = result.stdout.strip().splitlines()[0] if result.stdout else "OK"
                msg = f"[OK] {name}: {ver}"
                ok(on_progress, msg)
                issues.append(msg)
            else:
                msg = f"[MISSING] {name}"
                error(on_progress, msg)
                issues.append(msg)
                all_ok = False
        except Exception:
            msg = f"[MISSING] {name}"
            error(on_progress, msg)
            issues.append(msg)
            all_ok = False

    try:
        result = subprocess.run(
            ["/usr/bin/pdfinfo", "--version"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            msg = "[OK] pdfinfo (poppler-utils)"
            ok(on_progress, msg)
            issues.append(msg)
        else:
            msg = "[WARN] pdfinfo not found — PDF validation will use pymupdf only"
            warn(on_progress, msg)
            issues.append(msg)
    except Exception:
        msg = "[WARN] pdfinfo not found — PDF validation will use pymupdf only"
        warn(on_progress, msg)
        issues.append(msg)

    try:
        venv_python = str(Path(__file__).resolve().parents[3] / ".venv" / "bin" / "python")
        result = subprocess.run(
            [venv_python, "-c", "import fitz; print('OK')"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and "OK" in result.stdout:
            msg = "[OK] pymupdf"
            ok(on_progress, msg)
            issues.append(msg)
        else:
            msg = "[WARN] pymupdf not importable"
            warn(on_progress, msg)
            issues.append(msg)
    except Exception:
        msg = "[WARN] pymupdf not importable"
        warn(on_progress, msg)
        issues.append(msg)

    return all_ok, issues
