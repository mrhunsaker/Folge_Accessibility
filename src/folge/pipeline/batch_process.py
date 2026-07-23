"""Batch vision processing for the Folge Vision Pipeline.

Processes all steps in a Folge guide through a vision API (Ollama or OpenRouter)
to extract accessibility metadata from screenshots.
"""
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import requests
import yaml
from PIL import Image

from folge.pipeline.progress import (
    ProgressCallback, banner, error, info, ok, step_error, step_ok,
    step_start, summary, warn,
)

OLLAMA_BASE_URL = "http://localhost:11434/v1"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "qwen2.5vl-8k:latest"
OPENROUTER_MODEL = "qwen/qwen-2.5-vl-72b-instruct"
VALID_UI_TYPES = {
    "button", "text_field", "dropdown", "checkbox", "radio",
    "slider", "navigation", "menu", "tab", "icon", "link", "other",
}
UI_CONTROL_TYPE_MAP = {
    "text": "text_field",
    "label": "text_field",
    "heading": "text_field",
    "paragraph": "text_field",
    "input": "text_field",
    "toolbar": "navigation",
    "sidebar": "navigation",
    "tab_bar": "navigation",
    "navbar": "navigation",
    "font": "other",
    "size": "other",
    "color": "other",
    "spacing": "other",
    "alignment": "other",
    "bold": "other",
    "italic": "other",
    "underline": "other",
}


def load_config():
    """Load config.yaml from project root."""
    config_path = Path(__file__).resolve().parents[3] / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def resolve_provider(provider: str = None, api_key: str = None,
                     model: str = None):
    """Resolve provider configuration from arguments and config.yaml.

    Args:
        provider: "ollama" or "openrouter" (None to use config default)
        api_key: API key override for OpenRouter
        model: Model name override

    Returns:
        Provider config dict.
    """
    config = load_config()
    provider_name = provider or config.get("provider", "ollama")

    if provider_name == "openrouter":
        resolved_key = (
            api_key
            or os.environ.get("OPENROUTER_API_KEY")
            or config.get("openrouter", {}).get("api_key")
        )
        base_url = config.get("openrouter", {}).get("base_url", OPENROUTER_BASE_URL)
        resolved_model = model or config.get("openrouter", {}).get("model", OPENROUTER_MODEL)
        workers = config.get("openrouter", {}).get("max_workers", 4)
        timeout = config.get("openrouter", {}).get("timeout", 60)
        retries = config.get("openrouter", {}).get("retries", 2)
        retry_delay = config.get("openrouter", {}).get("retry_delay", 2)
        return {
            "name": "openrouter",
            "base_url": base_url,
            "model": resolved_model,
            "api_key": resolved_key,
            "workers": workers,
            "timeout": timeout,
            "retries": retries,
            "retry_delay": retry_delay,
            "max_width": config.get("openrouter", {}).get("image_max_width", 1024),
        }
    else:
        ollama = config.get("ollama", {})
        return {
            "name": "ollama",
            "base_url": ollama.get("base_url", OLLAMA_BASE_URL),
            "model": model or ollama.get("model", DEFAULT_MODEL),
            "api_key": None,
            "workers": ollama.get("max_workers", 2),
            "timeout": ollama.get("timeout", 300),
            "retries": ollama.get("retries", 3),
            "retry_delay": ollama.get("retry_delay", 5),
            "max_width": ollama.get("image_max_width", 1024),
        }


def normalize_guide(guide):
    """Normalize a Folge export or canonical guide to canonical format."""
    guide_title = (
        guide.get("title")
        or (guide.get("guide") or {}).get("title")
        or "Untitled Guide"
    )
    guide_id = (
        guide.get("guide_id")
        or (guide.get("guide") or {}).get("id")
        or guide_title
    )
    normalized_steps = []
    for i, step in enumerate(guide.get("steps", [])):
        step_id = step.get("step_id") or step.get("id") or (i + 1)
        body = step.get("body") or step.get("description") or ""
        image = step.get("image") or step.get("screenshotFilename") or ""
        title = step.get("title") or ""
        order = step.get("order") or step.get("index") or i
        normalized_steps.append({
            "step_id": step_id,
            "title": title,
            "body": body,
            "image": image,
            "order": order,
        })
    return guide_title, guide_id, normalized_steps


def resize_image(image_path, max_width):
    """Resize image if wider than max_width, returning bytes of the resized PNG."""
    img = Image.open(image_path)
    if img.width <= max_width:
        return None
    ratio = max_width / img.width
    new_size = (max_width, int(img.height * ratio))
    resized = img.resize(new_size, Image.LANCZOS)
    import io
    buf = io.BytesIO()
    resized.save(buf, format="PNG")
    return buf.getvalue()


def encode_image(image_path, max_width=1024):
    """Encode image to base64, resizing if necessary."""
    import base64
    resized = resize_image(image_path, max_width)
    if resized is not None:
        return base64.b64encode(resized).decode("utf-8")
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def parse_json_response(content):
    """Extract and parse JSON from model response, handling markdown fences."""
    content = content.strip()
    content = re.sub(r"^```(?:json)?\s*\n?", "", content)
    content = re.sub(r"\n?```\s*$", "", content)
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", content)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Invalid JSON in response: {content[:200]}")


def normalize_ocr_text(val):
    """Coerce ocr_text to a flat array of strings."""
    if not isinstance(val, list):
        return []
    result = []
    for item in val:
        if isinstance(item, list):
            result.append(" ".join(str(x) for x in item))
        elif isinstance(item, str):
            result.append(item)
        else:
            result.append(str(item))
    return result


def normalize_ui_controls(ui):
    """Coerce ui_controls to a valid array of {type, label} objects."""
    if ui is None:
        return []
    if isinstance(ui, str):
        return [{"type": "other", "label": ui}]
    if isinstance(ui, dict):
        vals = list(ui.values())
        if vals and isinstance(vals[0], dict) and "type" in vals[0]:
            ui = vals
        else:
            ui = [ui]
    if not isinstance(ui, list):
        return [{"type": "other", "label": str(ui)}]
    result = []
    for item in ui:
        if not isinstance(item, dict):
            result.append({"type": "other", "label": str(item)})
            continue
        raw_type = str(item.get("type", "")).strip().lower()
        if raw_type not in VALID_UI_TYPES:
            raw_type = UI_CONTROL_TYPE_MAP.get(raw_type, "other")
        label = item.get("label", "")
        if not label:
            label = str({k: v for k, v in item.items() if k != "type"})
        result.append({"type": raw_type, "label": label})
    return result


def normalize_important_element(val):
    """Coerce important_element to a plain string."""
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        return val.get("label", str(val))
    if isinstance(val, list):
        first = val[0] if val else {}
        return first.get("label", str(val)) if isinstance(first, dict) else str(val)
    if val is None:
        return ""
    return str(val)


def normalize_vision_result(result):
    """Coerce model output to match the expected schema types."""
    vision = result.get("vision")
    if not isinstance(vision, dict):
        return result

    vision["important_element"] = normalize_important_element(vision.get("important_element"))
    vision["ui_controls"] = normalize_ui_controls(vision.get("ui_controls"))
    if "confidence" not in vision:
        vision["confidence"] = 0.7

    def is_placeholder(v):
        return (
            v.get("confidence", 1.0) <= 0.7
            and not v.get("important_element")
            and not v.get("ui_controls")
        )

    if is_placeholder(vision):
        for field in ["ui_controls", "important_element", "confidence", "ocr_text"]:
            if field in result and result[field] and field not in vision:
                vision[field] = result[field]
        vision["ui_controls"] = normalize_ui_controls(vision.get("ui_controls"))
        vision["important_element"] = normalize_important_element(vision.get("important_element"))

    misplaced_fields = ["ui_controls", "important_element", "confidence"]
    for field in misplaced_fields:
        if field in result and field not in vision:
            vision[field] = result.pop(field)

    vision["ui_controls"] = normalize_ui_controls(vision.get("ui_controls"))
    vision["important_element"] = normalize_important_element(vision.get("important_element"))
    vision["ocr_text"] = normalize_ocr_text(vision.get("ocr_text"))

    alt = vision.get("alt_text", "")
    if isinstance(alt, str) and len(alt) > 150:
        truncated = alt[:150]
        for sep in (". ", ", ", "."):
            idx = truncated.rfind(sep)
            if idx > 80:
                truncated = truncated[:idx + 1]
                break
        if truncated != alt[:150]:
            truncated = truncated.rstrip(". ,") + "."
        else:
            truncated = truncated[:147] + "..."
        vision["alt_text"] = truncated

    long_desc = vision.get("long_description", "")
    if isinstance(long_desc, str) and len(long_desc) > 1000:
        vision["long_description"] = long_desc[:997] + "..."

    important = vision.get("important_element", "")
    if isinstance(important, str) and len(important) > 200:
        vision["important_element"] = important[:197] + "..."

    return result


def warmup_model(base_url, model, timeout=60, on_progress=None):
    """Send a warmup request to load the model into memory."""
    info(on_progress, "Warming up model...")
    try:
        resp = requests.post(
            f"{base_url.rstrip('/v1')}/api/generate",
            json={"model": model, "prompt": "hello", "stream": False},
            timeout=timeout,
        )
        if resp.status_code == 200:
            ok(on_progress, "Model warmed up")
            return True
        warn(on_progress, f"Warmup failed: HTTP {resp.status_code}")
        return False
    except Exception as e:
        warn(on_progress, f"Warmup failed: {e}")
        return False


def check_model_loadable(base_url, model, timeout=30):
    """Check if the model can actually generate (detect load failures)."""
    try:
        resp = requests.post(
            f"{base_url.rstrip('/v1')}/api/generate",
            json={"model": model, "prompt": "Say OK", "stream": False},
            timeout=timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            if "response" in data:
                return True
        return False
    except Exception:
        return False


def generate_prompt(step, guide_title, previous_step=None, next_step=None):
    """Generate vision prompt for a step."""
    prev_title = previous_step["title"] if previous_step else ""
    next_title = next_step["title"] if next_step else ""
    prompt = f"""You are documenting software screenshots for accessibility.

RETURN ONLY VALID JSON with schema: step_id, vision(alt_text, long_description, ocr_text, ui_controls, important_element, confidence).

Guide: {guide_title}
Previous: {prev_title}
Current: {step['title']}
Instruction: {step['body']}
Next: {next_title}

Image: The screenshot is provided as an attachment.

RULES:
- alt_text: Max 150 chars, describe ONLY visible content
- long_description: 2-4 sentences, mention important controls
- ocr_text: Only visible text as array
- ui_controls: Objects with type and label
- important_element: Plain text string (NOT an object), max 200 chars, single most important element
- confidence: 0.0-1.0

RETURN ONLY JSON."""
    return prompt


def _build_auth_headers(provider):
    """Build request headers for the given provider."""
    headers = {"Content-Type": "application/json"}
    if provider["name"] == "openrouter" and provider.get("api_key"):
        headers["Authorization"] = f"Bearer {provider['api_key']}"
    return headers


def process_single_step(step, guide_title, previous_step, next_step,
                        image_dir, provider):
    """Process a single step through vision API with retry."""
    image_path = image_dir / step.get("image", "")

    if not image_path.exists():
        return {
            "step_id": step["step_id"],
            "vision_error": f"Image not found: {image_path}",
            "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    prompt = generate_prompt(step, guide_title, previous_step, next_step)
    payload_template = {
        "model": provider["model"],
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{encode_image(image_path, provider['max_width'])}"
                        },
                    },
                ],
            }
        ],
        "max_tokens": 8192,
        "temperature": 0.1,
        "top_p": 0.9,
        "stream": False,
    }

    headers = _build_auth_headers(provider)
    last_error = None
    for attempt in range(1, provider["retries"] + 1):
        try:
            response = requests.post(
                f"{provider['base_url']}/chat/completions",
                headers=headers,
                json=payload_template,
                timeout=provider["timeout"],
            )
            response.raise_for_status()

            content = response.json()["choices"][0]["message"]["content"]

            result = parse_json_response(content)
            result["step_id"] = step["step_id"]
            result["processed_at"] = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
            )
            result["model"] = provider["model"]
            return normalize_vision_result(result)

        except Exception as e:
            last_error = str(e)
            if attempt < provider["retries"]:
                wait = provider["retry_delay"] * attempt
                time.sleep(wait)

    return {
        "step_id": step["step_id"],
        "vision_error": last_error,
        "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def process_guide(guide_path, image_dir, output_path, provider,
                  sequential=False, on_progress=None):
    """Process all steps in a guide through vision API."""
    with open(guide_path, "r", encoding="utf-8") as f:
        guide = json.load(f)

    guide_title, guide_id, steps = normalize_guide(guide)
    total = len(steps)

    info(on_progress, f"Provider: {provider['name']}")
    info(on_progress, f"Model: {provider['model']}")
    info(on_progress, f"Steps: {total}")
    info(on_progress, f"Timeout: {provider['timeout']}s per request")
    info(on_progress, f"Retries: {provider['retries']}")
    info(on_progress, f"Max image width: {provider['max_width']}px")
    info(on_progress, f"Workers: {'sequential (1)' if sequential else provider['workers']}")

    results = []
    start = time.monotonic()

    if sequential:
        for i, step in enumerate(steps):
            cur = i + 1
            prev = steps[i - 1] if i > 0 else None
            nxt = steps[i + 1] if i < total - 1 else None
            step_start(on_progress, cur, total, step["title"], step.get("image", ""))
            t0 = time.monotonic()
            result = process_single_step(
                step, guide_title, prev, nxt, image_dir, provider
            )
            elapsed = time.monotonic() - t0
            if "vision_error" in result:
                step_error(on_progress, cur, total, step["title"], result["vision_error"][:80])
            else:
                step_ok(on_progress, cur, total, step["title"], elapsed)
            results.append(result)
    else:
        with ThreadPoolExecutor(max_workers=provider["workers"]) as executor:
            futures = {}
            future_start = {}
            for i, step in enumerate(steps):
                cur = i + 1
                prev = steps[i - 1] if i > 0 else None
                nxt = steps[i + 1] if i < total - 1 else None
                step_start(on_progress, cur, total, step["title"], step.get("image", ""))
                t0 = time.monotonic()
                future = executor.submit(
                    process_single_step,
                    step, guide_title, prev, nxt, image_dir, provider,
                )
                futures[future] = (cur, step["title"])
                future_start[future] = t0

            for future in as_completed(futures):
                result = future.result()
                cur, title = futures[future]
                elapsed = time.monotonic() - future_start[future]
                if "vision_error" in result:
                    step_error(on_progress, cur, total, title, result["vision_error"][:80])
                else:
                    step_ok(on_progress, cur, total, title, elapsed)
                results.append(result)

    elapsed = time.monotonic() - start
    results.sort(key=lambda x: x.get("step_id", 0))

    error_count = sum(1 for r in results if "vision_error" in r)
    success_count = len(results) - error_count
    summary(
        on_progress, "Processed",
        success_count,
        total,
        output_path,
        f"{error_count} failed — {elapsed:.1f}s",
    )

    output = {
        "schema_version": "1.0",
        "guide_id": guide_id,
        "title": guide_title,
        "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": provider["model"],
        "steps": results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return error_count == 0


def run(guide_path: Path, images_dir: Path, output_path: Path,
        provider: str = "ollama", api_key: str = None, model: str = None,
        sequential: bool = False,
        on_progress: ProgressCallback = None) -> Path:
    """Run batch vision processing on all guide steps.

    Args:
        guide_path: Path to guide.json
        images_dir: Directory containing step screenshots
        output_path: Where to write vision-results.json
        provider: "ollama" or "openrouter"
        api_key: API key for OpenRouter (optional)
        model: Override model name (optional)
        sequential: Process one step at a time without threading
        on_progress: Progress callback

    Returns:
        Path to vision-results.json
    """
    banner(on_progress, "STEP: BATCH VISION PROCESSING")

    prov = resolve_provider(provider=provider, api_key=api_key, model=model)

    if prov["name"] == "ollama":
        if not check_model_loadable(prov["base_url"], prov["model"]):
            error(on_progress, f"Model '{prov['model']}' is not loadable. Check Ollama logs.")
            info(on_progress, "  ollama list  (to verify model exists)")
            info(on_progress, "  journalctl -u ollama  (to check Ollama logs)")
            raise RuntimeError(f"Model '{prov['model']}' is not loadable")
        warmup_model(prov["base_url"], prov["model"], on_progress=on_progress)

    process_guide(
        guide_path, images_dir, output_path, prov,
        sequential=sequential, on_progress=on_progress,
    )

    return output_path
