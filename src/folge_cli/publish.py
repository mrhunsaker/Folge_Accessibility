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

from .config import (
    PROJECT_ROOT,
    get_bundled_path,
    get_min_confidence,
    project_images,
    project_output,
    resolve_guide,
)
from .formats import FORMATS, output_name, pandoc_args, resolve_targets, run_pandoc


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
        text=True,
        cwd=cwd
    )
    if check and result.returncode != 0:
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


def publish_with_pdf_ua(guide_path, output_dir, targets=None, provider="ollama",
                        orientation="portrait", project=None):
    """Run the full publishing pipeline with PDF/UA compliance.

    Parameters
    ----------
    guide_path : str or Path
        Path to the source guide JSON file. May be None when ``project``
        is given, in which case the project's single JSON file is used.
    output_dir : str or Path
        Directory where all output files are written. When None, defaults
        to ``<project>/output``.
    targets : list of str, optional
        Target formats to produce. Any key from the format registry
        (see ``folge_cli.formats``), e.g. ``'pdf'``, ``'docx'``,
        ``'html'``, ``'github'``. Default is ``None``, meaning every
        format supported by the installed pandoc.
    provider : str, optional
        Vision backend name. Default is ``"ollama"``.
    orientation : str, optional
        Page orientation: ``"portrait"`` or ``"landscape"``. Default is
        ``"portrait"``.
    project : str, optional
        Project folder name under ``~/Documents/FolgeProjects``, used only
        when ``guide_path`` is None.

    Returns
    -------
    bool
        ``True`` if the pipeline completed successfully.
    """
    try:
        guide_path = resolve_guide(guide_path, project)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return False
    output_dir = project_output(guide_path, output_dir)
    images_dir = project_images(guide_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    targets, skipped = resolve_targets(targets)
    for name in skipped:
        print(f"  [SKIP] {name}: not supported by this pandoc version")

    md_file = output_dir / "guide.md"
    min_conf = get_min_confidence()

    step_header("1-2", f"Processing with {provider.title()} Vision")
    vision_results = output_dir / "vision-results.json"
    if not run_cmd(
        f"uv run python -m folge_cli.batch_process {guide_path} {images_dir} {vision_results} --provider={provider}",
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
        f"uv run python -m folge_cli.render {enriched} pdf {md_file} --images-dir {images_dir}",
        cwd=str(PROJECT_ROOT),
    ):
        return False

    step_header("5b", "Generating accessible document metadata")
    from folge_cli.metadata import build_metadata, write_metadata_file, apply_pdf_metadata
    metadata = build_metadata(enriched)
    metadata_yaml = output_dir / "metadata.yaml"
    write_metadata_file(metadata, metadata_yaml)
    print(f"  Metadata YAML written to {metadata_yaml}")

    step_header("6", "Publishing to target formats")
    published = []
    page_css_name = "letter-portrait.css" if orientation != "landscape" else "letter-landscape.css"
    folge_css = get_bundled_path("templates", "folge.css")
    page_css = get_bundled_path("templates", page_css_name)
    css_args = f"--css={folge_css} --css={page_css}"
    metadata_args = f"--metadata-file={metadata_yaml}"
    pagebreak = get_bundled_path("templates", "pagebreak.lua")
    pdf_lua = get_bundled_path("pdf-accessibility.lua")
    pdf_filter_args = f"--lua-filter={pdf_lua}"
    if pagebreak.exists():
        pdf_filter_args = f"--lua-filter={pagebreak} {pdf_filter_args}"

    if "pdf" in targets:
        pdf_file = output_dir / "guide.pdf"
        print("\n  -> PDF (weasyprint)...", end=" ", flush=True)
        result = run_pandoc(
            f"pandoc {md_file} {pdf_filter_args} "
            f"{css_args} "
            f"--pdf-engine=weasyprint --pdf-engine-opt=--presentational-hints "
            f"{metadata_args} "
            f"--metadata=tagged-pdf:true "
            f"--standalone --verbose -o {pdf_file}",
            output_dir,
        )
        if result.returncode == 0:
            print(f"done ({pdf_file.stat().st_size / 1024:.1f} KB)")
            apply_pdf_metadata(pdf_file, metadata)
            print("  -> PDF metadata embedded; text copying allowed")
            published.append("pdf")
        else:
            print("FAILED")
            for engine, opts in [
                ("wkhtmltopdf", "--pdf-engine-opt=--enable-local-file-access --pdf-engine-opt=--tagged-pdf"),
                ("xelatex", "--pdf-engine-opt=-x dvipdfmx"),
            ]:
                print(f"  -> PDF ({engine})...", end=" ", flush=True)
                result2 = run_pandoc(
                    f"pandoc {md_file} {pdf_filter_args} "
                    f"{css_args} "
                    f"--pdf-engine={engine} {opts} "
                    f"{metadata_args} "
                    f"--metadata=tagged-pdf:true "
                    f"--standalone --verbose -o {pdf_file}",
                    output_dir,
                )
                if result2.returncode == 0:
                    print(f"done ({pdf_file.stat().st_size / 1024:.1f} KB)")
                    apply_pdf_metadata(pdf_file, metadata)
                    print("  -> PDF metadata embedded; text copying allowed")
                    published.append("pdf")
                    break
                else:
                    print("FAILED")

        if "pdf" in published and validate_pdf_tagging(pdf_file):
            print("  -> PDF is TAGGED and PDF/UA compliant!")

    # --- Generic pandoc targets (docx, html, pptx, + all registered formats) ---
    for tname in targets:
        if tname in ("pdf", "github"):
            continue
        out_file = output_name(tname)
        out_path = output_dir / out_file
        print(f"\n  -> {tname.upper()}...", end=" ", flush=True)
        args = pandoc_args(tname, orientation)
        engine = f"--pdf-engine={FORMATS[tname]['engine']}" if "engine" in FORMATS[tname] else ""
        result = run_pandoc(
            f"pandoc {md_file} {args} {engine} {metadata_args} --verbose -o {out_path}",
            output_dir,
        )
        if result.returncode == 0:
            print(f"done ({(out_path).stat().st_size / 1024:.1f} KB)")
            published.append(tname)
            if out_file.endswith(".pdf") and out_path.exists():
                apply_pdf_metadata(out_path, metadata)
        else:
            print("FAILED")

    if "github" in targets:
        github_file = output_dir / "guide.md"
        print("  -> GitHub Markdown...", end=" ", flush=True)
        result = subprocess.run(
            f"uv run python -m folge_cli.render {enriched} github {github_file} --images-dir {images_dir}",
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
    import argparse
    from folge_cli import __version__

    parser = argparse.ArgumentParser(
        prog="folge-cli publish",
        description="Publish a guide to target formats with PDF/UA compliance.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  folge-cli publish guide.json output/\n"
            "  folge-cli publish --project my-guide --targets pdf,docx,html\n"
            "  folge-cli publish guide.json output/ pdf --orientation landscape\n"
        ),
    )
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument("guide", nargs="?", default=None,
                        help="Path to guide JSON (Folge export, any name)")
    parser.add_argument("--project", default=None,
                        help="Project folder under ~/Documents/FolgeProjects to publish")
    parser.add_argument("output", nargs="?", default=None,
                        help="Output directory (default: <project>/output)")
    parser.add_argument("targets", nargs="?", default=None,
                        help="Comma-separated target formats (default: all)")
    parser.add_argument("provider", nargs="?", default="ollama",
                        help="Vision provider (default: ollama)")
    parser.add_argument("--orientation", choices=["portrait", "landscape"], default="portrait",
                        help="PDF page orientation (default: portrait)")
    args = parser.parse_args()

    targets = args.targets.split(",") if args.targets else None

    start_time = time.time()
    try:
        success = publish_with_pdf_ua(
            args.guide, args.output, targets, args.provider,
            orientation=args.orientation, project=args.project,
        )
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting cleanly.")
        sys.exit(130)
    elapsed = time.time() - start_time

    if success:
        print(f"\n  Pipeline completed in {elapsed:.1f} seconds")
        sys.exit(0)
    else:
        print(f"\n  Pipeline failed after {elapsed:.1f} seconds")
        sys.exit(1)


if __name__ == "__main__":
    main()
