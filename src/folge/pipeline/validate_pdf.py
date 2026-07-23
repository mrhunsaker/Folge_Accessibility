"""PDF/UA validation using pdfinfo and pymupdf."""

import subprocess
from pathlib import Path
from typing import Tuple, List

from folge.pipeline.progress import ProgressCallback, ok, warn, error, info


def check_pdfinfo_installed():
    try:
        result = subprocess.run(["/usr/bin/pdfinfo", "--version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def check_pymupdf_installed():
    try:
        import fitz
        return True
    except ImportError:
        return False


def validate_with_pdfinfo(pdf_path: Path) -> Tuple[bool, List[str]]:
    try:
        result = subprocess.run(["/usr/bin/pdfinfo", str(pdf_path)], capture_output=True, text=True, timeout=10)
        issues = []
        success = result.returncode == 0
        if success:
            for line in result.stdout.splitlines():
                if "Tagged:" in line:
                    if "yes" in line.lower():
                        issues.append(f"PDF/UA tagged: YES")
                    else:
                        issues.append(f"PDF/UA tagged: NO")
        return success, issues
    except Exception as e:
        return False, [f"pdfinfo error: {e}"]


def validate_with_pymupdf(pdf_path: Path) -> Tuple[bool, List[str]]:
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        issues = []
        issues.append(f"Pages: {len(doc)}")
        issues.append(f"Metadata keys: {list(doc.metadata.keys()) if doc.metadata else 'none'}")
        doc.close()
        return True, issues
    except Exception as e:
        return False, [f"pymupdf error: {e}"]


def validate(pdf_path: Path, on_progress: ProgressCallback = None) -> Tuple[bool, List[str]]:
    """Validate PDF/UA compliance. Returns (ok, issues)."""
    info(on_progress, f"Validating PDF: {pdf_path.name}")

    all_issues = []
    all_ok = True

    if check_pdfinfo_installed():
        ok_flag, issues = validate_with_pdfinfo(pdf_path)
        all_issues.extend(issues)
        if ok_flag:
            ok(on_progress, "pdfinfo validation passed")
        else:
            all_ok = False
            error(on_progress, "pdfinfo validation failed")
    else:
        warn(on_progress, "pdfinfo not available")

    if check_pymupdf_installed():
        ok_flag, issues = validate_with_pymupdf(pdf_path)
        all_issues.extend(issues)
        if ok_flag:
            ok(on_progress, "pymupdf validation passed")
        else:
            all_ok = False
            error(on_progress, "pymupdf validation failed")
    else:
        warn(on_progress, "pymupdf not available")

    return all_ok, all_issues
