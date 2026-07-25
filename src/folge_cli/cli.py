#!/usr/bin/env python3
# Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
# SPDX-License-Identifier: Apache-2.0
"""Folge CLI — single entry point for the vision publishing pipeline.

Usage:
    folge-cli pipeline <guide.json> [output-dir] [--targets ...] [--provider PROVIDER]
    folge-cli batch-process <guide.json> <images/> <output> [--provider PROVIDER]
    folge-cli merge <guide.json> <vision-results.json> <output>
    folge-cli validate-schema <json-file> [--warnings-out <file>]
    folge-cli validate-content <json-file> [min-confidence]
    folge-cli validate-pdf <pdf-file>
    folge-cli render <json-file> <target> <output.md>
    folge-cli publish <guide.json> <output-dir> [targets] [provider]
    folge-cli generate-manual-attention <json> <images/> <output.md> [warnings.json]

Providers: ollama, lmstudio, llamacpp, openrouter, openai, gemini, anthropic
"""
import sys
import argparse

from folge_cli.config import PROVIDERS


def main():
    """Parse CLI arguments and dispatch to the appropriate sub-command."""
    parser = argparse.ArgumentParser(
        prog="folge-cli",
        description="Folge Vision Publishing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # pipeline
    p_pipe = sub.add_parser("pipeline", help="Run the full end-to-end pipeline")
    p_pipe.add_argument("guide", help="Path to guide.json")
    p_pipe.add_argument("output", nargs="?", default="output", help="Output directory (default: output/)")
    p_pipe.add_argument("--targets", default=None, help="Comma-separated: pdf,docx,html,pptx,github")
    p_pipe.add_argument("--provider", choices=PROVIDERS, default=None)
    p_pipe.add_argument("--api-key", default=None)

    # batch-process
    p_bp = sub.add_parser("batch-process", help="Process images through Vision API")
    p_bp.add_argument("guide", help="Path to guide.json")
    p_bp.add_argument("image_dir", help="Path to images directory")
    p_bp.add_argument("output", help="Output path for vision-results.json")
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
                          help="Target: pdf, docx, pptx, html, github")
    p_render.add_argument("output", nargs="?", default=None, help="Output .md path")

    # publish
    p_pub = sub.add_parser("publish", help="Publish to target formats")
    p_pub.add_argument("guide", help="Path to guide.json")
    p_pub.add_argument("output", nargs="?", default="output", help="Output directory")
    p_pub.add_argument("targets", nargs="?", default=None, help="Comma-separated targets")
    p_pub.add_argument("provider", nargs="?", default=None, help="Vision provider")

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
            render_for_target(Path(args.guide), args.target, Path(args.output))
        elif args.output:
            render_markdown(Path(args.guide), output_path=Path(args.output))
        else:
            print("Usage: folge-cli render <guide.enriched.json> <target> <output.md>")
            sys.exit(1)

    elif args.command == "publish":
        from folge_cli.publish import publish_with_pdf_ua
        from pathlib import Path
        targets = args.targets.split(",") if args.targets else None
        success = publish_with_pdf_ua(
            args.guide, args.output, targets, args.provider or "ollama"
        )
        sys.exit(0 if success else 1)

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
