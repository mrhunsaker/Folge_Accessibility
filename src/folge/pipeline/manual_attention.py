"""Generate manual-attention-needed.md listing steps requiring manual review."""

import json
from pathlib import Path
from typing import List, Optional

from folge.pipeline.progress import ProgressCallback, ok, info


def generate(enriched_path: Path, images_dir: Path, output_path: Path,
             warnings: Optional[List[str]] = None,
             on_progress: ProgressCallback = None) -> Path:
    """Generate a markdown file listing steps that need manual attention."""
    with open(enriched_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    attention_steps = []
    for step in data.get("steps", []):
        vision = step.get("vision", {})
        step_id = step.get("id") or step.get("step_id") or str(step.get("index", "?"))
        reasons = []

        if vision.get("vision_error"):
            reasons.append(f"Vision error: {vision['vision_error']}")
        if not vision.get("alt_text"):
            reasons.append("Missing alt_text")
        if not vision.get("long_description"):
            reasons.append("Missing long_description")
        try:
            conf = float(vision.get("confidence", 0))
            if conf < 0.5:
                reasons.append(f"Low confidence: {conf:.2f}")
        except (ValueError, TypeError):
            reasons.append("Non-numeric confidence")

        if reasons:
            attention_steps.append({"step_id": step_id, "instruction": step.get("instruction", ""), "reasons": reasons})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Manual Attention Needed\n\n")
        f.write(f"Generated from: `{enriched_path.name}`\n\n")
        if not attention_steps:
            f.write("No steps require manual attention.\n")
        else:
            for item in attention_steps:
                f.write(f"## Step {item['step_id']}\n\n")
                f.write(f"**Instruction:** {item['instruction']}\n\n")
                for reason in item["reasons"]:
                    f.write(f"- {reason}\n")
                f.write("\n")

    if attention_steps:
        info(on_progress, f"Generated manual attention list: {len(attention_steps)} steps need review")
    else:
        ok(on_progress, "No steps require manual attention")

    return output_path
