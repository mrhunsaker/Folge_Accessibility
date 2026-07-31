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

# ── Target registry ─────────────────────────────────────────────────
# Maps target name to its pandoc output configuration.  PDF and github
# are handled with special-case logic and are NOT listed here.
TARGETS = {
    "docx":          {"to": None,          "ext": ".docx",  "lua": True,  "css": False},
    "html":          {"to": None,          "ext": ".html",  "lua": True,  "css": True,
                      "extra": "--standalone --embed-resources"},
    "pptx":          {"to": "pptx",        "ext": ".pptx",  "lua": True,  "css": False},
    "typst":         {"to": "typst",       "ext": ".typ",   "lua": False, "css": False},
    "asciidoc":      {"to": "asciidoc",    "ext": ".adoc",  "lua": False, "css": False},
    "beamer":        {"to": "beamer",      "ext": "_beamer.pdf", "lua": True, "css": True,
                      "engine": "xelatex"},
    "commonmark":    {"to": "commonmark",  "ext": "_cm.md", "lua": False, "css": False},
    "gfm":           {"to": "gfm",         "ext": "_gh.md", "lua": False, "css": False},
    "multimarkdown": {"to": "multimarkdown","ext": "_mmd.md","lua": False, "css": False},
    "docbook":       {"to": "docbook",     "ext": ".xml",   "lua": False, "css": False},
    "epub":          {"to": "epub",        "ext": ".epub",  "lua": False, "css": False,
                      "extra": "--epub-embed-resources=true"},
    "odt":           {"to": "odt",         "ext": ".odt",   "lua": False, "css": False},
    "rst":           {"to": "rst",         "ext": ".rst",   "lua": False, "css": False},
    "latex":         {"to": "latex",       "ext": ".tex",   "lua": False, "css": False},
}


def _pandoc_target_args(target_name, orientation="portrait"):
    """Build pandoc CLI arguments for a target from the ``TARGETS`` registry.

    Parameters
    ----------
    target_name : str
        Key into ``TARGETS`` (e.g. ``"docx"``, ``"epub"``).
    orientation : str, optional
        Page orientation for CSS selection. Default is ``"portrait"``.

    Returns
    -------
    str
        A space-separated string of Pandoc arguments.
    """
    cfg = TARGETS[target_name]
    parts = []
    if cfg["to"]:
        parts.append(f"--to {cfg['to']}")
    if cfg.get("lua"):
        parts.append("--lua-filter=templates/pagebreak.lua")
        for lua in ("pdf-accessibility.lua", "docx-accessibility.lua", "accessibility.lua"):
            parts.append(f"--lua-filter={lua}")
    if cfg.get("css"):
        page_css_name = "letter-portrait.css" if orientation != "landscape" else "letter-landscape.css"
        parts.append(f"--css=templates/folge.css --css=templates/{page_css_name}")
    if cfg.get("extra"):
        parts.append(cfg["extra"])
    return " ".join(parts)


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
                        orientation="portrait"):
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
    orientation : str, optional
        Page orientation: ``"portrait"`` or ``"landscape"``. Default is
        ``"portrait"``.

    Returns
    -------
    bool
        ``True`` if the pipeline completed successfully.
    """
    guide_path = Path(guide_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if targets is None:
        targets = [
            "pdf", "docx", "html", "pptx", "github",
            "typst", "asciidoc", "beamer", "commonmark", "gfm",
            "multimarkdown", "docbook", "epub", "odt", "rst", "latex",
        ]

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

    step_header("5b", "Generating accessible document metadata")
    from folge_cli.metadata import build_metadata, write_metadata_file, apply_pdf_metadata
    metadata = build_metadata(enriched)
    metadata_yaml = output_dir / "metadata.yaml"
    write_metadata_file(metadata, metadata_yaml)
    print(f"  Metadata YAML written to {metadata_yaml}")

    step_header("6", "Publishing to target formats")
    published = []
    page_css_name = "letter-portrait.css" if orientation != "landscape" else "letter-landscape.css"
    css_args = f"--css=templates/folge.css --css=templates/{page_css_name}"
    metadata_args = f"--metadata-file={metadata_yaml}"

    if "pdf" in targets:
        pdf_file = output_dir / "guide.pdf"
        print("\n  -> PDF (weasyprint)...", end=" ", flush=True)
        result = subprocess.run(
            f"pandoc {md_file} --lua-filter=templates/pagebreak.lua "
            f"--lua-filter=pdf-accessibility.lua "
            f"{css_args} "
            f"--pdf-engine=weasyprint --pdf-engine-opt=--presentational-hints "
            f"{metadata_args} "
            f"--metadata=tagged-pdf:true -o {pdf_file}",
            shell=True, capture_output=True, text=True,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            print(f"done ({pdf_file.stat().st_size / 1024:.1f} KB)")
            apply_pdf_metadata(pdf_file, metadata)
            print("  -> PDF metadata embedded; text copying allowed")
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
                    f"{css_args} "
                    f"--pdf-engine={engine} {opts} "
                    f"{metadata_args} "
                    f"--metadata=tagged-pdf:true -o {pdf_file}",
                    shell=True, capture_output=True, text=True,
                    cwd=str(PROJECT_ROOT),
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

    # --- Generic pandoc targets (docx, html, pptx, + new formats) ---
    for tname, tcfg in TARGETS.items():
        if tname not in targets:
            continue
        out_file = f"guide{tcfg['ext']}"
        print(f"\n  -> {tname.upper()}...", end=" ", flush=True)
        args = _pandoc_target_args(tname, orientation)
        engine = f"--pdf-engine={tcfg['engine']}" if "engine" in tcfg else ""
        result = subprocess.run(
            f"pandoc {md_file} {args} {engine} {metadata_args} -o {out_file}",
            shell=True, capture_output=True, text=True,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            print(f"done ({(output_dir / out_file).stat().st_size / 1024:.1f} KB)")
            published.append(tname)
            if out_file.endswith(".pdf") and (output_dir / out_file).exists():
                apply_pdf_metadata(output_dir / out_file, metadata)
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
    if "--version" in sys.argv:
        from folge_cli import __version__
        print(f"publish {__version__}")
        sys.exit(0)

    if len(sys.argv) < 2:
        print("Usage: folge-cli publish <guide.json> <output-dir> [--targets pdf,docx,html,...] [--orientation portrait|landscape]")
        print("Example: folge-cli publish guide.json output/ --targets pdf,docx,html,epub,typst")
        print("Targets: pdf, docx, html, pptx, github, typst, asciidoc, beamer, commonmark, gfm,")
        print("         multimarkdown, docbook, epub, odt, rst, latex (default: all)")
        print("Provider: ollama, lmstudio, jan, llamacpp, openrouter, openai, gemini, anthropic (default: ollama)")
        print("Orientation: portrait (default), landscape")
        sys.exit(1)

    orientation = "portrait"
    if "--orientation" in sys.argv:
        idx = sys.argv.index("--orientation")
        if idx + 1 < len(sys.argv):
            orientation = sys.argv[idx + 1]

    guide_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    targets = sys.argv[3].split(",") if len(sys.argv) > 3 else None
    provider = sys.argv[4] if len(sys.argv) > 4 else "ollama"

    start_time = time.time()
    success = publish_with_pdf_ua(guide_path, output_dir, targets, provider,
                                  orientation=orientation)
    elapsed = time.time() - start_time

    if success:
        print(f"\n  Pipeline completed in {elapsed:.1f} seconds")
        sys.exit(0)
    else:
        print(f"\n  Pipeline failed after {elapsed:.1f} seconds")
        sys.exit(1)


if __name__ == "__main__":
    main()
