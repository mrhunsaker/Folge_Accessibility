#!/usr/bin/env python3
"""Merge guide.json with vision-results.json using step_id as primary key."""
import json
import time
from pathlib import Path

def deterministic_merge(guide_path, vision_path, output_path):
    """
    Merge guide.json with vision-results.json.

    RULES:
    1. Primary key: step_id (NEVER filename)
    2. Only replace/create the 'vision' field
    3. Preserve ALL authored fields from guide.json
    4. Continue on missing data with warnings
    """

    # Load guide
    with open(guide_path, 'r', encoding='utf-8') as f:
        guide = json.load(f)

    # Load vision results
    with open(vision_path, 'r', encoding='utf-8') as f:
        vision_results = json.load(f)

    # Create lookup for vision results by step_id
    vision_lookup = {}
    for step in vision_results.get("steps", []):
        step_id = step.get("step_id")
        if step_id is not None:
            vision_lookup[step_id] = step

    # Merge
    enriched_steps = []
    warnings = []

    for step in guide.get("steps", []):
        step_id = step.get("step_id")

        # Create copy to avoid mutating original
        enriched_step = step.copy()

        # Find matching vision result
        if step_id is not None and step_id in vision_lookup:
            vision_data = vision_lookup[step_id]

            # Only replace vision field
            if "vision" in vision_data:
                enriched_step["vision"] = vision_data["vision"]
            else:
                # Handle case where vision data is at root level
                enriched_step["vision"] = {
                    k: v for k, v in vision_data.items()
                    if k not in ["step_id"]
                }
        else:
            warnings.append(f"No vision data for step_id {step_id}")

        enriched_steps.append(enriched_step)

    # Check for vision results without matching guide steps
    guide_step_ids = {s.get("step_id") for s in guide.get("steps", [])}
    for step_id in vision_lookup:
        if step_id not in guide_step_ids:
            warnings.append(f"Vision data for step_id {step_id} not found in guide")

    # Build output
    output = {
        "schema_version": "1.0",
        "guide_id": guide.get("guide_id", guide.get("title", "unknown")),
        "title": guide.get("title", "Untitled Guide"),
        "description": guide.get("description", ""),
        "version": guide.get("version", "1.0.0"),
        "language": guide.get("language", "en"),
        "created_at": guide.get("created_at"),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "steps": enriched_steps,
        "metadata": {
            "merge_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_guide": guide_path.name,
            "source_vision": vision_path.name,
            "warnings": warnings
        }
    }

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Merged {len(enriched_steps)} steps to {output_path}")
    if warnings:
        print(f"Warnings ({len(warnings)}):")
        for warning in warnings:
            print(f"  - {warning}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: python merge.py <guide.json> <vision-results.json> <guide.enriched.json>")
        sys.exit(1)
    deterministic_merge(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
