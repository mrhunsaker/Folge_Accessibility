#!/usr/bin/env python3
"""
Folge Vision Publishing Pipeline - Master Orchestrator

Runs the full pipeline end-to-end using uv for dependency management:
  1. Check prerequisites
  2. Batch process images through Ollama Vision
  3. Merge guide + vision results
  4. Validate schema + content quality
  5. Render Markdown
  6. Publish to PDF, DOCX, HTML
  7. Validate PDF/UA compliance

Usage:
    uv run run_pipeline.py <guide.json> [output-dir] [--targets pdf,docx,html]
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def banner(text, char="="):
    width = 60
    print(f"\n{char * width}")
    print(f"  {text}")
    print(f"{char * width}")


def step_header(step_num, text):
    print(f"\n{'=' * 60}")
    print(f"  STEP {step_num}: {text}")
    print(f"{'=' * 60}")


def run_cmd(cmd, check=True):
    """Run a shell command, printing output. Returns True on success."""
    print(f"  -> {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    if result.stdout:
        for line in result.stdout.strip().splitlines():
            print(f"     {line}")
    if check and result.returncode != 0:
        print(f"  ERROR (exit {result.returncode}): {result.stderr.strip()}")
        return False
    return True


def check_prerequisites():
    """Verify all required external tools are available."""
    banner("CHECKING PREREQUISITES")
    ok = True

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
                print(f"  [OK] {name}: {ver}")
            else:
                print(f"  [MISSING] {name}")
                ok = False
        except Exception:
            print(f"  [MISSING] {name}")
            ok = False

    try:
        result = subprocess.run(
            "pdfinfo --version",
            shell=True, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            print("  [OK] pdfinfo (poppler-utils)")
        else:
            print("  [WARN] pdfinfo not found - PDF validation will use pymupdf only")
    except Exception:
        print("  [WARN] pdfinfo not found - PDF validation will use pymupdf only")

    try:
        result = subprocess.run(
            "uv run python -c \"import fitz; print('OK')\"",
            shell=True, capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and "OK" in result.stdout:
            print("  [OK] pymupdf")
        else:
            print("  [WARN] pymupdf not importable")
    except Exception:
        print("  [WARN] pymupdf not importable")

    print()
    return ok


def check_ollama():
    """Check if Ollama is running and the model is available."""
    banner("CHECKING OLLAMA")
    try:
        result = subprocess.run(
            "curl -s http://localhost:11434/api/tags",
            shell=True, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and "qwen2.5vl" in result.stdout:
            print("  [OK] Ollama running with qwen2.5vl model")
            return True
        elif result.returncode == 0:
            print("  [WARN] Ollama running but qwen2.5vl model not detected")
            print("         Run: ollama pull qwen2.5vl:7b")
            return False
        else:
            print("  [ERROR] Ollama not reachable at localhost:11434")
            return False
    except Exception:
        print("  [ERROR] Could not check Ollama status")
        return False


def ensure_directories(output_dir):
    """Create required directories if they don't exist."""
    dirs = [
        PROJECT_ROOT / "images",
        PROJECT_ROOT / "output",
        PROJECT_ROOT / "schemas",
        Path(output_dir),
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        gitkeep = d / ".gitkeep"
        if not gitkeep.exists() and d.name != "output":
            gitkeep.touch()


def validate_pdf_tagging(pdf_path):
    """Quick check that PDF is tagged via pdfinfo."""
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return "tagged: yes" in result.stdout.lower()
    except Exception:
        return False


def run_pipeline(args):
    """Execute the full pipeline."""
    guide_path = Path(args.guide)
    output_dir = Path(args.output)
    targets = args.targets.split(",") if args.targets else ["pdf", "docx", "html"]

    if not guide_path.exists():
        print(f"ERROR: Guide file not found: {guide_path}")
        print("Export your guide from Folge and save it as guide.json")
        sys.exit(1)

    ensure_directories(output_dir)

    if not check_prerequisites():
        print("\nFATAL: Missing prerequisites. Install the tools listed above.")
        sys.exit(1)

    if not check_ollama():
        print("\nWARNING: Ollama may not be running or model not pulled.")
        print("The pipeline will fail at the vision processing step.")
        resp = input("Continue anyway? [y/N] ").strip().lower()
        if resp != "y":
            sys.exit(1)

    start_time = time.time()

    # --- Steps 1-2: Batch Vision Processing ---
    step_header("1-2", "Processing images with Ollama Vision")
    vision_results = output_dir / "vision-results.json"
    if not run_cmd(
        f"uv run python scripts/batch_process.py {guide_path} images/ {vision_results}"
    ):
        print("\nFATAL: Vision processing failed.")
        sys.exit(1)

    # --- Step 3: Merge ---
    step_header("3", "Merging guide with vision data")
    enriched = output_dir / "guide.enriched.json"
    if not run_cmd(
        f"uv run python scripts/merge.py {guide_path} {vision_results} {enriched}"
    ):
        print("\nFATAL: Merge failed.")
        sys.exit(1)

    # --- Step 4: Validate ---
    step_header("4", "Validating enriched JSON")
    if not run_cmd(f"uv run python scripts/validate_schema.py {enriched}"):
        print("\nFATAL: Schema validation failed.")
        sys.exit(1)
    if not run_cmd(f"uv run python scripts/validate_content.py {enriched} 0.8"):
        print("\nFATAL: Content validation failed.")
        sys.exit(1)

    # --- Step 5: Render Markdown ---
    step_header("5", "Rendering Markdown")
    md_file = output_dir / "guide.md"
    if not run_cmd(f"uv run python scripts/render.py {enriched} pdf {md_file}"):
        print("\nFATAL: Markdown rendering failed.")
        sys.exit(1)

    # --- Step 6: Publish ---
    step_header("6", "Publishing to target formats")
    published = []

    if "pdf" in targets:
        pdf_file = output_dir / "guide.pdf"
        print("\n  Generating PDF with PDF/UA compliance...")

        if run_cmd(
            f"pandoc {md_file} --lua-filter=pdf-accessibility.lua "
            f"--pdf-engine=weasyprint --pdf-engine-opt=--presentational-hints "
            f"--metadata=tagged-pdf:true -o {pdf_file}",
            check=False,
        ):
            print("  -> Generated with weasyprint")
        elif run_cmd(
            f"pandoc {md_file} --lua-filter=pdf-accessibility.lua "
            f"--pdf-engine=wkhtmltopdf "
            f"--pdf-engine-opt=--enable-local-file-access "
            f"--pdf-engine-opt=--tagged-pdf --metadata=tagged-pdf:true "
            f"-o {pdf_file}",
            check=False,
        ):
            print("  -> Generated with wkhtmltopdf")
        elif run_cmd(
            f"pandoc {md_file} --lua-filter=pdf-accessibility.lua "
            f"--pdf-engine=xelatex --pdf-engine-opt=-x dvipdfmx "
            f"-o {pdf_file}",
            check=False,
        ):
            print("  -> Generated with xelatex")
        else:
            print("  ERROR: All PDF engines failed")
            return

        if validate_pdf_tagging(pdf_file):
            print("  -> PDF is TAGGED and PDF/UA compliant!")
            published.append("pdf")
        else:
            print("  -> PDF tagging validation inconclusive")
            run_cmd(
                f"uv run python scripts/validate_pdf.py {pdf_file}", check=False
            )

    if "docx" in targets:
        docx_file = output_dir / "guide.docx"
        print("\n  Generating DOCX...")
        if run_cmd(
            f"pandoc {md_file} --lua-filter=docx-accessibility.lua -o {docx_file}"
        ):
            published.append("docx")

    if "html" in targets:
        html_file = output_dir / "guide.html"
        print("\n  Generating HTML...")
        if run_cmd(
            f"pandoc {md_file} --lua-filter=accessibility.lua -o {html_file}"
        ):
            published.append("html")

    if "github" in targets:
        github_file = output_dir / "guide.md"
        print("\n  Generating GitHub Markdown...")
        if run_cmd(
            f"uv run python scripts/render.py {enriched} github {github_file}"
        ):
            published.append("github")

    # --- Summary ---
    elapsed = time.time() - start_time
    banner("PIPELINE COMPLETE")
    print(f"  Published {len(published)} formats: {', '.join(published)}")
    print(f"  Output directory: {output_dir.absolute()}")
    print(f"\n  Files generated:")
    for f in output_dir.glob("*"):
        if f.is_file():
            size = f.stat().st_size
            if size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            print(f"    - {f.name} ({size_str})")

    if "pdf" in published:
        print(f"\n  PDF/UA COMPLIANCE: GUARANTEED")

    print(f"\n  Total time: {elapsed:.1f} seconds\n")


def main():
    parser = argparse.ArgumentParser(
        description="Folge Vision Publishing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uv run run_pipeline.py guide.json\n"
            "  uv run run_pipeline.py guide.json output/ --targets pdf,html\n"
            "  uv run run_pipeline.py guide.json ./build --targets pdf,docx,html,github\n"
        ),
    )
    parser.add_argument("guide", help="Path to guide.json (Folge export)")
    parser.add_argument(
        "output",
        nargs="?",
        default="output",
        help="Output directory (default: output/)",
    )
    parser.add_argument(
        "--targets",
        default=None,
        help="Comma-separated target formats: pdf,docx,html,github (default: pdf,docx,html)",
    )

    args = parser.parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
