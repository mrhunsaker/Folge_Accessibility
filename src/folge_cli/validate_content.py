#!/usr/bin/env python3
# Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
# SPDX-License-Identifier: Apache-2.0
"""Validate content quality of enriched JSON against accessibility standards."""
import json
import re
import sys
from pathlib import Path

REQUIRED_VISION_FIELDS = [
    "alt_text",
    "long_description",
    "confidence",
]


def count_sentences(text):
    """Count approximate number of sentences in text.

    Parameters
    ----------
    text : str
        The text to count sentences in.

    Returns
    -------
    int
        Number of sentences found.
    """
    if not text:
        return 0
    sentences = re.split(r"[.!?]+", text.strip())
    return len([s for s in sentences if s.strip()])


def validate_step(step, min_confidence=0.7):
    """Validate a single step's content quality.

    Returns (errors, warnings) tuples. Errors block the pipeline;
    warnings are informational only.

    Parameters
    ----------
    step : dict
        The step dictionary to validate.
    min_confidence : float, optional
        Minimum confidence threshold. Default is 0.7.

    Returns
    -------
    tuple[list[str], list[str]]
        Tuple of (errors, warnings) lists.
    """
    errors = []
    warnings = []
    step_id = step.get("step_id") or step.get("id", "?")
    label = f"step_id={step_id}"

    if "vision_error" in step:
        return errors, warnings

    vision = step.get("vision")
    if vision is None:
        errors.append(f"{label}: Missing 'vision' object")
        return errors, warnings

    for field in REQUIRED_VISION_FIELDS:
        if field not in vision:
            errors.append(f"{label}: Missing required vision field '{field}'")

    alt_text = vision.get("alt_text", "")
    if len(alt_text) > 150:
        errors.append(f"{label}: alt_text exceeds 150 chars ({len(alt_text)} chars)")

    long_desc = vision.get("long_description", "")
    sentence_count = count_sentences(long_desc)
    if sentence_count < 2:
        warnings.append(
            f"{label}: long_description has {sentence_count} sentences (need 2-4)"
        )
    elif sentence_count > 4:
        warnings.append(
            f"{label}: long_description has {sentence_count} sentences (need 2-4)"
        )

    confidence = vision.get("confidence", 0)
    if confidence < min_confidence:
        warnings.append(
            f"{label}: confidence {confidence} below threshold {min_confidence}"
        )

    return errors, warnings


def validate_content(filepath, min_confidence=0.7):
    """Validate content quality of an enriched JSON file.

    Parameters
    ----------
    filepath : str or Path
        Path to the enriched JSON file.
    min_confidence : float, optional
        Minimum confidence threshold. Default is 0.7.

    Returns
    -------
    bool
        True if validation passes, False otherwise.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        print(f"INVALID: {filepath} - file not found")
        return False

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"INVALID: {filepath} - JSON decode error: {e}")
        return False

    steps = data.get("steps", [])
    if not steps:
        print(f"INVALID: {filepath} - no steps found")
        return False

    all_errors = []
    all_warnings = []
    step_ids = []

    for step in steps:
        step_id = step.get("step_id") or step.get("id")
        if step_id in step_ids:
            all_errors.append(f"Duplicate step_id: {step_id}")
        step_ids.append(step_id)
        errors, warnings = validate_step(step, min_confidence)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    if all_warnings:
        print(f"  Warnings ({len(all_warnings)}):")
        for w in all_warnings:
            print(f"    - {w}")

    if all_errors:
        print(f"  INVALID: {filepath}")
        for e in all_errors:
            print(f"    - {e}")
        return False

    print(f"  Content valid: {filepath} ({len(steps)} steps, min_confidence={min_confidence})")
    return True


def main():
    """Run CLI validation for enriched JSON content."""
    from folge_cli.config import get_min_confidence

    if len(sys.argv) < 2:
        print("Usage: folge-cli validate-content <json-file> [min-confidence]")
        print("Example: folge-cli validate-content guide.enriched.json 0.7")
        sys.exit(1)

    filepath = sys.argv[1]
    override = float(sys.argv[2]) if len(sys.argv) > 2 else None
    threshold = get_min_confidence(override)
    success = validate_content(filepath, threshold)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
