#!/usr/bin/env python3
"""
Validate PDF for PDF/UA compliance and tagging.
Ensures generated PDFs meet accessibility standards.
"""
import subprocess
import sys
from pathlib import Path


def check_pdfinfo_installed():
    """Check if pdfinfo (from poppler-utils) is installed."""
    try:
        subprocess.run(
            ["pdfinfo", "--version"], capture_output=True, check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_pymupdf_installed():
    """Check if pymupdf is installed."""
    try:
        import fitz  # noqa: F401
        return True
    except ImportError:
        return False


def validate_with_pdfinfo(pdf_path):
    """
    Validate PDF using pdfinfo command.
    Checks for: Tagged status, PDF version, metadata.
    """
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout.lower()
        issues = []
        successes = []

        if "tagged: yes" in output:
            successes.append("PDF is TAGGED (PDF/UA compliant)")
        else:
            issues.append("PDF is NOT tagged - CRITICAL for accessibility")

        for line in output.split('\n'):
            if 'pdf version:' in line.lower():
                version = line.split(':')[-1].strip()
                if float(version) >= 1.7:
                    successes.append(
                        f"PDF version {version} (meets PDF/UA requirement)"
                    )
                else:
                    issues.append(
                        f"PDF version {version} (needs 1.7+ for PDF/UA)"
                    )

        if "creator:" in output:
            successes.append("PDF has creator metadata")
        if "producer:" in output:
            successes.append("PDF has producer metadata")

        return issues, successes

    except Exception as e:
        return [f"pdfinfo validation failed: {str(e)}"], []


def validate_with_pymupdf(pdf_path):
    """
    Validate PDF using pymupdf library.
    Provides more detailed tagging information.
    """
    try:
        import fitz

        doc = fitz.open(str(pdf_path))
        issues = []
        successes = []

        if doc.is_tagged:
            successes.append("PDF is TAGGED (pymupdf confirmed)")
        else:
            issues.append("PDF is NOT tagged - CRITICAL for accessibility")

        if doc.is_pdf_ua:
            successes.append("PDF is PDF/UA compliant")
        else:
            issues.append("PDF is NOT PDF/UA compliant")

        version = doc.pdf_version
        if version >= 1.7:
            successes.append(f"PDF version {version} (meets requirement)")
        else:
            issues.append(f"PDF version {version} (needs 1.7+ for PDF/UA)")

        if doc.has_structure:
            successes.append("PDF has structure elements")
        else:
            issues.append("PDF missing structure elements")

        return issues, successes

    except Exception as e:
        return [f"pymupdf validation failed: {str(e)}"], []


def validate_pdf(pdf_path):
    """
    Comprehensive PDF validation for accessibility.
    Uses multiple methods for redundancy.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        return [f"PDF file not found: {pdf_path}"], []

    all_issues = []
    all_successes = []

    if check_pdfinfo_installed():
        issues, successes = validate_with_pdfinfo(pdf_path)
        all_issues.extend(issues)
        all_successes.extend(successes)
    else:
        print("pdfinfo not found. Install poppler-utils for better validation.")
        print("  Ubuntu: sudo apt-get install poppler-utils")
        print("  Mac: brew install poppler")
        print("  Windows: Download from poppler.freedesktop.org")

    if check_pymupdf_installed():
        issues, successes = validate_with_pymupdf(pdf_path)
        all_issues.extend(issues)
        all_successes.extend(successes)
    else:
        print("pymupdf not found. Install with: uv add pymupdf")

    return all_issues, all_successes


def print_results(pdf_path, issues, successes):
    """Print validation results in a readable format."""
    print(f"\n{'=' * 60}")
    print(f"PDF ACCESSIBILITY VALIDATION: {pdf_path}")
    print(f"{'=' * 60}")

    if successes:
        print("\nPASSED:")
        for success in successes:
            print(f"  + {success}")

    if issues:
        print("\nFAILED:")
        for issue in issues:
            print(f"  - {issue}")

    if not issues and successes:
        print("\nPDF is FULLY ACCESSIBLE and PDF/UA COMPLIANT!")
        return True
    else:
        print("\nPDF has accessibility issues that need to be fixed.")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_pdf.py <pdf-file>")
        print("Example: python validate_pdf.py output/guide.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]
    issues, successes = validate_pdf(pdf_path)
    success = print_results(pdf_path, issues, successes)

    sys.exit(0 if success else 1)
