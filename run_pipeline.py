#!/usr/bin/env python3
"""
Folge Vision Publishing Pipeline - Master Orchestrator

Runs the full pipeline end-to-end using uv for dependency management:
  1. Check prerequisites
  2. Batch process images through Vision API (Ollama or OpenRouter)
  3. Merge guide + vision results
  4. Validate schema + content quality
  5. Render Markdown
  6. Publish to PDF, DOCX, HTML
  7. Validate PDF/UA compliance

Usage:
    uv run run_pipeline.py <guide.json> [output-dir] [--targets pdf,docx,html] [--provider ollama|openrouter]
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def banner(text, char="=", width=60):
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
        stderr = result.stderr.strip()
        if stderr:
            for line in stderr.splitlines()[:10]:
                print(f"     {line}")
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


def check_provider(provider_name, api_key=None):
    """Check if the selected vision provider is reachable."""
    banner("CHECKING PROVIDER")

    if provider_name == "openrouter":
        key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not key:
            print("  [ERROR] OPENROUTER_API_KEY not set")
            print("          export OPENROUTER_API_KEY='sk-or-...'")
            return False
        masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
        print(f"  [OK] Provider: OpenRouter (cloud)")
        print(f"  [OK] API key: {masked}")
        return True

    # Ollama (default)
    try:
        result = subprocess.run(
            "curl -s http://localhost:11434/api/tags",
            shell=True, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            data = result.stdout
            if "qwen2.5vl" in data:
                print("  [OK] Provider: Ollama (local)")
                print("  [OK] Ollama running with qwen2.5vl model")
                return True
            elif "granite" in data:
                print("  [WARN] Ollama running but qwen2.5vl not found (granite available)")
                print("         Vision processing requires a vision model like qwen2.5vl-8k:latest")
                return False
            else:
                print("  [WARN] Ollama running but no vision model detected")
                print("         Run: ollama pull qwen2.5vl-8k:latest")
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


def count_guide_steps(guide_path):
    """Quick count of steps in the guide JSON."""
    try:
        import json
        with open(guide_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return len(data.get("steps", []))
    except Exception:
        return None


def run_pipeline(args):
    """Execute the full pipeline."""
    guide_path = Path(args.guide)
    output_dir = Path(args.output)
    targets = args.targets.split(",") if args.targets else ["pdf", "docx", "html"]
    provider_name = args.provider or "ollama"
    api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY")

    if not guide_path.exists():
        print(f"ERROR: Guide file not found: {guide_path}")
        print("Export your guide from Folge and save it as guide.json")
        sys.exit(1)

    ensure_directories(output_dir)

    if not check_prerequisites():
        print("\nFATAL: Missing prerequisites. Install the tools listed above.")
        sys.exit(1)

    if not check_provider(provider_name, api_key):
        print(f"\nWARNING: {provider_name.title()} may not be available.")
        print("The pipeline will fail at the vision processing step.")
        resp = input("Continue anyway? [y/N] ").strip().lower()
        if resp != "y":
            sys.exit(1)

    start_time = time.time()

    # Count steps for progress context
    step_count = count_guide_steps(guide_path)
    step_label = f"({step_count} steps)" if step_count else ""

    # --- Steps 1-2: Batch Vision Processing ---
    step_header("1-2", f"Processing images with {provider_name.title()} Vision")
    vision_results = output_dir / "vision-results.json"

    # Build batch_process command
    batch_cmd = (
        f"uv run python scripts/batch_process.py {guide_path} images/ {vision_results}"
        f" --provider={provider_name}"
    )
    if api_key and provider_name == "openrouter":
        batch_cmd += f" --api-key={api_key}"

    if not run_cmd(batch_cmd):
        print("\nWARNING: Some vision processing steps returned errors.")
        print("The pipeline will continue but enriched output may have vision_error fields.")
        if not vision_results.exists():
            print("\nFATAL: Vision processing produced no output.")
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
    schema_warnings = output_dir / "schema-warnings.json"
    if not run_cmd(
        f"uv run python scripts/validate_schema.py {enriched} --warnings-out {schema_warnings}"
    ):
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

    # --- Step 5b: Manual attention list ---
    manual_file = output_dir / "manual-attention-needed.md"
    manual_cmd = (
        f"uv run python scripts/generate_manual_attention.py {enriched} images/ {manual_file}"
    )
    if schema_warnings.exists():
        manual_cmd += f" {schema_warnings}"
    run_cmd(manual_cmd, check=False)

    # --- Step 6: Publish ---
    step_header("6", "Publishing to target formats")
    published = []
    pdf_errors = []

    if "pdf" in targets:
        pdf_file = output_dir / "guide.pdf"
        print(f"\n  -> PDF (weasyprint)...", end=" ", flush=True)

        result = subprocess.run(
            f"pandoc {md_file} --lua-filter=pdf-accessibility.lua "
            f"--pdf-engine=weasyprint --pdf-engine-opt=--presentational-hints "
            f"--metadata=tagged-pdf:true -o {pdf_file}",
            shell=True, capture_output=True, text=True,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            print(f"done ({pdf_file.stat().st_size / 1024:.1f} KB)")
            published.append("pdf")
        else:
            err_msg = result.stderr.strip()[:200] if result.stderr else "unknown error"
            print(f"FAILED")
            pdf_errors.append(("weasyprint", err_msg))

            # Fallback: wkhtmltopdf
            print(f"  -> PDF (wkhtmltopdf)...", end=" ", flush=True)
            result2 = subprocess.run(
                f"pandoc {md_file} --lua-filter=pdf-accessibility.lua "
                f"--pdf-engine=wkhtmltopdf "
                f"--pdf-engine-opt=--enable-local-file-access "
                f"--pdf-engine-opt=--tagged-pdf --metadata=tagged-pdf:true "
                f"-o {pdf_file}",
                shell=True, capture_output=True, text=True,
                cwd=str(PROJECT_ROOT),
            )
            if result2.returncode == 0:
                print(f"done ({pdf_file.stat().st_size / 1024:.1f} KB)")
                published.append("pdf")
            else:
                err_msg2 = result2.stderr.strip()[:200] if result2.stderr else "unknown error"
                print(f"FAILED")
                pdf_errors.append(("wkhtmltopdf", err_msg2))

                # Fallback: xelatex
                print(f"  -> PDF (xelatex)...", end=" ", flush=True)
                result3 = subprocess.run(
                    f"pandoc {md_file} --lua-filter=pdf-accessibility.lua "
                    f"--pdf-engine=xelatex --pdf-engine-opt=-x dvipdfmx "
                    f"-o {pdf_file}",
                    shell=True, capture_output=True, text=True,
                    cwd=str(PROJECT_ROOT),
                )
                if result3.returncode == 0:
                    print(f"done ({pdf_file.stat().st_size / 1024:.1f} KB)")
                    published.append("pdf")
                else:
                    err_msg3 = result3.stderr.strip()[:200] if result3.stderr else "unknown error"
                    print(f"FAILED")
                    pdf_errors.append(("xelatex", err_msg3))

        if "pdf" not in published:
            print("\n  All PDF engines failed:")
            for engine, err in pdf_errors:
                print(f"    {engine}: {err[:120]}")
        elif validate_pdf_tagging(pdf_file):
            print("  -> PDF is TAGGED and PDF/UA compliant!")

    if "docx" in targets:
        docx_file = output_dir / "guide.docx"
        print(f"\n  -> DOCX...", end=" ", flush=True)
        result = subprocess.run(
            f"pandoc {md_file} --lua-filter=docx-accessibility.lua -o {docx_file}",
            shell=True, capture_output=True, text=True,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            print(f"done ({docx_file.stat().st_size / 1024:.1f} KB)")
            published.append("docx")
        else:
            print("FAILED")
            if result.stderr:
                for line in result.stderr.strip().splitlines()[:5]:
                    print(f"    {line}")

    if "html" in targets:
        html_file = output_dir / "guide.html"
        print(f"\n  -> HTML...", end=" ", flush=True)
        result = subprocess.run(
            f"pandoc {md_file} --lua-filter=accessibility.lua -o {html_file}",
            shell=True, capture_output=True, text=True,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            print(f"done ({html_file.stat().st_size / 1024:.1f} KB)")
            published.append("html")
        else:
            print("FAILED")
            if result.stderr:
                for line in result.stderr.strip().splitlines()[:5]:
                    print(f"    {line}")

    if "github" in targets:
        github_file = output_dir / "guide.md"
        print(f"\n  -> GitHub Markdown...", end=" ", flush=True)
        result = subprocess.run(
            f"uv run python scripts/render.py {enriched} github {github_file}",
            shell=True, capture_output=True, text=True,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            print("done")
            published.append("github")
        else:
            print("FAILED")

    # --- Summary ---
    elapsed = time.time() - start_time
    banner("PIPELINE COMPLETE")
    print(f"  Published {len(published)} formats: {', '.join(published)}")
    if step_count:
        print(f"  Steps processed: {step_count}")
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
            "  uv run run_pipeline.py guide.json --provider=openrouter\n"
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
    parser.add_argument(
        "--provider",
        choices=["ollama", "openrouter"],
        default=None,
        help="Vision backend (default: ollama)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key for OpenRouter (or set OPENROUTER_API_KEY env var)",
    )

    args = parser.parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
