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

If an enriched JSON already exists in the output directory (from a prior
run), the pipeline offers to reuse it and skip stages 1-3 (vision
processing + merge) entirely, jumping straight to validation and manual
review. Pass --skip-vision to do this non-interactively.

--first-step <stage> resumes the pipeline from a specific stage
(1 | 3 | 4 | 4b | 5 | 5b | 6), skipping every earlier stage and its
interactive prompts. When resuming, the intermediate artifacts (enriched
JSON, vision results, Markdown, metadata) are discovered from the output
directory by their on-disk names — so a run from an earlier date is picked
up correctly even though today's date differs.

Usage:
    folge-cli pipeline <guide.json> [output-dir] [--project NAME]
                       [--targets pdf,docx,html] [--provider PROVIDER]
                       [--skip-vision] [--first-step STEP]
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
    guide_stem,
)
from .formats import FORMATS, output_name, pandoc_args, resolve_targets, run_pandoc
from .progress import StepCounter, info

# Canonical pipeline step identifiers in execution order.
# Each entry matches the step_num shown in step_header() calls.
_PIPELINE_STEPS = ["1", "3", "4", "4b", "5", "5b", "6"]


def _step_order(step_id):
    """Return the ordinal position of a pipeline step.

    Parameters
    ----------
    step_id : str
        A pipeline step identifier (e.g. ``"4b"``).

    Returns
    -------
    int
        Ordinal position (0-based) of the step, or ``len(_PIPELINE_STEPS)``
        if the step is not found.
    """
    try:
        return _PIPELINE_STEPS.index(step_id)
    except ValueError:
        return len(_PIPELINE_STEPS)


def _discover_file(output_dir, *suffixes):
    """Find an existing output file matching any of the given suffixes.

    When resuming mid-pipeline (``--first-step``), the artifacts from a
    previous run may carry an older date in their names (e.g.
    ``Headings-2026-08-28.enriched.json``), so the pipeline must look them
    up on disk rather than assume the current date.

    Parameters
    ----------
    output_dir : str or Path
        Directory to search for the artifact.
    suffixes : str
        One or more filename suffixes to match. A file matches if its
        name ends with any suffix, tolerating ``-`` vs ``_`` variants.

    Returns
    -------
    Path or None
        The single matching file, or ``None`` if none is found. When
        multiple stems match, the most recently modified file is chosen.
    """
    output_dir = Path(output_dir)
    if not output_dir.is_dir():
        return None
    matches = [
        p
        for p in output_dir.iterdir()
        if p.is_file() and any(p.name.endswith(sfx) for sfx in suffixes)
    ]
    if not matches:
        return None
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]


def _discover_stem(output_dir, fallback):
    """Derive the effective run stem from existing output artifacts.

    Uses the most recently produced artifact in the output directory
    (preferring the enriched JSON, then vision results, then Markdown) so
    that files written during a resumed run share the same stem as the
    earlier run, even if that run was on a different date.

    Parameters
    ----------
    output_dir : str or Path
        Output directory to inspect.
    fallback : str
        Stem to return when no artifact is found (the guide stem).

    Returns
    -------
    str
        The discovered stem, or *fallback*.
    """
    output_dir = Path(output_dir)
    if output_dir.is_dir():
        for pattern in ("*.enriched.json", "*.vision-results.json", "*.md"):
            matches = sorted(
                (p for p in output_dir.glob(pattern) if p.is_file()),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if matches:
                return Path(matches[0].name).with_suffix("").with_suffix("")
    return fallback


def _skip_step(first_step, step_id):
    """Return whether a pipeline step should be skipped given ``--first-step``.

    A step runs when every stage before it has already run or is skipped,
    i.e. it is skipped only when it comes strictly before the chosen start.

    Parameters
    ----------
    first_step : str or None
        The ``--first-step`` value, or ``None`` for a full run.
    step_id : str
        The step identifier to test (e.g. ``"4b"``).

    Returns
    -------
    bool
        ``True`` if the step should be skipped.
    """
    if not first_step:
        return False
    return _step_order(step_id) < _step_order(first_step)


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
    stem = guide_stem(guide_path)
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

    counter = StepCounter(8)

    # --- Resolve pipeline artifact paths ---
    # Discovery-first: when resuming mid-pipeline, the artifacts from an
    # earlier run may carry a date other than today's, so look them up by
    # their on-disk names rather than assuming the current stem.  New files
    # written this run use the same discovered stem so everything stays
    # grouped with the existing folder.
    first_step = getattr(args, "first_step", None)
    art_stem = _discover_stem(output_dir, stem)
    enriched = _discover_file(output_dir, ".enriched.json") or output_dir / f"{art_stem}.enriched.json"
    vision_results = (
        _discover_file(output_dir, ".vision-results.json", "-vision-results.json", "_vision-results.json")
        or output_dir / f"{art_stem}.vision-results.json"
    )
    schema_warnings = (
        _discover_file(output_dir, ".schema-warnings.json")
        or output_dir / f"{art_stem}.schema-warnings.json"
    )
    md_file = output_dir / f"{art_stem}.md"
    manual_file = (
        _discover_file(output_dir, ".manual-attention-needed.md")
        or output_dir / f"{art_stem}.manual-attention-needed.md"
    )
    metadata_yaml = (
        _discover_file(output_dir, ".metadata.yaml")
        or output_dir / f"{art_stem}.metadata.yaml"
    )

    # --- Determine which steps to skip ---
    skip_vision = False
    if first_step:
        print(f"\n  --first-step {first_step}: starting pipeline from step {first_step}")
    elif getattr(args, "skip_vision", False):
        if not enriched.exists():
            print(f"ERROR: --skip-vision given but no enriched JSON found at {enriched}")
            sys.exit(1)
        skip_vision = True
        print(f"\n  --skip-vision: reusing existing enriched JSON at {enriched.absolute()}")
    elif enriched.exists():
        print(f"\n  Found existing enriched JSON: {enriched.absolute()}")
        try:
            resp = input(
                "  (U)se existing enriched JSON and skip vision processing"
                "  or  (R)egenerate vision data from scratch? [U/R] "
            ).strip().upper()
        except EOFError:
            resp = "R"
        skip_vision = resp == "U"

    if not check_prerequisites():
        print("\nFATAL: Missing prerequisites. Install the tools listed above.")
        sys.exit(1)
    done, _ = counter.tick()
    info(f"  {done}/8 complete — prerequisites OK")

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
    info(f"  {done}/8 complete — provider check OK")

    # When starting mid-pipeline, verify that required intermediate files exist.
    if first_step and _step_order(first_step) >= _step_order("4"):
        if not enriched.exists():
            print(f"\nFATAL: --first-step {first_step} requires enriched JSON but none found at:")
            print(f"  {enriched}")
            print("Run the full pipeline first, or use --first-step 1 to regenerate from scratch.")
            sys.exit(1)

    start_time = time.time()

    step_count = count_guide_steps(guide_path)
    min_conf = get_min_confidence()

    # --- Steps 1-2: Batch Vision Processing ---
    if _skip_step(first_step, "1") or skip_vision:
        step_header("1-2", "Skipping vision processing (reusing existing enriched JSON)")
        done, _ = counter.tick()
        info(f"  {done}/8 complete — batch vision processing skipped")
    else:
        step_header("1-2", f"Processing images with {provider_name.title()} Vision")

        batch_cmd = (
            f"uv run python -m folge_cli.batch_process {guide_path} {images_dir} {vision_results}"
            f" --provider={provider_name}"
        )
        prompt_name = getattr(args, "prompt", None)
        if prompt_name:
            from folge_cli.batch_process import get_available_prompts
            if prompt_name in get_available_prompts():
                batch_cmd += f" --prompt={prompt_name}"
            else:
                print(f"  [SKIP] Unknown prompt module '{prompt_name}'; using default prompt")
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
        info(f"  {done}/8 complete — batch vision processing done")

    # --- Step 3: Merge ---
    if _skip_step(first_step, "3") or skip_vision:
        step_header("3", "Skipping merge (reusing existing enriched JSON)")
        done, _ = counter.tick()
        info(f"  {done}/8 complete — merge skipped")
    else:
        step_header("3", "Merging guide with vision data")
        if not vision_results.exists():
            print(f"\nFATAL: --first-step {first_step} requires an existing vision-results JSON "
                  f"but none was found at:\n  {vision_results}\n"
                  "Run --first-step 1 to regenerate vision data, or --first-step 4 to "
                  "resume after merge.")
            sys.exit(1)
        if not run_cmd(
            f"uv run python -m folge_cli.merge {guide_path} {vision_results} {enriched}"
        ):
            print("\nFATAL: Merge failed.")
            sys.exit(1)
        done, _ = counter.tick()
        info(f"  {done}/8 complete — merge done")

    # --- Step 4: Validate ---
    if _skip_step(first_step, "4"):
        step_header("4", "Skipping validation")
        done, _ = counter.tick()
        info(f"  {done}/8 complete — validation skipped")
    else:
        step_header("4", "Validating enriched JSON")
        if not run_cmd(
            f"uv run python -m folge_cli.validate_schema {enriched} --warnings-out {schema_warnings}"
        ):
            print("\nFATAL: Schema validation failed.")
            sys.exit(1)
        if not run_cmd(f"uv run python -m folge_cli.validate_content {enriched} {min_conf}"):
            print("\nFATAL: Content validation failed.")
            sys.exit(1)
        done, _ = counter.tick()
        info(f"  {done}/8 complete — validation done")

    # --- Step 4b: Manual Review Pause ---
    if _skip_step(first_step, "4b"):
        step_header("4b", "Skipping manual review")
        done, _ = counter.tick()
        info(f"  {done}/8 complete — manual review skipped")
    else:
        step_header("4b", "MANUAL REVIEW REQUIRED")
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
                info(f"  {done}/8 complete — manual review done")
                break
            else:
                print("  Please enter C or R")

    # --- Step 5: Render Markdown ---
    if _skip_step(first_step, "5"):
        step_header("5", "Skipping render")
        done, _ = counter.tick()
        info(f"  {done}/8 complete — render skipped")
    else:
        step_header("5", "Rendering Markdown")
        if not run_cmd(f"uv run python -m folge_cli.render {enriched} pdf {md_file} --images-dir {images_dir}"):
            print("\nFATAL: Markdown rendering failed.")
            sys.exit(1)
        done, _ = counter.tick()
        info(f"  {done}/8 complete — render done")

    # --- Step 5b: Accessible document metadata ---
    metadata_args = ""
    if _skip_step(first_step, "5b"):
        step_header("5b", "Skipping metadata generation")
        if metadata_yaml.exists():
            # Reuse the metadata file discovered from a prior run so
            # publishing (step 6) still embeds document metadata.
            metadata_args = f"--metadata-file={metadata_yaml}"
            print(f"  Reusing existing metadata YAML at {metadata_yaml}")
        done, _ = counter.tick()
        info(f"  {done}/8 complete — metadata skipped")
    else:
        step_header("5b", "Generating accessible document metadata")
        from folge_cli.metadata import build_metadata, write_metadata_file
        metadata = build_metadata(enriched)
        write_metadata_file(metadata, metadata_yaml)
        print(f"  Metadata YAML written to {metadata_yaml}")
        metadata_args = f"--metadata-file={metadata_yaml}"

    # --- Step 6: Publish ---
    step_header("6", "Publishing to target formats")
    published = []
    pdf_errors = []

    if "pdf" in targets:
        pdf_file = output_dir / f"{art_stem}.pdf"
        print("\n  -> PDF (weasyprint)...", end=" ", flush=True)

        data_args = _pandoc_data_args(orientation)
        result = run_pandoc(
            f"pandoc {art_stem}.md {data_args} "
            "--pdf-engine=weasyprint --pdf-engine-opt=--presentational-hints "
            f"{metadata_args} --metadata=tagged-pdf:true "
            f"--standalone --verbose -o {art_stem}.pdf",
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
                f"pandoc {art_stem}.md {data_args} "
                "--pdf-engine=wkhtmltopdf "
                "--pdf-engine-opt=--enable-local-file-access "
                "--pdf-engine-opt=--tagged-pdf "
                f"{metadata_args} --metadata=tagged-pdf:true "
                f"--standalone --verbose -o {art_stem}.pdf",
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
                    f"pandoc {art_stem}.md {data_args} "
                    "--pdf-engine=xelatex --pdf-engine-opt=-x dvipdfmx "
                    f"{metadata_args} "
                    f"--standalone --verbose -o {art_stem}.pdf",
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
        out_file = output_name(tname, base=art_stem)
        print(f"\n  -> {tname.upper()}...", end=" ", flush=True)
        args = pandoc_args(tname, orientation)
        engine = f"--pdf-engine={FORMATS[tname]['engine']}" if "engine" in FORMATS[tname] else ""
        result = run_pandoc(
            f"pandoc {art_stem}.md {args} {engine} {metadata_args} --verbose -o {out_file}",
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
        github_file = output_dir / f"{art_stem}.md"
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
    info(f"  {done}/8 complete — all phases done")
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
    parser.add_argument(
        "--skip-vision",
        action="store_true",
        help=(
            "If an enriched JSON already exists in the output directory, "
            "reuse it and skip vision processing + merge without prompting."
        ),
    )
    parser.add_argument(
        "--first-step",
        default=None,
        choices=["1", "3", "4", "4b", "5", "5b", "6"],
        help=(
            "Start pipeline from this step instead of the beginning. "
            "Valid values: 1 (batch vision), 3 (merge), 4 (validate), "
            "4b (manual review), 5 (render), 5b (metadata), 6 (publish). "
            "Requires intermediate artifacts (e.g. enriched JSON) to already exist."
        ),
    )
    from folge_cli.batch_process import get_available_prompts
    _available_prompts = get_available_prompts()
    parser.add_argument(
        "--prompt",
        choices=_available_prompts if _available_prompts else None,
        default=None,
        help=f"Custom prompt module for vision processing (available: {', '.join(_available_prompts) or 'none'})",
    )
    args = parser.parse_args()
    try:
        run_pipeline(args)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting cleanly.")
        sys.exit(130)


if __name__ == "__main__":
    main()
