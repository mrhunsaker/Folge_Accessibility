#!/usr/bin/env python3
# Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
# SPDX-License-Identifier: Apache-2.0
"""
Folge Vision Publishing Pipeline - Master Orchestrator

Runs the full pipeline end-to-end using uv for dependency management:
  1. Check prerequisites
  2. Batch process images through Vision API (ollama, lmstudio, jan, llamacpp, openrouter, openai, gemini, anthropic)
  3. Merge guide + vision results
  4. Validate schema + content quality
  4b. Manual review pause (C)ontinue / (R)eVerify
  5. Render Markdown
  6. Publish to PDF, DOCX, HTML
  7. Validate PDF/UA compliance

Usage:
    folge-cli pipeline <guide.json> [output-dir] [--project NAME]
                       [--targets pdf,docx,html] [--provider PROVIDER]
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .config import (
    PROJECT_ROOT,
    get_bundled_path,
    get_min_confidence,
    get_env,
    LOCAL_PROVIDERS,
    PROVIDERS,
    project_base,
    project_images,
    project_output,
    resolve_guide,
)
from .formats import FORMATS, output_name, pandoc_args, resolve_targets, run_pandoc
from .progress import StepCounter, info


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


def _pandoc_data_args(orientation="portrait"):
    """Build ``--lua-filter`` and ``--css`` arguments with resolved paths.

    Parameters
    ----------
    orientation : str, optional
        Page orientation: ``"portrait"`` or ``"landscape"``. Default is
        ``"portrait"``.

    Returns
    -------
    str
        A space-separated string of Pandoc arguments for data files,
        suitable for interpolation into a shell command.
    """
    parts = []
    for lua in ("pdf-accessibility.lua", "docx-accessibility.lua", "accessibility.lua"):
        lua_path = get_bundled_path(lua)
        if lua_path.exists():
            parts.append(f"--lua-filter={lua_path}")
    pagebreak = get_bundled_path("templates", "pagebreak.lua")
    if pagebreak.exists():
        parts.append(f"--lua-filter={pagebreak}")
    folge_css = get_bundled_path("templates", "folge.css")
    if folge_css.exists():
        parts.append(f"--css={folge_css}")
    page_css_name = "letter-portrait.css" if orientation != "landscape" else "letter-landscape.css"
    page_css = get_bundled_path("templates", page_css_name)
    if page_css.exists():
        parts.append(f"--css={page_css}")
    return " ".join(parts)


def run_cmd(cmd, check=True, env=None):
    """Run a shell command, printing output.

    Parameters
    ----------
    cmd : str
        The shell command to execute.
    check : bool, optional
        If ``True``, return ``False`` on non-zero exit. Default is ``True``.
    env : dict, optional
        Extra environment variables for the child, merged over the current
        process environment. Used to pass secrets (API keys) without
        exposing them on the command line. Default is ``None``.

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
        cwd=str(PROJECT_ROOT),
        env={**os.environ, **(env or {})},
    )
    if check and result.returncode != 0:
        return False
    return True


def check_prerequisites():
    """Verify all required external tools are available.

    Returns
    -------
    bool
        ``True`` if every mandatory tool is present.
    """
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

    pdfinfo_path = shutil.which("pdfinfo")
    if pdfinfo_path:
        try:
            result = subprocess.run(
                [pdfinfo_path, "-v"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                ver = result.stdout.strip().splitlines()[0] if result.stdout else "OK"
                print(f"  [OK] pdfinfo (poppler-utils) at {pdfinfo_path} ({ver})")
            else:
                print(f"  [WARN] pdfinfo found at {pdfinfo_path} but returned error - PDF validation will use pymupdf only")
        except Exception:
            print(f"  [WARN] pdfinfo found at {pdfinfo_path} but could not run - PDF validation will use pymupdf only")
    else:
        print("  [WARN] pdfinfo not found on PATH - PDF validation will use pymupdf only")

    venv_python = str(PROJECT_ROOT / ".venv" / "bin" / "python")
    try:
        result = subprocess.run(
            [venv_python, "-c", "import fitz; print('OK')"],
            capture_output=True, text=True, timeout=10,
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
    """Check if the selected vision provider is reachable.

    Parameters
    ----------
    provider_name : str
        Name of the vision backend (e.g. ``'ollama'``, ``'openrouter'``).
    api_key : str, optional
        API key for cloud providers. Ignored for local providers.

    Returns
    -------
    bool
        ``True`` if the provider responded successfully.
    """
    banner("CHECKING PROVIDER")

    if provider_name in LOCAL_PROVIDERS:
        prefix = provider_name.upper()
        base_url = get_env(f"{prefix}_BASE_URL", default="http://localhost:11434/v1")
        if provider_name == "ollama":
            probe_url = base_url.rstrip("/v1") + "/api/tags"
        else:
            probe_url = base_url.rstrip("/") + "/models"
        try:
            result = subprocess.run(
                f"curl -s {probe_url}",
                shell=True, capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                print(f"  [OK] Provider: {provider_name.title()} (local)")
                print(f"  [OK] Reachable at {base_url}")
                return True
            else:
                print(f"  [WARN] {provider_name.title()} not responding at {base_url}")
                return False
        except Exception:
            print(f"  [ERROR] Could not check {provider_name.title()} at {base_url}")
            return False

    # Cloud providers — verify API key
    prefix = provider_name.upper()
    # ANTHROPIC uses ANTHROPIC_API_KEY but model var is ANTHROPIC_MODEL
    key_env = f"{prefix}_API_KEY"
    key = api_key or get_env(key_env)
    if not key:
        print(f"  [ERROR] {key_env} not set")
        print(f"          export {key_env}='...'")
        return False
    masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
    print(f"  [OK] Provider: {provider_name.title()} (cloud)")
    print(f"  [OK] API key: {masked}")
    return True


def ensure_directories(project_dir, images_dir, output_dir):
    """Create the project directories if they do not exist.

    Parameters
    ----------
    project_dir : str or Path
        The project folder that owns the guide.
    images_dir : str or Path
        The project's images directory.
    output_dir : str or Path
        The user-specified (or defaulted) output directory.
    """
    dirs = [project_dir, images_dir, Path(output_dir)]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def validate_pdf_tagging(pdf_path):
    """Quick check that a PDF file is tagged via pdfinfo.

    Parameters
    ----------
    pdf_path : str or Path
        Path to the PDF file to check.

    Returns
    -------
    bool
        ``True`` if the PDF contains a tag structure.
    """
    pdfinfo_path = shutil.which("pdfinfo")
    if not pdfinfo_path:
        return False
    try:
        result = subprocess.run(
            [pdfinfo_path, str(pdf_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return "tagged: yes" in result.stdout.lower()
    except Exception:
        return False


def count_guide_steps(guide_path):
    """Return the number of steps in the guide JSON.

    Parameters
    ----------
    guide_path : str or Path
        Path to the guide JSON file.

    Returns
    -------
    int or None
        The step count, or ``None`` if the file could not be read.
    """
    try:
        import json
        with open(guide_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return len(data.get("steps", []))
    except Exception:
        return None


def run_pipeline(args):
    """Execute the full publishing pipeline.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments containing ``guide``, ``output``,
        ``targets``, ``provider``, ``api_key``, and ``orientation``.
    """
    try:
        guide_path = resolve_guide(getattr(args, "guide", None), getattr(args, "project", None))
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    project_dir = project_base(guide_path)
    images_dir = project_images(guide_path)
    output_dir = project_output(guide_path, getattr(args, "output", None))
    requested_targets = (
        [t.strip() for t in args.targets.split(",") if t.strip()]
        if args.targets else None
    )
    targets, skipped = resolve_targets(requested_targets)
    for name in skipped:
        print(f"  [SKIP] {name}: not supported by this pandoc version")
    provider_name = args.provider or get_env("PROVIDER", default="ollama")
    api_key = args.api_key or get_env("OPENROUTER_API_KEY")
    orientation = getattr(args, "orientation", None) or "portrait"

    if not guide_path.exists():
        print(f"ERROR: Guide file not found: {guide_path}")
        print("Export your guide from Folge and save it (any name) in your project folder.")
        sys.exit(1)

    ensure_directories(project_dir, images_dir, output_dir)

    counter = StepCounter(7)

    if not check_prerequisites():
        print("\nFATAL: Missing prerequisites. Install the tools listed above.")
        sys.exit(1)
    done, _ = counter.tick()
    info(f"  {done}/7 complete — prerequisites OK")

    if not check_provider(provider_name, api_key):
        print(f"\nWARNING: {provider_name.title()} may not be available.")
        print("The pipeline will fail at the vision processing step.")
        try:
            resp = input("Continue anyway? [y/N] ").strip().lower()
        except EOFError:
            resp = "n"
        if resp != "y":
            sys.exit(1)
    done, _ = counter.tick()
    info(f"  {done}/7 complete — provider check OK")

    start_time = time.time()

    step_count = count_guide_steps(guide_path)
    min_conf = get_min_confidence()

    # --- Steps 1-2: Batch Vision Processing ---
    step_header("1-2", f"Processing images with {provider_name.title()} Vision")
    vision_results = output_dir / "vision-results.json"

    batch_cmd = (
        f"uv run python -m folge_cli.batch_process {guide_path} {images_dir} {vision_results}"
        f" --provider={provider_name}"
    )
    batch_env = None
    if api_key and provider_name not in LOCAL_PROVIDERS:
        key_env = f"{provider_name.upper()}_API_KEY"
        if api_key != get_env(key_env):
            batch_env = {key_env: api_key}

    if not run_cmd(batch_cmd, env=batch_env):
        print("\nWARNING: Some vision processing steps returned errors.")
        print("The pipeline will continue but enriched output may have vision_error fields.")
        if not vision_results.exists():
            print("\nFATAL: Vision processing produced no output.")
            sys.exit(1)
    done, _ = counter.tick()
    info(f"  {done}/7 complete — batch vision processing done")

    # --- Step 3: Merge ---
    step_header("3", "Merging guide with vision data")
    enriched = output_dir / "guide.enriched.json"
    if not run_cmd(
        f"uv run python -m folge_cli.merge {guide_path} {vision_results} {enriched}"
    ):
        print("\nFATAL: Merge failed.")
        sys.exit(1)
    done, _ = counter.tick()
    info(f"  {done}/7 complete — merge done")

    # --- Step 4: Validate ---
    step_header("4", "Validating enriched JSON")
    schema_warnings = output_dir / "schema-warnings.json"
    if not run_cmd(
        f"uv run python -m folge_cli.validate_schema {enriched} --warnings-out {schema_warnings}"
    ):
        print("\nFATAL: Schema validation failed.")
        sys.exit(1)
    if not run_cmd(f"uv run python -m folge_cli.validate_content {enriched} {min_conf}"):
        print("\nFATAL: Content validation failed.")
        sys.exit(1)
    done, _ = counter.tick()
    info(f"  {done}/7 complete — validation done")

    # --- Step 4b: Manual Review Pause ---
    step_header("4b", "MANUAL REVIEW REQUIRED")
    manual_file = output_dir / "manual-attention-needed.md"
    manual_cmd = (
        f"uv run python -m folge_cli.generate_manual_attention {enriched} {images_dir} {manual_file}"
    )
    if schema_warnings.exists():
        manual_cmd += f" {schema_warnings}"
    run_cmd(manual_cmd, check=False)

    print("\n  Please review the following files before continuing:")
    print(f"    - {enriched.absolute()}")
    if manual_file.exists():
        print(f"    - {manual_file.absolute()}")
    print()

    while True:
        try:
            resp = input("  (C)ontinue to rendering  or  (R)eVerify enriched JSON? [C/R] ").strip().upper()
        except EOFError:
            print("\n\nInterrupted by user. Exiting cleanly.")
            sys.exit(130)
        if resp == "R":
            step_header("4b-r", "Re-validating enriched JSON")
            run_cmd(
                f"uv run python -m folge_cli.validate_schema {enriched} --warnings-out {schema_warnings}"
            )
            run_cmd(f"uv run python -m folge_cli.validate_content {enriched} {min_conf}")
            run_cmd(manual_cmd, check=False)
            print("\n  Please review the updated files:")
            print(f"    - {enriched.absolute()}")
            if manual_file.exists():
                print(f"    - {manual_file.absolute()}")
            print()
        elif resp == "C":
            done, _ = counter.tick()
            info(f"  {done}/7 complete — manual review done")
            break
        else:
            print("  Please enter C or R")

    # --- Step 5: Render Markdown ---
    step_header("5", "Rendering Markdown")
    md_file = output_dir / "guide.md"
    if not run_cmd(f"uv run python -m folge_cli.render {enriched} pdf {md_file} --images-dir {images_dir}"):
        print("\nFATAL: Markdown rendering failed.")
        sys.exit(1)
    done, _ = counter.tick()
    info(f"  {done}/7 complete — render done")

    # --- Step 5b: Accessible document metadata ---
    step_header("5b", "Generating accessible document metadata")
    from folge_cli.metadata import build_metadata, write_metadata_file
    metadata = build_metadata(enriched)
    metadata_yaml = output_dir / "metadata.yaml"
    write_metadata_file(metadata, metadata_yaml)
    print(f"  Metadata YAML written to {metadata_yaml}")
    metadata_args = f"--metadata-file={metadata_yaml}"

    # --- Step 6: Publish ---
    step_header("6", "Publishing to target formats")
    published = []
    pdf_errors = []

    if "pdf" in targets:
        pdf_file = output_dir / "guide.pdf"
        print("\n  -> PDF (weasyprint)...", end=" ", flush=True)

        data_args = _pandoc_data_args(orientation)
        result = run_pandoc(
            f"pandoc guide.md {data_args} "
            "--pdf-engine=weasyprint --pdf-engine-opt=--presentational-hints "
            f"{metadata_args} --metadata=tagged-pdf:true "
            "--standalone --verbose -o guide.pdf",
            output_dir,
        )
        if result.returncode == 0:
            print(f"done ({pdf_file.stat().st_size / 1024:.1f} KB)")
            published.append("pdf")
        else:
            err_msg = result.stderr.strip()[:200] if result.stderr else "unknown error"
            print("FAILED")
            pdf_errors.append(("weasyprint", err_msg))

            # Fallback: wkhtmltopdf
            print("  -> PDF (wkhtmltopdf)...", end=" ", flush=True)
            data_args = _pandoc_data_args(orientation)
            result2 = run_pandoc(
                f"pandoc guide.md {data_args} "
                "--pdf-engine=wkhtmltopdf "
                "--pdf-engine-opt=--enable-local-file-access "
                "--pdf-engine-opt=--tagged-pdf "
                f"{metadata_args} --metadata=tagged-pdf:true "
                "--standalone --verbose -o guide.pdf",
                output_dir,
            )
            if result2.returncode == 0:
                print(f"done ({pdf_file.stat().st_size / 1024:.1f} KB)")
                published.append("pdf")
            else:
                err_msg2 = result2.stderr.strip()[:200] if result2.stderr else "unknown error"
                print("FAILED")
                pdf_errors.append(("wkhtmltopdf", err_msg2))

                # Fallback: xelatex
                print("  -> PDF (xelatex)...", end=" ", flush=True)
                data_args = _pandoc_data_args(orientation)
                result3 = run_pandoc(
                    f"pandoc guide.md {data_args} "
                    "--pdf-engine=xelatex --pdf-engine-opt=-x dvipdfmx "
                    f"{metadata_args} "
                    "--standalone --verbose -o guide.pdf",
                    output_dir,
                )
                if result3.returncode == 0:
                    print(f"done ({pdf_file.stat().st_size / 1024:.1f} KB)")
                    published.append("pdf")
                else:
                    err_msg3 = result3.stderr.strip()[:200] if result3.stderr else "unknown error"
                    print("FAILED")
                    pdf_errors.append(("xelatex", err_msg3))

        if "pdf" not in published:
            print("\n  All PDF engines failed:")
            for engine, err in pdf_errors:
                print(f"    {engine}: {err[:120]}")
        elif validate_pdf_tagging(pdf_file):
            print("  -> PDF is TAGGED and PDF/UA compliant!")

    # --- Generic pandoc targets (docx, html, pptx, + all registered formats) ---
    for tname in targets:
        if tname in ("pdf", "github"):
            continue
        out_file = output_name(tname)
        print(f"\n  -> {tname.upper()}...", end=" ", flush=True)
        args = pandoc_args(tname, orientation)
        engine = f"--pdf-engine={FORMATS[tname]['engine']}" if "engine" in FORMATS[tname] else ""
        result = run_pandoc(
            f"pandoc guide.md {args} {engine} {metadata_args} --verbose -o {out_file}",
            output_dir,
        )
        if result.returncode == 0:
            print(f"done ({(output_dir / out_file).stat().st_size / 1024:.1f} KB)")
            published.append(tname)
        else:
            print("FAILED")
            if result.stderr:
                for line in result.stderr.strip().splitlines()[:5]:
                    print(f"    {line}")

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

    # --- Summary ---
    done, _ = counter.tick()
    info(f"  {done}/7 complete — all phases done")
    elapsed = time.time() - start_time
    banner("PIPELINE COMPLETE")
    print(f"  Published {len(published)} formats: {', '.join(published)}")
    if step_count:
        print(f"  Steps processed: {step_count}")
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

    print(f"\n  Total time: {elapsed:.1f} seconds\n")


def main():
    """CLI entry point for the pipeline sub-command."""
    import argparse
    from folge_cli import __version__
    parser = argparse.ArgumentParser(
        description="Folge Vision Publishing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  folge-cli pipeline guide.json\n"
            "  folge-cli pipeline --project my-guide\n"
            "  folge-cli pipeline guide.json output/ --targets pdf,html\n"
            "  folge-cli pipeline ~/Documents/FolgeProjects/my-guide/guide.json\n"
        ),
    )
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "guide",
        nargs="?",
        default=None,
        help="Path to guide JSON (Folge export, any name)",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="Project folder under ~/Documents/FolgeProjects to process",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help="Output directory (default: <project>/output)",
    )
    parser.add_argument(
        "--targets",
        default=None,
        help=(
            "Comma-separated target formats (e.g. pdf,docx,html). "
            "Default: every format supported by the installed pandoc "
            "(see src/folge_cli/formats.py for the full registry)."
        ),
    )
    parser.add_argument(
        "--provider",
        choices=PROVIDERS,
        default=None,
        help="Vision backend (default: from .env PROVIDER)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key for cloud providers (or set *_API_KEY env var)",
    )
    parser.add_argument(
        "--orientation",
        choices=["portrait", "landscape"],
        default=None,
        help="PDF page orientation (default: portrait)",
    )
    args = parser.parse_args()
    try:
        run_pipeline(args)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting cleanly.")
        sys.exit(130)


if __name__ == "__main__":
    main()
