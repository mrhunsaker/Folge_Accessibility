#!/usr/bin/env python3
"""Merge guide.json with vision-results.json using step_id as primary key."""
import json
import time
from pathlib import Path

def _get_step_id(step):
    """Get step_id from either canonical or Folge format."""
    return step.get("step_id") or step.get("id")


def _get_guide_title(guide):
    """Get guide title from either canonical or Folge format."""
    return (
        guide.get("title")
        or (guide.get("guide") or {}).get("title")
        or "Untitled Guide"
    )


def _get_guide_id(guide):
    """Get guide_id from either canonical or Folge format."""
    return (
        guide.get("guide_id")
        or (guide.get("guide") or {}).get("id")
        or _get_guide_title(guide)
    )


def _clean(obj):
    """Recursively remove None values from dicts."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_clean(i) for i in obj]
    return obj


def _is_vision_error(vision):
    """Check if a vision object contains only error data (no usable fields)."""
    if not isinstance(vision, dict):
        return True
    if "vision_error" in vision:
        return True
    has_error = "error" in vision
    has_alt = bool(vision.get("alt_text"))
    has_desc = bool(vision.get("long_description"))
    return has_error and not has_alt and not has_desc


def _normalize_vision(vision):
    """Flatten nested ocr_text arrays to strings for schema compliance."""
    if not isinstance(vision, dict):
        return vision
    ocr = vision.get("ocr_text")
    if isinstance(ocr, list):
        vision["ocr_text"] = [
            " ".join(str(x) for x in item) if isinstance(item, list) else str(item)
            for item in ocr
        ]
    return vision


def deterministic_merge(guide_path, vision_path, output_path):
    """
    Merge guide.json with vision-results.json.

    RULES:
    1. Primary key: step_id (NEVER filename)
    2. Only replace/create the 'vision' field
    3. Preserve ALL authored fields from guide.json
    4. Continue on missing data with warnings
    """

    print(f"  -> Merging {guide_path.name} with {vision_path.name}...")

    # Load guide
    with open(guide_path, 'r', encoding='utf-8') as f:
        guide = json.load(f)

    # Load vision results
    with open(vision_path, 'r', encoding='utf-8') as f:
        vision_results = json.load(f)

    # Create lookup for vision results by step_id
    vision_lookup = {}
    for step in vision_results.get("steps", []):
        step_id = _get_step_id(step)
        if step_id is not None:
            vision_lookup[step_id] = step

    # Merge
    enriched_steps = []
    warnings = []

    for step in guide.get("steps", []):
        step_id = _get_step_id(step)

        # Create copy to avoid mutating original
        enriched_step = step.copy()

        # Normalize step_id key in enriched output
        if "id" in enriched_step and "step_id" not in enriched_step:
            enriched_step["step_id"] = enriched_step.pop("id")

        # Normalize body key
        if "description" in enriched_step and "body" not in enriched_step:
            enriched_step["body"] = enriched_step.pop("description")

        # Normalize image key
        if "screenshotFilename" in enriched_step and "image" not in enriched_step:
            enriched_step["image"] = enriched_step.pop("screenshotFilename")

        # Find matching vision result
        if step_id is not None and step_id in vision_lookup:
            vision_data = vision_lookup[step_id]

            if "vision" in vision_data:
                vision = vision_data["vision"]
                if _is_vision_error(vision):
                    enriched_step["vision_error"] = vision.get("vision_error") or vision.get("error", "unknown error")
                else:
                    enriched_step["vision"] = _normalize_vision(_clean(vision))
            elif "vision_error" in vision_data:
                enriched_step["vision_error"] = vision_data["vision_error"]
            else:
                # Handle case where vision data is at root level
                root_vision = {
                    k: v for k, v in vision_data.items()
                    if k not in ["step_id", "id", "vision_error", "error", "processed_at", "model"]
                }
                if _is_vision_error(root_vision):
                    enriched_step["vision_error"] = vision_data.get("error") or vision_data.get("vision_error", "unknown error")
                else:
                    enriched_step["vision"] = _normalize_vision(_clean(root_vision))
        else:
            warnings.append(f"No vision data for step_id {step_id}")

        enriched_steps.append(enriched_step)

    # Check for vision results without matching guide steps
    guide_step_ids = {_get_step_id(s) for s in guide.get("steps", [])}
    for step_id in vision_lookup:
        if step_id not in guide_step_ids:
            warnings.append(f"Vision data for step_id {step_id} not found in guide")

    # Count stats
    error_steps = sum(1 for s in enriched_steps if "vision_error" in s)
    ok_steps = len(enriched_steps) - error_steps

    # Build output
    output = {
        "schema_version": "1.0",
        "guide_id": _get_guide_id(guide),
        "title": _get_guide_title(guide),
        "description": guide.get("description", ""),
        "version": guide.get("version", "1.0.0"),
        "language": guide.get("language", "en"),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "steps": enriched_steps,
        "metadata": {
            "merge_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_guide": guide_path.name,
            "source_vision": vision_path.name,
            "steps_with_vision": ok_steps,
            "steps_with_errors": error_steps,
            "warnings": warnings,
        },
    }

    # Filter None values from output
    output = _clean(output)

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"  Merged {len(enriched_steps)} steps ({ok_steps} vision OK, {error_steps} errors) to {output_path}")
    if warnings:
        print(f"  Warnings ({len(warnings)}):")
        for warning in warnings:
            print(f"    - {warning}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: python merge.py <guide.json> <vision-results.json> <guide.enriched.json>")
        sys.exit(1)
    deterministic_merge(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
