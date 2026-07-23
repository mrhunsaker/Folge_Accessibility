"""Vision provider checking for the Folge Vision Pipeline."""

import os
import subprocess
from typing import Tuple

from folge.pipeline.progress import ProgressCallback, banner, ok, warn, error


def _check_local_server(base_url, timeout=5):
    """Quick HTTP check for a local server."""
    try:
        import requests
        resp = requests.get(base_url.rstrip("/v1"), timeout=timeout)
        return resp.status_code < 500
    except Exception:
        return False


def check(provider_name: str = "ollama", api_key: str = None,
          on_progress: ProgressCallback = None) -> Tuple[bool, str]:
    """Check if the selected vision provider is reachable.

    Args:
        provider_name: Provider name from PROVIDER_REGISTRY
        api_key: API key for cloud providers (optional)
        on_progress: Progress callback

    Returns:
        (ok, message) where ok is True if provider is available.
    """
    from folge.pipeline.batch_process import PROVIDER_REGISTRY

    banner(on_progress, "CHECKING PROVIDER")

    reg = PROVIDER_REGISTRY.get(provider_name)
    if not reg:
        msg = f"Unknown provider: {provider_name}"
        error(on_progress, msg)
        return False, msg

    is_local = reg["api_key_env"] is None

    if is_local:
        if _check_local_server(reg["base_url"]):
            ok(on_progress, f"Provider: {reg['label']}")
            ok(on_progress, f"Server reachable at {reg['base_url']}")
            return True, f"{reg['label']} ready"
        else:
            msg = f"{reg['label']} not reachable at {reg['base_url']}"
            error(on_progress, msg)
            return False, msg
    else:
        key = api_key or os.environ.get(reg["api_key_env"])
        if not key:
            msg = f"{reg['api_key_env']} not set. export {reg['api_key_env']}='sk-...'"
            error(on_progress, msg)
            return False, msg
        masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
        ok(on_progress, f"Provider: {reg['label']}")
        ok(on_progress, f"API key: {masked}")
        return True, f"{reg['label']} ready"
