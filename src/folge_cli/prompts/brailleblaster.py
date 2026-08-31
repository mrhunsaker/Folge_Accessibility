"""Custom prompt for BrailleBlaster screenshots."""


def generate_prompt(step, guide_title, previous_step=None, next_step=None):
    """Generate vision prompt for BrailleBlaster screenshots.
    
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

BrailleBlaster-specific instructions:
Describe the image in detail. If the image shows the BrailleBlaster editor, begin your description with the following exact sentence:
"BrailleBlaster window showing a style panel on the left, print text editing panel in the center, and braille preview on the right. The top menu bar and toolbars provide editing controls."
Then, continue with a detailed description of the specific content, actions, or elements visible in the image.

CRITICAL: Return a single JSON object. NOT an array. Do NOT include any text before or after the JSON. Do NOT wrap in markdown code fences."""
    return prompt
