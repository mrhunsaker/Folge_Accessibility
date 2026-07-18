#!/usr/bin/env python3
"""Process all steps through Ollama Vision API."""
import requests
import base64
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

OLLAMA_BASE_URL = "http://localhost:11434/v1"
MODEL = "qwen2.5vl:7b"
RATE_LIMIT = 0.5  # seconds between requests
MAX_WORKERS = 2  # parallel requests

def encode_image(image_path):
    """Encode image to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def generate_prompt(step, guide_title, previous_step=None, next_step=None):
    """Generate vision prompt for a step."""
    prompt = f"""You are documenting software screenshots for accessibility.

RETURN ONLY VALID JSON with schema: step_id, vision(alt_text, long_description, ocr_text, ui_controls, important_element, confidence).

Guide: {guide_title}
Previous: {previous_step['title'] if previous_step else ''}
Current: {step['title']}
Instruction: {step['body']}
Next: {next_step['title'] if next_step else ''}

Image: The screenshot is provided as an attachment.

RULES:
- alt_text: Max 150 chars, describe ONLY visible content
- long_description: 2-4 sentences, mention important controls
- ocr_text: Only visible text as array
- ui_controls: Objects with type and label
- important_element: Single focus element
- confidence: 0.0-1.0

RETURN ONLY JSON."""
    return prompt

def process_single_step(step, guide_title, previous_step, next_step, image_dir):
    """Process a single step through vision API."""
    image_path = image_dir / step.get("image", "")

    if not image_path.exists():
        return {
            "step_id": step["step_id"],
            "error": f"Image not found: {image_path}",
            "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

    prompt = generate_prompt(step, guide_title, previous_step, next_step)

    headers = {"Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{encode_image(image_path)}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 2048,
        "temperature": 0.1,
        "top_p": 0.9,
        "stream": False
    }

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]

        # Parse JSON response
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                return json.loads(match.group())
            return {
                "step_id": step["step_id"],
                "error": f"Invalid JSON response: {content[:200]}",
                "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
    except Exception as e:
        return {
            "step_id": step["step_id"],
            "error": str(e),
            "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

def process_guide(guide_path, image_dir, output_path):
    """Process all steps in a guide through vision API."""
    with open(guide_path, 'r', encoding='utf-8') as f:
        guide = json.load(f)

    steps = guide.get("steps", [])
    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for i, step in enumerate(steps):
            previous_step = steps[i-1] if i > 0 else None
            next_step = steps[i+1] if i < len(steps)-1 else None
            future = executor.submit(
                process_single_step, step, guide["title"], previous_step, next_step, image_dir
            )
            futures[future] = step["step_id"]

        for future in as_completed(futures):
            results.append(future.result())
            time.sleep(RATE_LIMIT)

    # Sort by step_id
    results.sort(key=lambda x: x.get("step_id", 0))

    output = {
        "schema_version": "1.0",
        "guide_id": guide.get("guide_id", guide.get("title", "unknown")),
        "title": guide.get("title", "Untitled Guide"),
        "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": MODEL,
        "steps": results
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Processed {len(results)} steps to {output_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: python batch_process.py <guide.json> <images-dir> <output.json>")
        sys.exit(1)
    process_guide(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
