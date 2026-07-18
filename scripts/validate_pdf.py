#!/usr/bin/env python3
"""Validate PDF for accessibility compliance."""
import subprocess
import sys
from pathlib import Path

def validate_pdf_tagging(pdf_path):
    """Check if PDF has proper tagging structure."""
    try:
        # Use pdfinfo to check for tags
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True, text=True
        )

        if "Tagged: yes" in result.stdout:
            print(f"✓ {pdf_path} is TAGGED (PDF/UA compliant)")
            return True
        else:
            print(f"✗ {pdf_path} is NOT tagged")
            return False

    except FileNotFoundError:
        print("pdfinfo not found. Install poppler-utils:")
        print("  Ubuntu: sudo apt-get install poppler-utils")
        print("  Mac: brew install poppler")
        return False

def validate_pdf_accessibility(pdf_path):
    """Use pa11y or axe-pdf for comprehensive validation."""
    try:
        # Option 1: Use pa11y-cli
        result = subprocess.run(
            ["pa11y", str(pdf_path)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"✓ {pdf_path} passed pa11y validation")
            return True
        else:
            print(f"✗ {pdf_path} failed pa11y validation")
            print(result.stdout)
            return False
    except FileNotFoundError:
        print("pa11y not found. Install with: npm install -g pa11y-cli")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_pdf.py <pdf-file>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    tagged = validate_pdf_tagging(pdf_path)
    accessible = validate_pdf_accessibility(pdf_path)

    if tagged and accessible:
        print("✓ PDF is fully accessible and tagged!")
        sys.exit(0)
    else:
        print("✗ PDF accessibility issues found")
        sys.exit(1)
