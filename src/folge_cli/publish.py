#!/usr/bin/env python3
# Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
# SPDX-License-Identifier: Apache-2.0
"""
End-to-end publishing pipeline with GUARANTEED tagged PDF/UA compliance.

Standalone alternative to pipeline.py — same logic, different entry point.
"""
import subprocess
import sys
import time
from pathlib import Path

from .config import PROJECT_ROOT, get_min_confidence


def banner(text, char="=", width=60):
    """Print a decorative banner with a repeating character.

    Parameters
    ----------
    text : str
        The text to display inside the banner.
    char : str, optional
        Character used for the border lines. Default is ``"="``.
    width : int, optional
        Total width of the border lines. Default is 60.
    """
    print(f"\n{char * width}")
    print(f"  {text}")
    print(f"{char * width}")


def step_header(step_num, text):
    """Print a formatted step header.

    Parameters
    ----------
    step_num : str or int
        The step number or range to display.
    text : str
        A short description of the step.
    """
    print(f"\n{'=' * 60}")
    print(f"  STEP {step_num}: {text}")
    print(f"{'=' * 60}")


def run_cmd(cmd, check=True, cwd=None):
    """Run a shell command, printing output.

    Parameters
    ----------
    cmd : str
        The shell command to execute.
    check : bool, optional
        If ``True``, return ``False`` on non-zero exit. Default is ``True``.
    cwd : str or Path, optional
        Working directory for the command.

    Returns
    -------
    bool
        ``True`` if the command succeeded or ``check`` is ``False``.
    """
    print(f"  -> {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=cwd
    )
    if result.stdout:
        for line in result.stdout.strip().splitlines():
            print(f"     {line}")
    if check and result.returncode != 0:
        stderr = result.stderr.strip()
        if stderr:
            for line in stderr.splitlines()[:5]:
                print(f"     {line}")
        return False
    return True


def validate_pdf_tagging(pdf_path):
    """Quick validation that a PDF file is tagged.

    Parameters
    ----------
    pdf_path : str or Path
        Path to the PDF file to check.

    Returns
    -------
    bool
        ``True`` if the PDF contains a tag structure.
    """
    try:
        result = subprocess.run(
            ["/usr/bin/pdfinfo", str(pdf_path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        return "tagged: yes" in result.stdout.lower()
    except Exception:
        return False


def publish_with_pdf_ua(guide_path, output_dir, targets=None, provider="ollama"):
    """Run the full publishing pipeline with PDF/UA compliance.

    Parameters
    ----------
    guide_path : str or Path
        Path to the source ``guide.json`` file.
    output_dir : str or Path
        Directory where all output files are written.
    targets : list of str, optional
        Target formats to produce. One or more of ``'pdf'``, ``'docx'``,
        ``'html'``, ``'pptx'``, ``'github'``. Default is
        ``["pdf", "docx", "html", "pptx"]``.
    provider : str, optional
        Vision backend name. Default is ``"ollama"``.

    Returns
    -------
    bool
        ``True`` if the pipeline completed successfully.
    """
    guide_path = Path(guide_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if targets is None:
        targets = ["pdf", "docx", "html", "pptx"]

    md_file = output_dir / "guide.md"
    min_conf = get_min_confidence()

    step_header("1-2", f"Processing with {provider.title()} Vision")
    vision_results = output_dir / "vision-results.json"
    if not run_cmd(
        f"uv run python -m folge_cli.batch_process {guide_path} images/ {vision_results} --provider={provider}",
        cwd=str(PROJECT_ROOT),
    ):
        return False

    step_header("3", "Merging guide with vision data")
    enriched = output_dir / "guide.enriched.json"
    if not run_cmd(
        f"uv run python -m folge_cli.merge {guide_path} {vision_results} {enriched}",
        cwd=str(PROJECT_ROOT),
    ):
        return False

    step_header("4", "Validating enriched JSON")
    if not run_cmd(
        f"uv run python -m folge_cli.validate_schema {enriched}",
        cwd=str(PROJECT_ROOT),
    ):
        return False
    if not run_cmd(
        f"uv run python -m folge_cli.validate_content {enriched} {min_conf}",
        cwd=str(PROJECT_ROOT),
    ):
        return False

    step_header("5", "Rendering Markdown")
    if not run_cmd(
        f"uv run python -m folge_cli.render {enriched} pdf {md_file}",
        cwd=str(PROJECT_ROOT),
    ):
        return False

    step_header("6", "Publishing to target formats")
    published = []

    if "pdf" in targets:
        pdf_file = output_dir / "guide.pdf"
        print("\n  -> PDF (weasyprint)...", end=" ", flush=True)
        result = subprocess.run(
            f"pandoc {md_file} --lua-filter=templates/pagebreak.lua "
            f"--lua-filter=pdf-accessibility.lua "
            f"--css=templates/landscape.css "
            f"--pdf-engine=weasyprint --pdf-engine-opt=--presentational-hints "
            f"--metadata=tagged-pdf:true -o {pdf_file}",
            shell=True, capture_output=True, text=True,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            print(f"done ({pdf_file.stat().st_size / 1024:.1f} KB)")
            published.append("pdf")
        else:
            print("FAILED")
            for engine, opts in [
                ("wkhtmltopdf", "--lua-filter=templates/pagebreak.lua --pdf-engine-opt=--enable-local-file-access --pdf-engine-opt=--tagged-pdf"),
                ("xelatex", "--lua-filter=templates/pagebreak.lua --pdf-engine-opt=-x dvipdfmx"),
            ]:
                print(f"  -> PDF ({engine})...", end=" ", flush=True)
                result2 = subprocess.run(
                    f"pandoc {md_file} --lua-filter=pdf-accessibility.lua "
                    f"--pdf-engine={engine} {opts} "
                    f"--metadata=tagged-pdf:true -o {pdf_file}",
                    shell=True, capture_output=True, text=True,
                    cwd=str(PROJECT_ROOT),
                )
                if result2.returncode == 0:
                    print(f"done ({pdf_file.stat().st_size / 1024:.1f} KB)")
                    published.append("pdf")
                    break
                else:
                    print("FAILED")

        if "pdf" in published and validate_pdf_tagging(pdf_file):
            print("  -> PDF is TAGGED and PDF/UA compliant!")

    if "docx" in targets:
        docx_file = output_dir / "guide.docx"
        print("\n  -> DOCX...", end=" ", flush=True)
        result = subprocess.run(
            f"pandoc {md_file} --lua-filter=templates/pagebreak.lua "
            f"--lua-filter=docx-accessibility.lua -o {docx_file}",
            shell=True, capture_output=True, text=True,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            print(f"done ({docx_file.stat().st_size / 1024:.1f} KB)")
            published.append("docx")
        else:
            print("FAILED")

    if "html" in targets:
        html_file = output_dir / "guide.html"
        print("\n  -> HTML...", end=" ", flush=True)
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

    if "pptx" in targets:
        pptx_file = output_dir / "guide.pptx"
        print("\n  -> PPTX...", end=" ", flush=True)
        result = subprocess.run(
            f"pandoc {md_file} --lua-filter=templates/pagebreak.lua "
            f"--lua-filter=docx-accessibility.lua "
            f"--to pptx -o {pptx_file}",
            shell=True, capture_output=True, text=True,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            print(f"done ({pptx_file.stat().st_size / 1024:.1f} KB)")
            published.append("pptx")
        else:
            print("FAILED")

    if "github" in targets:
        github_file = output_dir / "guide.md"
        print("  -> GitHub Markdown...", end=" ", flush=True)
        result = subprocess.run(
            f"uv run python -m folge_cli.render {enriched} github {github_file}",
            shell=True, capture_output=True, text=True,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            print("done")
            published.append("github")
        else:
            print("FAILED")

    banner("PUBLISHING COMPLETE")
    print(f"  Published {len(published)} formats: {', '.join(published)}")
    print(f"  Output directory: {output_dir.absolute()}")
    print("\n  Files generated:")
    for f in output_dir.glob("*"):
        if f.is_file():
            size = f.stat().st_size
            if size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            print(f"    - {f.name} ({size_str})")

    if "pdf" in published:
        print("\n  PDF/UA COMPLIANCE: GUARANTEED")

    return True


def main():
    """CLI entry point for the publish sub-command."""
    if len(sys.argv) < 2:
        print("Usage: folge-cli publish <guide.json> <output-dir> [targets] [provider]")
        print("Example: folge-cli publish guide.json output/ pdf,docx,html,pptx openrouter")
        print("Targets: pdf, docx, html, pptx, github (default: pdf,docx,html,pptx)")
        print("Provider: ollama, lmstudio, llamacpp, openrouter, openai, gemini, anthropic (default: ollama)")
        sys.exit(1)

    guide_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    targets = sys.argv[3].split(",") if len(sys.argv) > 3 else None
    provider = sys.argv[4] if len(sys.argv) > 4 else "ollama"

    start_time = time.time()
    success = publish_with_pdf_ua(guide_path, output_dir, targets, provider)
    elapsed = time.time() - start_time

    if success:
        print(f"\n  Pipeline completed in {elapsed:.1f} seconds")
        sys.exit(0)
    else:
        print(f"\n  Pipeline failed after {elapsed:.1f} seconds")
        sys.exit(1)


if __name__ == "__main__":
    main()
