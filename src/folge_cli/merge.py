#!/usr/bin/env python3
# Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
# SPDX-License-Identifier: Apache-2.0
"""Merge guide.json with vision-results.json using step_id as primary key."""
import html
import json
import time
from pathlib import Path


def _get_step_id(step):
    """Get step_id from either canonical or Folge format.

    Parameters
    ----------
    step : dict
        A step dictionary in canonical or Folge format.

    Returns
    -------
    str or None
        The step_id if present, otherwise None.
    """
    return step.get("step_id") or step.get("id")


def _get_guide_title(guide):
    """Get guide title from either canonical or Folge format.

    Parameters
    ----------
    guide : dict
        A guide dictionary in canonical or Folge format.

    Returns
    -------
    str
        The guide title, or "Untitled Guide" as a fallback.
    """
    return (
        guide.get("title")
        or (guide.get("guide") or {}).get("title")
        or "Untitled Guide"
    )


def _get_guide_id(guide):
    """Get guide_id from either canonical or Folge format.

    Parameters
    ----------
    guide : dict
        A guide dictionary in canonical or Folge format.

    Returns
    -------
    str
        The guide_id, falling back to the guide title.
    """
    return (
        guide.get("guide_id")
        or (guide.get("guide") or {}).get("id")
        or _get_guide_title(guide)
    )


def _clean(obj):
    """Recursively remove None values from dicts.

    Parameters
    ----------
    obj : dict, list, or any
        The object to clean. Dicts have None-valued keys removed,
        lists are cleaned element-wise.

    Returns
    -------
    dict, list, or any
        The cleaned object with no None values.
    """
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_clean(i) for i in obj]
    return obj


def _is_vision_error(vision):
    """Check if a vision object contains only error data.

    Parameters
    ----------
    vision : dict or any
        A vision dictionary to inspect.

    Returns
    -------
    bool
        True if the vision object has no usable fields, False otherwise.
    """
    if not isinstance(vision, dict):
        return True
    if "vision_error" in vision:
        return True
    has_error = "error" in vision
    has_alt = bool(vision.get("alt_text"))
    has_desc = bool(vision.get("long_description"))
    return has_error and not has_alt and not has_desc


def _normalize_vision(vision):
    """Flatten nested ocr_text arrays to strings.

    Parameters
    ----------
    vision : dict or any
        A vision dictionary that may contain nested ocr_text lists.

    Returns
    -------
    dict or any
        The vision dictionary with ocr_text arrays flattened to strings.
    """
    if not isinstance(vision, dict):
        return vision
    ocr = vision.get("ocr_text")
    if isinstance(ocr, list):
        vision["ocr_text"] = [
            " ".join(str(x) for x in item) if isinstance(item, list) else str(item)
            for item in ocr
        ]
    return vision


def _escape_html_text(value):
    """HTML-escape a string so it renders literally rather than as markup.

    Only applies when the value is a string; other types pass through
    unchanged.

    Parameters
    ----------
    value : any
        Value to escape, normally the vision ``long_description``.

    Returns
    -------
    any
        HTML-escaped string, or the original value if not a string.
    """
    if not isinstance(value, str):
        return value
    return html.escape(value, quote=True)


def _escape_vision_long_description(vision):
    """HTML-escape the ``long_description`` field of a vision dict.

    Focuses only on ``long_description`` (the field most prone to
    embedded HTML tags).  Other vision fields are left untouched.

    Parameters
    ----------
    vision : dict
        Vision dict, mutated in place.

    Returns
    -------
    dict
        The same vision dict with ``long_description`` escaped if string.
    """
    if not isinstance(vision, dict):
        return vision
    if "long_description" in vision:
        vision["long_description"] = _escape_html_text(vision.get("long_description"))
    return vision


def deterministic_merge(guide_path, vision_path, output_path):
    """Merge guide.json with vision-results.json.

    Uses step_id as the primary key to attach vision data to each
    guide step. Only the ``vision`` field is created or replaced;
    all other authored fields are preserved.

    Parameters
    ----------
    guide_path : str or Path
        Path to the source guide.json file.
    vision_path : str or Path
        Path to the vision-results.json file.
    output_path : str or Path
        Path where the merged output JSON will be written.
    """
    guide_path = Path(guide_path)
    vision_path = Path(vision_path)
    output_path = Path(output_path)

    print(f"  -> Merging {guide_path.name} with {vision_path.name}...")

    with open(guide_path, "r", encoding="utf-8") as f:
        guide = json.load(f)

    with open(vision_path, "r", encoding="utf-8") as f:
        vision_results = json.load(f)

    vision_lookup = {}
    for step in vision_results.get("steps", []):
        step_id = _get_step_id(step)
        if step_id is not None:
            vision_lookup[step_id] = step

    enriched_steps = []
    warnings = []

    for step in guide.get("steps", []):
        step_id = _get_step_id(step)
        enriched_step = step.copy()

        if "id" in enriched_step and "step_id" not in enriched_step:
            enriched_step["step_id"] = enriched_step.pop("id")

        if "description" in enriched_step and "body" not in enriched_step:
            enriched_step["body"] = enriched_step.pop("description")

        if "screenshotFilename" in enriched_step and "image" not in enriched_step:
            enriched_step["image"] = enriched_step.pop("screenshotFilename")

        if step_id is not None and step_id in vision_lookup:
            vision_data = vision_lookup[step_id]

            if "vision" in vision_data:
                vision = vision_data["vision"]
                if _is_vision_error(vision):
                    enriched_step["vision_error"] = vision.get("vision_error") or vision.get("error", "unknown error")
                else:
                    validated = _normalize_vision(_clean(vision))
                    enriched_step["vision"] = _escape_vision_long_description(validated)
            elif "vision_error" in vision_data:
                enriched_step["vision_error"] = vision_data["vision_error"]
            else:
                root_vision = {
                    k: v for k, v in vision_data.items()
                    if k not in ["step_id", "id", "vision_error", "error", "processed_at", "model"]
                }
                if _is_vision_error(root_vision):
                    enriched_step["vision_error"] = vision_data.get("error") or vision_data.get("vision_error", "unknown error")
                else:
                    validated = _normalize_vision(_clean(root_vision))
                    enriched_step["vision"] = _escape_vision_long_description(validated)
        else:
            warnings.append(f"No vision data for step_id {step_id}")

        enriched_steps.append(enriched_step)

    guide_step_ids = {_get_step_id(s) for s in guide.get("steps", [])}
    for step_id in vision_lookup:
        if step_id not in guide_step_ids:
            warnings.append(f"Vision data for step_id {step_id} not found in guide")

    error_steps = sum(1 for s in enriched_steps if "vision_error" in s)
    ok_steps = len(enriched_steps) - error_steps

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

    output = _clean(output)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"  Merged {len(enriched_steps)} steps ({ok_steps} vision OK, {error_steps} errors) to {output_path}")
    if warnings:
        print(f"  Warnings ({len(warnings)}):")
        for warning in warnings:
            print(f"    - {warning}")


def main():
    """CLI entry point for the merge command.

    Expects exactly three positional arguments: guide.json,
    vision-results.json, and the output path.
    """
    import sys
    if len(sys.argv) != 4:
        print("Usage: folge-cli merge <guide.json> <vision-results.json> <guide.enriched.json>")
        sys.exit(1)
    deterministic_merge(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))


if __name__ == "__main__":
    main()
