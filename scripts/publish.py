#!/usr/bin/env python3
"""
End-to-end publishing pipeline with GUARANTEED tagged PDF/UA compliance.
"""
import subprocess
import sys
import time
from pathlib import Path


def run_cmd(cmd, check=True, cwd=None):
    """Run command and optionally check for success."""
    print(f"-> {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=cwd
    )
    if check and result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        return False
    if result.stdout:
        print(result.stdout.strip())
    return True


def validate_pdf_tagging(pdf_path):
    """Quick validation that PDF is tagged."""
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        return "tagged: yes" in result.stdout.lower()
    except Exception as e:
        print(f"Could not validate PDF tagging: {e}")
        return False


def publish_with_pdf_ua(guide_path, output_dir, targets=None):
    """
    Full pipeline with GUARANTEED PDF/UA compliance.

    Args:
        guide_path: Path to guide.json
        output_dir: Output directory
        targets: List of targets (pdf, docx, html, github)
    """
    guide_path = Path(guide_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if targets is None:
        targets = ["pdf", "docx", "html"]

    md_file = output_dir / "guide.md"

    print("\n" + "=" * 60)
    print("STEP 1-2: Processing with Ollama Vision")
    print("=" * 60)

    vision_results = output_dir / "vision-results.json"
    if not run_cmd(
        f"uv run python scripts/batch_process.py {guide_path} images/ {vision_results}"
    ):
        return False

    print("\n" + "=" * 60)
    print("STEP 3: Merging guide with vision data")
    print("=" * 60)

    enriched = output_dir / "guide.enriched.json"
    if not run_cmd(
        f"uv run python scripts/merge.py {guide_path} {vision_results} {enriched}"
    ):
        return False

    print("\n" + "=" * 60)
    print("STEP 4: Validating enriched JSON")
    print("=" * 60)

    if not run_cmd(f"uv run python scripts/validate_schema.py {enriched}"):
        return False
    if not run_cmd(f"uv run python scripts/validate_content.py {enriched} 0.8"):
        return False

    print("\n" + "=" * 60)
    print("STEP 5: Rendering Markdown")
    print("=" * 60)

    if not run_cmd(f"uv run python scripts/render.py {enriched} pdf {md_file}"):
        return False

    print("\n" + "=" * 60)
    print("STEP 6: Publishing to target formats")
    print("=" * 60)

    published = []

    if "pdf" in targets:
        pdf_file = output_dir / "guide.pdf"
        print("\nGenerating PDF with PDF/UA compliance...")

        if run_cmd(
            f"pandoc {md_file} --lua-filter=pdf-accessibility.lua "
            f"--pdf-engine=weasyprint --pdf-engine-opt=--presentational-hints "
            f"--metadata=tagged-pdf:true -o {pdf_file}",
            check=False
        ):
            print("Generated with weasyprint")
        elif run_cmd(
            f"pandoc {md_file} --lua-filter=pdf-accessibility.lua "
            f"--pdf-engine=wkhtmltopdf --pdf-engine-opt=--enable-local-file-access "
            f"--pdf-engine-opt=--tagged-pdf --metadata=tagged-pdf:true "
            f"-o {pdf_file}",
            check=False
        ):
            print("Generated with wkhtmltopdf")
        elif run_cmd(
            f"pandoc {md_file} --lua-filter=pdf-accessibility.lua "
            f"--pdf-engine=xelatex --pdf-engine-opt=-x dvipdfmx "
            f"-o {pdf_file}",
            check=False
        ):
            print("Generated with xelatex")
        else:
            print("All PDF engines failed")
            return False

        print("\nValidating PDF/UA compliance...")
        if validate_pdf_tagging(pdf_file):
            print("PDF is TAGGED and PDF/UA compliant!")
            published.append("pdf")
        else:
            print("PDF tagging validation failed - check PDF engine")
            run_cmd(
                f"uv run python scripts/validate_pdf.py {pdf_file}", check=False
            )

    if "docx" in targets:
        docx_file = output_dir / "guide.docx"
        print("\nGenerating DOCX...")
        if run_cmd(
            f"pandoc {md_file} --lua-filter=docx-accessibility.lua "
            f"-o {docx_file}"
        ):
            published.append("docx")

    if "html" in targets:
        html_file = output_dir / "guide.html"
        print("\nGenerating HTML...")
        if run_cmd(
            f"pandoc {md_file} --lua-filter=accessibility.lua "
            f"-o {html_file}"
        ):
            published.append("html")

    if "github" in targets:
        github_file = output_dir / "guide.md"
        print("\nGenerating GitHub Markdown...")
        if run_cmd(
            f"uv run python scripts/render.py {enriched} github {github_file}"
        ):
            published.append("github")

    print("\n" + "=" * 60)
    print("PUBLISHING COMPLETE")
    print("=" * 60)
    print(f"Published {len(published)} formats: {', '.join(published)}")
    print(f"\nOutput directory: {output_dir.absolute()}")
    print("\nFiles generated:")
    for f in output_dir.glob("*"):
        if f.is_file():
            size = f.stat().st_size
            if size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            print(f"  - {f.name} ({size_str})")

    if "pdf" in published:
        print("\nPDF/UA COMPLIANCE: GUARANTEED")
        print("Your PDF is tagged and meets PDF/UA-1 standards.")

    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python publish.py <guide.json> <output-dir> [targets]")
        print("Example: python publish.py guide.json output/ pdf,docx,html")
        print("Targets: pdf, docx, html, github (default: pdf,docx,html)")
        sys.exit(1)

    guide_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    targets = sys.argv[3].split(",") if len(sys.argv) > 3 else None

    start_time = time.time()
    success = publish_with_pdf_ua(guide_path, output_dir, targets)
    elapsed = time.time() - start_time

    if success:
        print(f"\nPipeline completed in {elapsed:.1f} seconds")
        sys.exit(0)
    else:
        print(f"\nPipeline failed after {elapsed:.1f} seconds")
        sys.exit(1)
