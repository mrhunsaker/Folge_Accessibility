"""Merge guide.json with vision-results.json."""

import json
from pathlib import Path

from folge.pipeline.progress import ProgressCallback, banner, ok, Timer


def _get_step_id(step):
    return step.get("id") or step.get("step_id") or str(step.get("index", ""))


def _get_guide_title(guide):
    return guide.get("title") or guide.get("name") or "Untitled Guide"


def _get_guide_id(guide):
    return guide.get("id") or guide.get("guide_id") or ""


def _clean(obj):
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_clean(i) for i in obj]
    return obj


def _is_vision_error(vision):
    if not vision:
        return True
    keys = set(vision.keys())
    return keys == {"vision_error"} or keys == {"error"} or (len(keys) == 1 and "vision_error" in keys)


def _normalize_vision(vision):
    if not vision:
        return vision
    result = dict(vision)
    for key in ("ocr_text", "text_blocks"):
        if key in result and isinstance(result[key], list):
            result[key] = "\n".join(str(item) for item in result[key] if item)
    return result


def deterministic_merge(guide_path: Path, vision_path: Path, output_path: Path,
                        on_progress: ProgressCallback = None) -> Path:
    """Merge guide.json with vision-results.json using step_id as primary key.

    Returns:
        Path to the merged enriched JSON file.
    """
    with Timer() as timer:
        with open(guide_path, "r", encoding="utf-8") as f:
            guide = json.load(f)
        with open(vision_path, "r", encoding="utf-8") as f:
            vision_data = json.load(f)

        guide_title = _get_guide_title(guide)
        guide_id = _get_guide_id(guide)
        steps = guide.get("steps", [])

        vision_lookup = {}
        for item in vision_data if isinstance(vision_data, list) else []:
            sid = _get_step_id(item)
            if sid:
                vision_lookup[sid] = item

        enriched_steps = []
        for i, step in enumerate(steps):
            sid = _get_step_id(step)
            vision = vision_lookup.get(sid, {})

            if _is_vision_error(vision):
                vision = {"vision_error": "No vision data available"}

            enriched_step = dict(step)
            enriched_step["vision"] = _normalize_vision(vision)
            enriched_steps.append(enriched_step)

        enriched = {
            "title": guide_title,
            "id": guide_id,
            "steps": enriched_steps,
            "metadata": guide.get("metadata", {}),
        }
        enriched = _clean(enriched)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(enriched, f, indent=2, ensure_ascii=False)

    ok(on_progress, f"Merged {len(enriched_steps)} steps → {output_path.name} ({timer.elapsed:.1f}s)")
    return output_path


def run(guide_path: Path, vision_path: Path, output_path: Path,
        on_progress: ProgressCallback = None) -> Path:
    """Run the merge step.

    Returns:
        Path to the enriched JSON file.
    """
    banner(on_progress, "STEP: MERGING GUIDE + VISION DATA")
    enriched_path = deterministic_merge(guide_path, vision_path, output_path, on_progress)

    # Generate manual-attention-needed.md
    from folge.pipeline.manual_attention import generate
    images_dir = guide_path.parent / "images"
    attention_path = output_path.parent / "manual-attention-needed.md"
    generate(enriched_path, images_dir, attention_path, on_progress=on_progress)

    return enriched_path
