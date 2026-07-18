#!/usr/bin/env python3
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
    """Count approximate number of sentences in text."""
    if not text:
        return 0
    sentences = re.split(r'[.!?]+', text.strip())
    return len([s for s in sentences if s.strip()])


def validate_step(step, min_confidence=0.8):
    """Validate a single step's content quality."""
    issues = []
    step_id = step.get("step_id", "?")
    label = f"step_id={step_id}"

    vision = step.get("vision")
    if vision is None:
        issues.append(f"{label}: Missing 'vision' object")
        return issues

    for field in REQUIRED_VISION_FIELDS:
        if field not in vision:
            issues.append(f"{label}: Missing required vision field '{field}'")

    alt_text = vision.get("alt_text", "")
    if len(alt_text) > 150:
        issues.append(
            f"{label}: alt_text exceeds 150 chars ({len(alt_text)} chars)"
        )

    long_desc = vision.get("long_description", "")
    sentence_count = count_sentences(long_desc)
    if sentence_count < 2:
        issues.append(
            f"{label}: long_description has {sentence_count} sentences (need 2-4)"
        )
    elif sentence_count > 4:
        issues.append(
            f"{label}: long_description has {sentence_count} sentences (need 2-4)"
        )

    confidence = vision.get("confidence", 0)
    if confidence < min_confidence:
        issues.append(
            f"{label}: confidence {confidence} below threshold {min_confidence}"
        )

    return issues


def validate_content(filepath, min_confidence=0.8):
    """Validate content quality of an enriched JSON file."""
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

    all_issues = []
    step_ids = []

    for step in steps:
        step_id = step.get("step_id")
        if step_id in step_ids:
            all_issues.append(f"Duplicate step_id: {step_id}")
        step_ids.append(step_id)
        all_issues.extend(validate_step(step, min_confidence))

    if all_issues:
        print(f"INVALID: {filepath}")
        for issue in all_issues:
            print(f"  - {issue}")
        return False

    print(f"VALID: {filepath}")
    print(f"All {len(steps)} steps passed content validation (min_confidence={min_confidence})!")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_content.py <json-file> [min-confidence]")
        print("Example: python validate_content.py guide.enriched.json 0.8")
        sys.exit(1)

    filepath = sys.argv[1]
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.8
    success = validate_content(filepath, threshold)
    sys.exit(0 if success else 1)
