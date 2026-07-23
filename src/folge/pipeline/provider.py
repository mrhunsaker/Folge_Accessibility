"""Vision provider checking for the Folge Vision Pipeline."""

import os
import subprocess
from typing import Tuple

from folge.pipeline.progress import ProgressCallback, banner, ok, warn, error


def check(provider_name: str = "ollama", api_key: str = None, on_progress: ProgressCallback = None) -> Tuple[bool, str]:
    """Check if the selected vision provider is reachable.

    Args:
        provider_name: "ollama" or "openrouter"
        api_key: API key for OpenRouter (optional)
        on_progress: Progress callback

    Returns:
        (ok, message) where ok is True if provider is available.
    """
    banner(on_progress, "CHECKING PROVIDER")

    if provider_name == "openrouter":
        key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not key:
            msg = "OPENROUTER_API_KEY not set. export OPENROUTER_API_KEY='sk-or-...'"
            error(on_progress, msg)
            return False, msg
        masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
        ok(on_progress, f"Provider: OpenRouter (cloud)")
        ok(on_progress, f"API key: {masked}")
        return True, "OpenRouter ready"

    # Ollama (default)
    try:
        result = subprocess.run(
            "curl -s http://localhost:11434/api/tags",
            shell=True, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            data = result.stdout
            if "qwen2.5vl" in data:
                ok(on_progress, "Provider: Ollama (local)")
                ok(on_progress, "Ollama running with qwen2.5vl model")
                return True, "Ollama ready with qwen2.5vl"
            elif "granite" in data:
                msg = "Ollama running but qwen2.5vl not found (granite available)"
                warn(on_progress, msg)
                return False, msg
            else:
                msg = "Ollama running but no vision model detected. Run: ollama pull qwen2.5vl-8k:latest"
                warn(on_progress, msg)
                return False, msg
        else:
            msg = "Ollama not reachable at localhost:11434"
            error(on_progress, msg)
            return False, msg
    except Exception:
        msg = "Could not check Ollama status"
        error(on_progress, msg)
        return False, msg
