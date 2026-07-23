"""CLI entry point for the Folge Vision Pipeline.

This module is referenced by pyproject.toml's [project.scripts] entry.
"""

import argparse
import sys
import time
from pathlib import Path

from folge.pipeline.prerequisites import check as check_prereq
from folge.pipeline.provider import check as check_prov
from folge.pipeline.batch_process import run as run_batch
from folge.pipeline.merge import run as run_merge
from folge.pipeline.validate import run as run_validate
from folge.pipeline.render import run as run_render
from folge.pipeline.publish import run as run_publish
from folge.pipeline.manual_attention import generate as gen_attention
from folge.pipeline.progress import banner, ok, error


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def run_pipeline(args):
    """Execute the full pipeline from CLI."""
    guide_path = Path(args.guide)
    output_dir = Path(args.output)
    targets = args.targets.split(",") if args.targets else ["pdf", "docx", "html", "pptx"]
    provider = args.provider or "ollama"
    api_key = args.api_key

    if not guide_path.exists():
        print(f"ERROR: Guide file not found: {guide_path}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Prerequisites
    prereq_ok, _ = check_prereq()
    if not prereq_ok:
        print("\nFATAL: Missing prerequisites.")
        sys.exit(1)

    # Step 2: Provider
    prov_ok, _ = check_prov(provider_name=provider, api_key=api_key)
    if not prov_ok:
        print(f"\nWARNING: {provider} may not be available.")
        resp = input("Continue anyway? [y/N] ").strip().lower()
        if resp != "y":
            sys.exit(1)

    start_time = time.time()

    # Step 3: Batch vision processing
    images_dir = output_dir / "images" if not (PROJECT_ROOT / "images").exists() else PROJECT_ROOT / "images"
    vision_path = output_dir / "vision-results.json"
    run_batch(guide_path, images_dir, vision_path,
              provider=provider, api_key=api_key)

    # Step 4: Merge
    enriched_path = output_dir / "guide.enriched.json"
    run_merge(guide_path, vision_path, enriched_path)

    # Step 5: Generate manual attention list
    attention_path = output_dir / "manual-attention-needed.md"
    gen_attention(enriched_path, images_dir, attention_path)

    # Step 6: Validate
    run_validate(enriched_path, output_dir=output_dir)

    # Step 7: Render + Publish
    published = run_publish(enriched_path, targets, output_dir)

    elapsed = time.time() - start_time
    banner(None, "PIPELINE COMPLETE")
    ok(None, f"Published {len(published)} formats: {', '.join(published)}")
    ok(None, f"Total time: {elapsed:.1f}s")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Folge Vision Publishing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uv run run_pipeline.py guide.json\n"
            "  uv run run_pipeline.py guide.json output/ --targets pdf,html\n"
            "  uv run run_pipeline.py guide.json --provider=openrouter\n"
        ),
    )
    parser.add_argument("guide", help="Path to guide.json (Folge export)")
    parser.add_argument(
        "output", nargs="?", default="output",
        help="Output directory (default: output/)",
    )
    parser.add_argument(
        "--targets", default=None,
        help="Comma-separated: pdf,docx,html,pptx,github",
    )
    parser.add_argument(
        "--provider", choices=["ollama", "openrouter"], default=None,
        help="Vision backend (default: ollama)",
    )
    parser.add_argument(
        "--api-key", default=None,
        help="API key for OpenRouter",
    )

    args = parser.parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
