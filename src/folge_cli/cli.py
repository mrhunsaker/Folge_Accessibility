#!/usr/bin/env python3
# Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
# SPDX-License-Identifier: Apache-2.0
"""Folge CLI — single entry point for the vision publishing pipeline.

Usage:
    folge-cli pipeline [guide.json] [output-dir] [--project NAME] [--targets ...] [--provider PROVIDER]
    folge-cli batch-process [guide.json] [images/] [output] [--project NAME] [--provider PROVIDER]
    folge-cli merge <guide.json> <vision-results.json> <output>
    folge-cli validate-schema <json-file> [--warnings-out <file>]
    folge-cli validate-content <json-file> [min-confidence]
    folge-cli validate-pdf <pdf-file>
    folge-cli render <json-file> <target> <output.md>
    folge-cli publish [guide.json] [output-dir] [targets] [provider] [--project NAME]
    folge-cli metadata <guide.json> [-o metadata.yaml] [--apply-pdf guide.pdf] [--check]
    folge-cli generate-manual-attention <json> <images/> <output.md> [warnings.json]

Projects live in ~/Documents/FolgeProjects/<project>/ with the guide JSON
(any name — it must be the only top-level JSON), an images/ folder, and an
output/ folder.  Use --project NAME to process one without typing paths.

Providers: ollama, lmstudio, jan, llamacpp, openrouter, openai, gemini, anthropic
"""
import sys
import argparse

from folge_cli import __version__
from folge_cli.config import PROVIDERS


def main():
    """CLI entry point — dispatches to ``_main`` with a Ctrl+C safety net."""
    try:
        _main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting cleanly.")
        sys.exit(130)


def _main():
    """Parse CLI arguments and dispatch to the appropriate sub-command."""
    parser = argparse.ArgumentParser(
        prog="folge-cli",
        description="Folge Vision Publishing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # pipeline
    p_pipe = sub.add_parser("pipeline", help="Run the full end-to-end pipeline")
    p_pipe.add_argument("guide", nargs="?", default=None,
                        help="Path to guide JSON (any name; default: --project/<project>/<only JSON>)")
    p_pipe.add_argument("--project", default=None,
                        help="Project folder under ~/Documents/FolgeProjects to process")
    p_pipe.add_argument("output", nargs="?", default=None,
                        help="Output directory (default: <project>/output)")
    p_pipe.add_argument("--targets", default=None,
                        help="Comma-separated target formats (e.g. pdf,docx,html). "
                             "Default: every format supported by the installed pandoc "
                             "(see folge_cli.formats).")
    p_pipe.add_argument("--provider", choices=PROVIDERS, default=None)
    p_pipe.add_argument("--api-key", default=None)
    p_pipe.add_argument("--orientation", choices=["portrait", "landscape"], default=None,
                        help="PDF page orientation (default: portrait)")

    # batch-process
    p_bp = sub.add_parser("batch-process", help="Process images through Vision API")
    p_bp.add_argument("guide", nargs="?", default=None,
                      help="Path to guide.json (default: --project/<project>/<only JSON>)")
    p_bp.add_argument("--project", default=None,
                      help="Project folder under ~/Documents/FolgeProjects to process")
    p_bp.add_argument("image_dir", nargs="?", default=None,
                      help="Path to images directory (default: <project>/images)")
    p_bp.add_argument("output", nargs="?", default=None,
                      help="Output path for vision-results.json (default: <project>/output/vision-results.json)")
    p_bp.add_argument("--provider", choices=PROVIDERS, default=None)
    p_bp.add_argument("--api-key", default=None)
    p_bp.add_argument("--model", default=None)
    p_bp.add_argument("--sequential", action="store_true")

    # merge
    p_merge = sub.add_parser("merge", help="Merge guide + vision results")
    p_merge.add_argument("guide", help="Path to guide.json")
    p_merge.add_argument("vision", help="Path to vision-results.json")
    p_merge.add_argument("output", help="Output path for guide.enriched.json")

    # validate-schema
    p_vs = sub.add_parser("validate-schema", help="Validate enriched JSON against schema")
    p_vs.add_argument("files", nargs="+", help="JSON file(s) to validate")
    p_vs.add_argument("--warnings-out", default=None, help="Write warnings to this file")

    # validate-content
    p_vc = sub.add_parser("validate-content", help="Validate content quality")
    p_vc.add_argument("file", help="JSON file to validate")
    p_vc.add_argument("min_confidence", nargs="?", type=float, default=None,
                       help="Minimum confidence (default: from env/config)")

    # validate-pdf
    p_vpdf = sub.add_parser("validate-pdf", help="Validate PDF/UA compliance")
    p_vpdf.add_argument("pdf", help="PDF file to validate")

    # render
    p_render = sub.add_parser("render", help="Render Markdown from enriched JSON")
    p_render.add_argument("guide", help="Path to guide.enriched.json")
    p_render.add_argument("target", nargs="?", default=None,
                          help="Format key (e.g. pdf, docx, html, github)")
    p_render.add_argument("output", nargs="?", default=None, help="Output .md path")
    p_render.add_argument("--images-dir", default=None,
                          help="Guide's images directory (default: <guide dir>/images)")

    # publish
    p_pub = sub.add_parser("publish", help="Publish to target formats")
    p_pub.add_argument("guide", nargs="?", default=None,
                       help="Path to guide JSON (any name; default: --project/<project>/<only JSON>)")
    p_pub.add_argument("--project", default=None,
                       help="Project folder under ~/Documents/FolgeProjects to publish")
    p_pub.add_argument("output", nargs="?", default=None, help="Output directory (default: <project>/output)")
    p_pub.add_argument("targets", nargs="?", default=None, help="Comma-separated targets")
    p_pub.add_argument("provider", nargs="?", default=None, help="Vision provider")
    p_pub.add_argument("--orientation", choices=["portrait", "landscape"], default=None,
                       help="PDF page orientation (default: portrait)")

    # metadata
    p_meta = sub.add_parser("metadata", help="Generate accessible-document metadata for all formats")
    p_meta.add_argument("guide", help="Path to guide.json or guide.enriched.json")
    p_meta.add_argument("-o", "--out", default=None,
                        help="Write Pandoc-compatible metadata YAML to this path")
    p_meta.add_argument("--apply-pdf", default=None,
                        help="Embed metadata into this PDF and allow text copying")
    p_meta.add_argument("--check", action="store_true",
                        help="Check metadata against accessibility best practices")
    p_meta.add_argument("--strict", action="store_true",
                        help="Exit 1 when --check finds issues")
    p_meta.add_argument("--author", default=None, help="Override the document author")
    p_meta.add_argument("--subject", default=None, help="Override the document subject")
    p_meta.add_argument("--language", default=None, help="Override the primary document language")
    p_meta.add_argument("--keywords", default=None,
                        help="Override keywords (comma/semicolon separated)")

    # generate-manual-attention
    p_ma = sub.add_parser("generate-manual-attention", help="Generate manual attention markdown")
    p_ma.add_argument("enriched", help="Path to guide.enriched.json")
    p_ma.add_argument("images_dir", help="Path to images directory")
    p_ma.add_argument("output", help="Output .md path")
    p_ma.add_argument("warnings", nargs="?", default=None, help="Warnings JSON file")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Dispatch to the appropriate module
    if args.command == "pipeline":
        from folge_cli.pipeline import run_pipeline
        # Reconstruct an args-like object compatible with pipeline
        run_pipeline(args)

    elif args.command == "batch-process":
        from folge_cli.batch_process import main as bp_main
        from folge_cli.config import resolve_guide, project_images, project_output
        from pathlib import Path
        if args.project:
            guide = resolve_guide(project=args.project)
            image_dir, output = args.image_dir, args.output
            if args.guide and Path(args.guide).suffix.lower() != ".json":
                # First positional was an images dir (or output), not a guide.
                if image_dir is None:
                    image_dir = args.guide
                elif output is None:
                    output = args.guide
            sys.argv = [
                "batch-process",
                str(guide),
                str(image_dir or project_images(guide)),
                str(output or (project_output(guide) / "vision-results.json")),
            ]
        else:
            if not (args.guide and args.image_dir and args.output):
                print("ERROR: provide <guide> <image_dir> <output> or use --project NAME")
                sys.exit(1)
            sys.argv = ["batch-process", args.guide, args.image_dir, args.output]
        if args.provider:
            sys.argv += ["--provider", args.provider]
        if args.api_key:
            sys.argv += ["--api-key", args.api_key]
        if args.model:
            sys.argv += ["--model", args.model]
        if args.sequential:
            sys.argv += ["--sequential"]
        bp_main()

    elif args.command == "merge":
        from folge_cli.merge import deterministic_merge
        from pathlib import Path
        deterministic_merge(Path(args.guide), Path(args.vision), Path(args.output))

    elif args.command == "validate-schema":
        from folge_cli.validate_schema import validate_json
        from pathlib import Path
        import json as _json
        all_valid = True
        all_warnings = []
        for fp in args.files:
            ok, warns = validate_json(Path(fp))
            if not ok:
                all_valid = False
            all_warnings.extend(warns)
        if all_warnings:
            print(f"\n  {len(all_warnings)} length warning(s) (not blocking):")
            for w in all_warnings:
                print(f"    - {w['path']}: {w['message']}")
        if args.warnings_out and all_warnings:
            Path(args.warnings_out).write_text(
                _json.dumps(all_warnings, indent=2), encoding="utf-8"
            )
            print(f"  Warnings written to {args.warnings_out}")
        sys.exit(0 if all_valid else 1)

    elif args.command == "validate-content":
        from folge_cli.validate_content import validate_content
        from folge_cli.config import get_min_confidence
        threshold = get_min_confidence(args.min_confidence)
        success = validate_content(args.file, threshold)
        sys.exit(0 if success else 1)

    elif args.command == "validate-pdf":
        from folge_cli.validate_pdf import validate_pdf, print_results
        from pathlib import Path
        issues, successes = validate_pdf(args.pdf)
        success = print_results(args.pdf, issues, successes)
        sys.exit(0 if success else 1)

    elif args.command == "render":
        from folge_cli.render import render_markdown, render_for_target
        from pathlib import Path
        if args.target:
            render_for_target(Path(args.guide), args.target, Path(args.output),
                              images_dir=args.images_dir)
        elif args.output:
            render_markdown(Path(args.guide), output_path=Path(args.output),
                            images_dir=args.images_dir)
        else:
            print("Usage: folge-cli render <guide.enriched.json> <target> <output.md>")
            sys.exit(1)

    elif args.command == "publish":
        from folge_cli.publish import publish_with_pdf_ua
        from folge_cli.config import PROVIDERS as _PROVIDERS
        from pathlib import Path
        if args.project:
            # With --project, guide/output default to the project, so the
            # positional slots are interpreted as [targets] [provider]
            # (unless a value clearly names a path).
            def _is_path(value):
                return bool(value) and (
                    Path(value).suffix == ".json" or Path(value).exists()
                    or str(value).endswith("/") or "/" in value
                )
            guide = output = targets = provider = None
            for value in (args.guide, args.output, args.targets, args.provider):
                if not value:
                    continue
                if provider is None and value in _PROVIDERS:
                    provider = value
                elif guide is None and _is_path(value) and Path(value).suffix == ".json":
                    guide = value
                elif output is None and _is_path(value) and Path(value).suffix != ".json":
                    output = value
                elif targets is None:
                    targets = value
        else:
            guide, output, targets, provider = args.guide, args.output, args.targets, args.provider
        targets = targets.split(",") if targets else None
        success = publish_with_pdf_ua(
            guide, output, targets, provider or "ollama",
            orientation=getattr(args, "orientation", None) or "portrait",
            project=args.project,
        )
        sys.exit(0 if success else 1)

    elif args.command == "metadata":
        from folge_cli.metadata import run as run_metadata
        from pathlib import Path
        result = run_metadata(
            args.guide,
            out=args.out,
            apply_pdf=args.apply_pdf,
            check=args.check,
            strict=args.strict,
            author=args.author,
            subject=args.subject,
            language=args.language,
            keywords=args.keywords,
        )
        if args.strict and result.get("issues"):
            sys.exit(1)

    elif args.command == "generate-manual-attention":
        from folge_cli.generate_manual_attention import generate
        import json as _json
        warnings = None
        if args.warnings:
            with open(args.warnings, "r", encoding="utf-8") as wf:
                warnings = _json.load(wf)
            if not warnings:
                warnings = None
        generate(args.enriched, args.images_dir, args.output, warnings=warnings)
