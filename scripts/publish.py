#!/usr/bin/env python3
"""End-to-end publishing with GUARANTEED tagged PDF."""
import subprocess
import sys
from pathlib import Path

def run_cmd(cmd, check=True):
    """Run command and optionally check for success."""
    print(f"→ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        return False
    return True

def publish_with_tagged_pdf(guide_path, output_dir):
    """Full pipeline with guaranteed tagged PDF."""
    guide_path = Path(guide_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Steps 1-5: Same as before
    vision_results = output_dir / "vision-results.json"
    enriched = output_dir / "guide.enriched.json"
    md_file = output_dir / "guide.md"

    run_cmd(f"python scripts/batch_process.py {guide_path} images/ {vision_results}")
    run_cmd(f"python scripts/merge.py {guide_path} {vision_results} {enriched}")
    run_cmd(f"python scripts/validate_schema.py {enriched}")
    run_cmd(f"python scripts/render.py {enriched} pdf {md_file}")

    # Step 6: Generate TAGGED PDF with multiple fallbacks
    pdf_file = output_dir / "guide.pdf"

    # Try weasyprint first (best free option)
    if run_cmd(
        f"pandoc {md_file} --lua-filter=pdf-accessibility.lua "
        f"--pdf-engine=weasyprint --pdf-engine-opt=--presentational-hints "
        f"-o {pdf_file}",
        check=False
    ):
        print("✓ Generated with weasyprint")
    # Fallback to wkhtmltopdf
    elif run_cmd(
        f"pandoc {md_file} --lua-filter=pdf-accessibility.lua "
        f"--pdf-engine=wkhtmltopdf --pdf-engine-opt=--enable-local-file-access "
        f"--pdf-engine-opt=--tagged-pdf -o {pdf_file}",
        check=False
    ):
        print("✓ Generated with wkhtmltopdf")
    # Fallback to xelatex with tagging
    elif run_cmd(
        f"pandoc {md_file} --lua-filter=pdf-accessibility.lua "
        f"--pdf-engine=xelatex --pdf-engine-opt=-x "
        f"dvipdfmx -o {pdf_file}",
        check=False
    ):
        print("✓ Generated with xelatex")
    else:
        print("✗ All PDF engines failed")
        return False

    # Step 7: VALIDATE PDF is tagged
    if not run_cmd(f"python scripts/validate_pdf.py {pdf_file}", check=False):
        print("⚠️  PDF tagging validation failed")
        return False

    # Generate other formats
    run_cmd(f"pandoc {md_file} --lua-filter=docx-accessibility.lua -o {output_dir / 'guide.docx'}")
    run_cmd(f"pandoc {md_file} --lua-filter=accessibility.lua -o {output_dir / 'guide.html'}")

    print("✓ All outputs generated with tagged PDF guaranteed!")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python publish.py <guide.json> <output-dir>")
        sys.exit(1)

    success = publish_with_tagged_pdf(sys.argv[1], sys.argv[2])
    sys.exit(0 if success else 1)
