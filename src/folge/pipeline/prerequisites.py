"""Prerequisite checking for the Folge Vision Pipeline."""

import shutil
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

    # Check for pdfinfo with robust path detection
    pdfinfo_path = shutil.which("pdfinfo")
    if not pdfinfo_path:
        # Check common locations
        for p in [
            "/usr/bin/pdfinfo",
            "/usr/local/bin/pdfinfo",
            "/opt/homebrew/bin/pdfinfo",
        ]:
            if Path(p).exists():
                pdfinfo_path = p
                break

    if pdfinfo_path:
        try:
            result = subprocess.run(
                [pdfinfo_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                msg = "[OK] pdfinfo (poppler-utils)"
                ok(on_progress, msg)
                issues.append(msg)
            else:
                msg = "[WARN] pdfinfo found but not working — PDF validation will use pymupdf only"
                warn(on_progress, msg)
                issues.append(msg)
        except Exception:
            msg = "[WARN] pdfinfo found but not working — PDF validation will use pymupdf only"
            warn(on_progress, msg)
            issues.append(msg)
    else:
        msg = "[WARN] pdfinfo not found — PDF validation will use pymupdf only (install: sudo apt install poppler-utils)"
        warn(on_progress, msg)
        issues.append(msg)

    try:
        venv_python = str(
            Path(__file__).resolve().parents[3] / ".venv" / "bin" / "python"
        )
        result = subprocess.run(
            [venv_python, "-c", "import fitz; print('OK')"],
            capture_output=True,
            text=True,
            timeout=10,
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
