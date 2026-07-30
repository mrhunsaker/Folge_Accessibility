#!/usr/bin/env python3
# Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
# SPDX-License-Identifier: Apache-2.0
"""Process all steps through Vision API with retry, resize, and error handling.

Supports providers: ollama (default), lmstudio, llamacpp, openrouter,
openai, gemini, anthropic.  Configuration is resolved from .env with
config.yaml as a secondary fallback.  See config.py for resolution order.
"""
import argparse
import html as html_module
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from PIL import Image

from .progress import error, info, ok, step_error, step_ok, step_start, summary, warn, StepCounter
from .config import resolve_provider, PROVIDERS, LOCAL_PROVIDERS


def _clean_html(text):
    """Strip HTML tags and decode HTML entities from text.

    Parameters
    ----------
    text : str
        Raw text possibly containing HTML markup.

    Returns
    -------
    str
        Clean plain text.
    """
    if not isinstance(text, str) or not text:
        return text
    text = html_module.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_guide(guide):
    """Normalize a Folge export or canonical guide to canonical format.

    Parameters
    ----------
    guide : dict
        Guide dict in Folge export or canonical format.

    Returns
    -------
    tuple[str, str, list[dict]]
        (guide_title, guide_id, normalized_steps).
    """
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
        body = _clean_html(step.get("body") or step.get("description") or "")
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
    """Resize image if wider than max_width, returning resized PNG bytes.

    Parameters
    ----------
    image_path : str | Path
        Path to the source image file.
    max_width : int
        Maximum allowed width in pixels.

    Returns
    -------
    bytes or None
        PNG bytes of the resized image, or None if no resize was needed.
    """
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
    """Encode image to base64, resizing if necessary.

    Parameters
    ----------
    image_path : str | Path
        Path to the source image file.
    max_width : int, optional
        Maximum width before resizing. Default is 1024.

    Returns
    -------
    str
        Base64-encoded image data.
    """
    import base64
    resized = resize_image(image_path, max_width)
    if resized is not None:
        return base64.b64encode(resized).decode("utf-8")
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _fix_trailing_commas(text):
    """Remove trailing commas before closing brackets/braces."""
    return re.sub(r",\s*([\]}])", r"\1", text)


def _fix_unquoted_keys(text):
    """Add double quotes to unquoted object keys (conservative)."""
    return re.sub(r"(\{|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', text)


def _try_parse_lenient(text):
    """Attempt to parse JSON with common structural fixes."""
    for fixer in (_fix_trailing_commas, _fix_unquoted_keys):
        fixed = fixer(text)
        if fixed != text:
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass
    # bare single-quoted strings (unescaped inside)
    fixed = re.sub(r"(?<=:)\s*'([^']*)'\s*(?=[,}\]])", r'"\1"', text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in response: {text[:200]}")


def _close_incomplete_json(text):
    """Append missing closing braces/brackets to truncated JSON.

    Parameters
    ----------
    text : str
        Potentially truncated JSON string missing closing delimiters.

    Returns
    -------
    str
        Text with balanced closing braces/brackets appended.
    """
    open_braces = text.count("{") - text.count("}")
    open_brackets = text.count("[") - text.count("]")
    if open_braces > 0 or open_brackets > 0:
        text += "}" * open_braces + "]" * open_brackets
    return text


def parse_json_response(content):
    """Extract and parse JSON from model response.

    Handles markdown fences, arrays, misplaced string ``vision``,
    common JSON syntax issues (trailing commas, unquoted keys),
    and truncated output (missing closing braces/brackets).

    Parameters
    ----------
    content : str
        Raw text response from the model.

    Returns
    -------
    dict
        Parsed JSON object.

    Raises
    ------
    ValueError
        If no valid JSON can be extracted from the content.
    """
    content = content.strip()
    content = re.sub(r"^```(?:json)?\s*\n?", "", content)
    content = re.sub(r"\n?```\s*$", "", content)
    content = content.strip()
    if not content:
        raise ValueError("Empty response from model")

    # Try direct parse (unwrap array if needed)
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list) and len(parsed) > 0:
            return parsed[0]
        return parsed
    except json.JSONDecodeError:
        pass

    # Try extracting a {…} object
    obj_match = re.search(r"\{[\s\S]*\}", content)
    if obj_match:
        candidate = obj_match.group()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            try:
                return _try_parse_lenient(candidate)
            except ValueError:
                pass

    # Try extracting a […] array and taking the first element
    arr_match = re.search(r"\[[\s\S]*\]", content)
    if arr_match:
        candidate = arr_match.group()
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list) and len(parsed) > 0:
                return parsed[0]
        except json.JSONDecodeError:
            try:
                parsed = _try_parse_lenient(candidate)
                if isinstance(parsed, list) and len(parsed) > 0:
                    return parsed[0]
            except ValueError:
                pass

    # Attempt to close incomplete JSON (truncated output)
    closed = _close_incomplete_json(content)
    if closed != content:
        try:
            return json.loads(closed)
        except json.JSONDecodeError:
            try:
                return _try_parse_lenient(closed)
            except ValueError:
                pass

    raise ValueError(f"Invalid JSON in response: {content[:200]}")


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


def normalize_ocr_text(val):
    """Coerce ocr_text to a flat array of strings.

    Parameters
    ----------
    val : list or None
        Raw OCR text value from model output.

    Returns
    -------
    list[str]
        Normalized list of string values.
    """
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
    """Coerce ui_controls to a valid array of {type, label} objects.

    Parameters
    ----------
    ui : list, dict, str, or None
        Raw UI controls value from model output.

    Returns
    -------
    list[dict]
        Normalized list of UI control dicts with 'type' and 'label' keys.
    """
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
    """Coerce important_element to a plain string.

    Parameters
    ----------
    val : str, dict, list, or None
        Raw important element value from model output.

    Returns
    -------
    str
        Normalized plain-text string.
    """
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
    """Coerce model output to match the expected schema types.

    Parameters
    ----------
    result : dict
        Raw model output dict, expected to contain a 'vision' key.

    Returns
    -------
    dict
        Normalized result with vision sub-fields coerced to valid types.
    """
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
            truncated = truncated.rstrip("., ") + "."
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


def warmup_model(base_url, model, timeout=60):
    """Send a warmup request to load the model into memory.

    Parameters
    ----------
    base_url : str
        Base URL of the model server.
    model : str
        Model identifier to warm up.
    timeout : int, optional
        Request timeout in seconds. Default is 60.

    Returns
    -------
    bool
        True if warmup succeeded, False otherwise.
    """
    info("Warming up model...")
    try:
        resp = requests.post(
            f"{base_url.rstrip('/v1')}/api/generate",
            json={"model": model, "prompt": "hello", "stream": False},
            timeout=timeout,
        )
        if resp.status_code == 200:
            ok("Model warmed up")
            return True
        warn(f"Warmup failed: HTTP {resp.status_code}")
        return False
    except Exception as e:
        warn(f"Warmup failed: {e}")
        return False


def check_model_loadable(base_url, model, timeout=30):
    """Check if the model can actually generate (detect load failures).

    Parameters
    ----------
    base_url : str
        Base URL of the model server.
    model : str
        Model identifier to test.
    timeout : int, optional
        Request timeout in seconds. Default is 30.

    Returns
    -------
    bool
        True if the model responded successfully, False otherwise.
    """
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
    """Generate vision prompt for a step.

    Parameters
    ----------
    step : dict
        Step dict with 'title', 'body', and 'step_id' keys.
    guide_title : str
        Title of the parent guide.
    previous_step : dict, optional
        Preceding step for context, or None.
    next_step : dict, optional
        Following step for context, or None.

    Returns
    -------
    str
        Formatted prompt string for the vision API.
    """
    prev_title = previous_step["title"] if previous_step else ""
    next_title = next_step["title"] if next_step else ""
    prompt = f"""You are documenting software screenshots for accessibility.

Return ONLY a single JSON object (NOT an array). Use this exact structure:

{{
  "step_id": "{step['step_id']}",
  "vision": {{
    "alt_text": "string (max 150 chars)",
    "long_description": "string (1-2 sentences)",
    "ocr_text": ["array of visible text strings"],
    "ui_controls": [{{"type": "button|text_field|dropdown|...", "label": "string"}}],
    "important_element": "plain text, NOT an object (max 200 chars)",
    "confidence": 0.95
  }}
}}

Guide: {guide_title}
Previous: {prev_title}
Current: {step['title']}
Instruction: {step['body']}
Next: {next_title}

RULES:
- alt_text: Describe ONLY visible on-screen content, max 150 chars
- long_description: 1-2 sentences, mention important interactive controls
- ocr_text: Only visible text as an array of strings
- ui_controls: Array of {{type, label}} objects for interactive controls
- important_element: Plain text string (NOT an object), max 200 chars
- confidence: 0.0-1.0 reflecting certainty

CRITICAL: Return a single JSON object. NOT an array. Do NOT include any text before or after the JSON. Do NOT wrap in markdown code fences."""
    return prompt


def _build_auth_headers(provider):
    """Build request headers for the given provider.

    Parameters
    ----------
    provider : dict
        Provider config with 'needs_auth_header', 'api_key',
        and optional 'auth_style' keys.

    Returns
    -------
    dict
        Headers dict ready for use in requests.
    """
    headers = {"Content-Type": "application/json"}
    if provider.get("needs_auth_header") and provider.get("api_key"):
        style = provider.get("auth_style", "bearer")
        if style == "x-api-key":
            headers["x-api-key"] = provider["api_key"]
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {provider['api_key']}"
    return headers


def process_single_step(step, guide_title, previous_step, next_step,
                        image_dir, provider):
    """Process a single step through vision API with retry.

    Parameters
    ----------
    step : dict
        Step dict with 'step_id', 'title', 'body', and 'image' keys.
    guide_title : str
        Title of the parent guide.
    previous_step : dict or None
        Preceding step for context, or None.
    next_step : dict or None
        Following step for context, or None.
    image_dir : Path
        Directory containing step screenshot images.
    provider : dict
        Provider configuration dict.

    Returns
    -------
    dict
        Processed result dict, or a dict with 'vision_error' on failure.
    """
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
        "max_tokens": 16384,
        "temperature": 0.1,
        "top_p": 0.9,
        "stream": False,
    }

    if provider["name"] in LOCAL_PROVIDERS:
        payload_template.setdefault("options", {})["num_predict"] = 16384

    headers = _build_auth_headers(provider)
    temperatures = [0.1, 0.5, 0.7]
    last_error = None
    raw_content = ""
    finish_reason = ""
    for attempt in range(1, provider["retries"] + 1):
        try:
            payload = payload_template.copy()
            temp_idx = min(attempt - 1, len(temperatures) - 1)
            payload["temperature"] = temperatures[temp_idx]

            response = requests.post(
                f"{provider['base_url']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=provider["timeout"],
            )
            response.raise_for_status()

            data = response.json()
            choice = data["choices"][0]
            finish_reason = choice.get("finish_reason", "unknown")
            raw_content = choice["message"]["content"]
            content = raw_content

            result = parse_json_response(content)
            result["step_id"] = step["step_id"]
            result["processed_at"] = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
            )
            result["model"] = provider["model"]
            result["finish_reason"] = finish_reason
            return normalize_vision_result(result)

        except Exception as e:
            last_error = str(e)
            log_dir = Path("output") / "debug_responses"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"failed_{step['step_id']}_attempt{attempt}.txt"
            try:
                with open(log_file, "w", encoding="utf-8") as lf:
                    lf.write(f"step_id: {step['step_id']}\n")
                    lf.write(f"finish_reason: {finish_reason}\n")
                    lf.write(f"error: {last_error}\n")
                    lf.write("--- raw response ---\n")
                    lf.write(raw_content if raw_content else "(no content captured)")
            except Exception:
                pass
            if attempt < provider["retries"]:
                wait = provider["retry_delay"] * attempt
                warn(
                    f"Attempt {attempt}/{provider['retries']} failed"
                    f" (temp={payload.get('temperature', 0.1)}): {e}"
                )
                time.sleep(wait)

    return {
        "step_id": step["step_id"],
        "vision_error": last_error,
        "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def process_guide(guide_path, image_dir, output_path, provider, sequential=False):
    """Process all steps in a guide through vision API.

    Parameters
    ----------
    guide_path : Path
        Path to the guide JSON file.
    image_dir : Path
        Directory containing step screenshot images.
    output_path : Path
        Output path for the vision-results JSON file.
    provider : dict
        Provider configuration dict.
    sequential : bool, optional
        Process steps one at a time instead of threading. Default is False.

    Returns
    -------
    bool
        True if all steps succeeded, False if any failed.
    """
    with open(guide_path, "r", encoding="utf-8") as f:
        guide = json.load(f)

    guide_title, guide_id, steps = normalize_guide(guide)
    total = len(steps)

    info(f"Provider: {provider['name']}")
    info(f"Model: {provider['model']}")
    info(f"Steps: {total}")
    info(f"Timeout: {provider['timeout']}s per request")
    info(f"Retries: {provider['retries']}")
    info(f"Max image width: {provider['max_width']}px")
    info(f"Workers: {'sequential (1)' if sequential else provider['workers']}")

    results = []
    start = time.monotonic()

    if sequential:
        counter = StepCounter(total)
        for i, step in enumerate(steps):
            cur = i + 1
            prev = steps[i - 1] if i > 0 else None
            nxt = steps[i + 1] if i < total - 1 else None
            step_start(cur, total, step["title"], step.get("image", ""))
            t0 = time.monotonic()
            result = process_single_step(
                step, guide_title, prev, nxt, image_dir, provider
            )
            elapsed = time.monotonic() - t0
            if "vision_error" in result:
                step_error(cur, total, step["title"], result["vision_error"][:80])
                done, errs = counter.tick(success=False)
            else:
                step_ok(cur, total, step["title"], elapsed)
                done, errs = counter.tick(success=True)
            if errs:
                info(f"  {done}/{total} complete ({errs} failed)")
            else:
                info(f"  {done}/{total} complete")
            results.append(result)
    else:
        counter = StepCounter(total)
        with ThreadPoolExecutor(max_workers=provider["workers"]) as executor:
            futures = {}
            future_start = {}
            for i, step in enumerate(steps):
                cur = i + 1
                prev = steps[i - 1] if i > 0 else None
                nxt = steps[i + 1] if i < total - 1 else None
                step_start(cur, total, step["title"], step.get("image", ""))
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
                    step_error(cur, total, title, result["vision_error"][:80])
                    done, errs = counter.tick(success=False)
                else:
                    step_ok(cur, total, title, elapsed)
                    done, errs = counter.tick(success=True)
                if errs:
                    info(f"  {done}/{total} complete ({errs} failed)")
                else:
                    info(f"  {done}/{total} complete")
                results.append(result)

    elapsed = time.monotonic() - start
    results.sort(key=lambda x: x.get("step_id", 0))

    error_count = sum(1 for r in results if "vision_error" in r)
    success_count = len(results) - error_count
    summary(
        "Processed",
        success_count,
        total,
        output_path,
        f"{error_count} failed \u2014 {elapsed:.1f}s",
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


def main():
    """Entry point for the batch-process CLI command."""
    from folge_cli import __version__
    parser = argparse.ArgumentParser(
        description="Process guide steps through Vision API"
    )
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument("guide", help="Path to guide.json")
    parser.add_argument("image_dir", help="Path to images directory")
    parser.add_argument("output", help="Output path for vision-results.json")
    parser.add_argument(
        "--provider",
        choices=PROVIDERS,
        default=None,
        help="Vision backend (default: from .env PROVIDER)",
    )
    parser.add_argument("--api-key", default=None, help="API key for cloud providers")
    parser.add_argument("--model", default=None, help="Override model name")
    parser.add_argument("--sequential", action="store_true",
                        help="Process steps one at a time (no threading)")
    args = parser.parse_args()

    provider = resolve_provider(args)

    if args.model:
        provider["model"] = args.model

    if provider["name"] in LOCAL_PROVIDERS:
        if not check_model_loadable(provider["base_url"], provider["model"]):
            error(f"Model '{provider['model']}' is not loadable. Check server logs.")
            info(f"  provider={provider['name']}  base_url={provider['base_url']}")
            sys.exit(1)
        warmup_model(provider["base_url"], provider["model"])
    else:
        if provider.get("needs_auth_header") and not provider.get("api_key"):
            error(f"{provider['name'].upper()}_API_KEY is not set.")
            sys.exit(1)

    success = process_guide(
        Path(args.guide),
        Path(args.image_dir),
        Path(args.output),
        provider,
        sequential=args.sequential,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
