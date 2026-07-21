#!/usr/bin/env python3
"""Generate a manual-attention-needed.md listing steps where vision processing failed."""
import json
import sys
from pathlib import Path


def generate(enriched_path, images_dir, output_path, warnings=None):
    with open(enriched_path, "r", encoding="utf-8") as f:
        guide = json.load(f)

    failed = []
    for seq, step in enumerate(guide.get("steps", []), start=1):
        if "vision_error" in step:
            failed.append((seq, step))

    if not failed and not warnings:
        print("No vision errors found. No manual attention file needed.")
        return False

    lines = []
    if failed:
        lines.append("# Steps Requiring Manual Vision Descriptions\n")
        lines.append(
            f"The following {len(failed)} step(s) failed automatic vision processing "
            "and need manual image descriptions.\n"
        )
        lines.append("For each step, provide an `alt_text` and `long_description` for the image.\n")
        lines.append("---\n")

        for seq, step in failed:
            step_num = str(seq)
            title = step.get("title", "Untitled")
            step_id = step.get("step_id", "unknown")
            image = step.get("screenshotRelativePath", step.get("image", "unknown"))
            body = step.get("body", "*(empty)*")
            if not body:
                body = "*(empty)*"
            error = step.get("vision_error", "unknown error")

            lines.append(f"## {step_num} {title}")
            lines.append(f"- **step_id:** `{step_id}`")
            lines.append(f"- **Image:** `{image}`")
            lines.append(f"- **Body:** {body}")
            lines.append(f"- **Error:** `{error}`")
            lines.append("")
            lines.append("### Manual Description Required")
            lines.append("- **alt_text:** ")
            lines.append("- **long_description:** ")
            lines.append("")
            lines.append("---\n")

        lines.append(
            "*After filling in the descriptions, add them to "
            "`output/guide.enriched.json` under the corresponding step's "
            "`vision` field, then re-run the render step.*\n"
        )

    if warnings:
        if not failed:
            lines.append("# Content Warnings\n")
        else:
            lines.append("# Content Warnings\n")
        lines.append(
            f"The following {len(warnings)} field(s) exceeded schema length limits.\n"
            "These are non-blocking but may cause rendering issues.\n"
        )
        lines.append("| Path | Issue |")
        lines.append("|------|-------|")
        for w in warnings:
            path = w.get("path", "unknown")
            msg = w.get("message", "unknown issue")
            lines.append(f"| `{path}` | {msg} |")
        lines.append("")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    parts = []
    if failed:
        parts.append(f"{len(failed)} failed vision")
    if warnings:
        parts.append(f"{len(warnings)} length warnings")
    print(f"Written to {output} ({', '.join(parts)} need attention)")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python generate_manual_attention.py <guide.enriched.json> <images_dir> <output.md> [warnings.json]")
        sys.exit(1)
    warnings = None
    if len(sys.argv) == 5:
        import json as _json
        with open(sys.argv[4], "r", encoding="utf-8") as wf:
            warnings = _json.load(wf)
        if not warnings:
            warnings = None
    generate(sys.argv[1], sys.argv[2], sys.argv[3], warnings=warnings)
