# Copyright 2026 Michael Ryan Hunsaker, M.Ed., Ph.D.
# SPDX-License-Identifier: Apache-2.0

"""Centralized configuration loading — .env takes precedence over config.yaml.

Resolution order for every setting:
    CLI argument  >  environment variable  >  config.yaml  >  hardcoded default

When running as a PyInstaller bundle, ``BUNDLED_DIR`` points to the
temporary extraction directory where data files (templates, Lua filters,
config.yaml) are accessible.
"""
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# When frozen by PyInstaller, data files live in sys._MEIPASS.
if getattr(sys, "frozen", False):
    BUNDLED_DIR = Path(sys._MEIPASS)
else:
    BUNDLED_DIR = PROJECT_ROOT

# All supported providers (ollama is always the default)
PROVIDERS = ["ollama", "lmstudio", "llamacpp", "openrouter", "openai", "gemini", "anthropic"]
LOCAL_PROVIDERS = {"ollama", "lmstudio", "llamacpp"}

def get_bundled_path(*parts):
    """Resolve a path relative to the bundled data directory.

    Parameters
    ----------
    *parts : str
        Path components to join (e.g. ``"templates", "markdown.md"``).

    Returns
    -------
    Path
        Absolute path inside the bundle or project root.
    """
    return BUNDLED_DIR.joinpath(*parts)


_env_loaded = False


def _ensure_env():
    """Load the ``.env`` file from the project root (once)."""
    global _env_loaded
    if _env_loaded:
        return
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
    _env_loaded = True


def get_env(key, default=None, cast=None):
    """Read an environment variable with optional type coercion.

    Parameters
    ----------
    key : str
        Name of the environment variable.
    default : str, optional
        Value returned when the variable is not set. Default is ``None``.
    cast : callable, optional
        Callable used to coerce the raw string value (e.g. ``int``,
        ``float``). Default is ``None``.

    Returns
    -------
    str | None
        The environment variable value after optional coercion, or
        *default* when the variable is missing or casting fails.
    """
    _ensure_env()
    val = os.environ.get(key, default)
    if cast is not None and val is not None:
        try:
            val = cast(val)
        except (ValueError, TypeError):
            val = default
    return val


def load_yaml_config():
    """Load ``config.yaml`` from the project root.

    The ``project.version`` key is always populated from the package's
    ``__version__`` attribute so it stays in sync with the CalVer
    defined in ``_version.py``.

    Returns
    -------
    dict
        Parsed YAML content, or an empty dict when the file is missing.
    """
    from folge_cli._version import __version__
    config_path = PROJECT_ROOT / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}
    config.setdefault("project", {})
    config["project"]["version"] = __version__
    return config


def get_min_confidence(override=None):
    """Return the minimum confidence threshold.

    Resolution: override arg > MIN_CONFIDENCE env > config.yaml > 0.7.

    Parameters
    ----------
    override : float, optional
        Explicit override value. Default is ``None``.

    Returns
    -------
    float
        The resolved minimum confidence value.
    """
    if override is not None:
        return override
    env_val = get_env("MIN_CONFIDENCE", cast=float)
    if env_val is not None:
        return env_val
    config = load_yaml_config()
    return config.get("validation", {}).get("min_confidence", 0.7)


# ── Provider definitions ──────────────────────────────────────────────
# Each entry maps an env prefix to its defaults and whether it needs an
# API key.  The YAML section name matches the provider key.
_PROVIDER_DEFS = {
    "ollama": {
        "env_prefix": "OLLAMA",
        "yaml_section": "ollama",
        "needs_api_key": False,
        "needs_auth_header": False,
        "defaults": {
            "base_url": "http://localhost:11434/v1",
            "model": "qwen2.5vl-8k:latest",
            "workers": 2,
            "timeout": 600,
            "retries": 3,
            "retry_delay": 5,
            "image_max_width": 1024,
        },
    },
    "lmstudio": {
        "env_prefix": "LMSTUDIO",
        "yaml_section": "lmstudio",
        "needs_api_key": False,
        "needs_auth_header": False,
        "defaults": {
            "base_url": "http://localhost:1234/v1",
            "model": "",
            "workers": 2,
            "timeout": 600,
            "retries": 3,
            "retry_delay": 5,
            "image_max_width": 1024,
        },
    },
    "llamacpp": {
        "env_prefix": "LLAMACPP",
        "yaml_section": "llamacpp",
        "needs_api_key": False,
        "needs_auth_header": False,
        "defaults": {
            "base_url": "http://localhost:8080/v1",
            "model": "",
            "workers": 2,
            "timeout": 600,
            "retries": 3,
            "retry_delay": 5,
            "image_max_width": 1024,
        },
    },
    "openrouter": {
        "env_prefix": "OPENROUTER",
        "yaml_section": "openrouter",
        "needs_api_key": True,
        "needs_auth_header": True,
        "auth_style": "bearer",
        "defaults": {
            "base_url": "https://openrouter.ai/api/v1",
            "model": "qwen/qwen-2.5-vl-72b-instruct",
            "workers": 4,
            "timeout": 60,
            "retries": 2,
            "retry_delay": 2,
            "image_max_width": 1024,
        },
    },
    "openai": {
        "env_prefix": "OPENAI",
        "yaml_section": "openai",
        "needs_api_key": True,
        "needs_auth_header": True,
        "auth_style": "bearer",
        "defaults": {
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o",
            "workers": 4,
            "timeout": 60,
            "retries": 2,
            "retry_delay": 2,
            "image_max_width": 1024,
        },
    },
    "gemini": {
        "env_prefix": "GEMINI",
        "yaml_section": "gemini",
        "needs_api_key": True,
        "needs_auth_header": True,
        "auth_style": "bearer",
        "defaults": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            "model": "gemini-2.5-flash",
            "workers": 4,
            "timeout": 60,
            "retries": 2,
            "retry_delay": 2,
            "image_max_width": 1024,
        },
    },
    "anthropic": {
        "env_prefix": "ANTHROPIC",
        "yaml_section": "anthropic",
        "needs_api_key": True,
        "needs_auth_header": True,
        "auth_style": "x-api-key",
        "defaults": {
            "base_url": "https://api.anthropic.com/v1",
            "model": "claude-sonnet-4-20250514",
            "workers": 4,
            "timeout": 60,
            "retries": 2,
            "retry_delay": 2,
            "image_max_width": 1024,
        },
    },
}


def _resolve_one_provider(provider_key, args=None):
    """Build a provider configuration dict for a single provider.

    Parameters
    ----------
    provider_key : str
        Key into ``_PROVIDER_DEFS`` (e.g. ``"ollama"``).
    args : argparse.Namespace, optional
        CLI argument namespace; ``args.model`` and ``args.api_key`` are
        checked when present. Default is ``None``.

    Returns
    -------
    dict
        Provider configuration with keys ``name``, ``base_url``,
        ``model``, ``api_key``, ``workers``, ``timeout``, ``retries``,
        ``retry_delay``, ``max_width``, ``needs_auth_header``, and
        ``auth_style``.
    """
    defn = _PROVIDER_DEFS[provider_key]
    prefix = defn["env_prefix"]
    config = load_yaml_config()
    yaml_cfg = config.get(defn["yaml_section"], {})
    defaults = defn["defaults"]

    # CLI --model override
    cli_model = (getattr(args, "model", None) if args else None)
    # CLI --api-key override
    cli_api_key = (getattr(args, "api_key", None) if args else None)

    api_key = None
    if defn["needs_api_key"]:
        api_key = cli_api_key or get_env(f"{prefix}_API_KEY") or yaml_cfg.get("api_key")

    return {
        "name": provider_key,
        "base_url": get_env(
            f"{prefix}_BASE_URL",
            default=yaml_cfg.get("base_url", defaults["base_url"]),
        ),
        "model": (
            cli_model
            or get_env(f"{prefix}_MODEL", default=yaml_cfg.get("model", defaults["model"]))
            or defaults["model"]
        ),
        "api_key": api_key,
        "workers": get_env(
            f"{prefix}_MAX_WORKERS",
            default=yaml_cfg.get("max_workers", defaults["workers"]),
            cast=int,
        ),
        "timeout": get_env(
            f"{prefix}_TIMEOUT",
            default=yaml_cfg.get("timeout", defaults["timeout"]),
            cast=int,
        ),
        "retries": get_env(
            f"{prefix}_RETRIES",
            default=yaml_cfg.get("retries", defaults["retries"]),
            cast=int,
        ),
        "retry_delay": get_env(
            f"{prefix}_RETRY_DELAY",
            default=yaml_cfg.get("retry_delay", defaults["retry_delay"]),
            cast=int,
        ),
        "max_width": get_env(
            f"{prefix}_IMAGE_MAX_WIDTH",
            default=yaml_cfg.get("image_max_width", defaults["image_max_width"]),
            cast=int,
        ),
        "needs_auth_header": defn["needs_auth_header"],
        "auth_style": defn.get("auth_style", "bearer"),
    }


def resolve_provider(args=None):
    """Resolve the active provider configuration.

    Resolution: CLI ``--provider`` > ``PROVIDER`` env > config.yaml > ``"ollama"``.

    Parameters
    ----------
    args : argparse.Namespace, optional
        CLI argument namespace; ``args.provider`` is checked when present.
        Default is ``None``.

    Returns
    -------
    dict
        Provider configuration dict (see ``_resolve_one_provider`` for
        keys).

    Raises
    ------
    ValueError
        If the resolved provider name is not in ``_PROVIDER_DEFS``.
    """
    _ensure_env()

    provider = None
    if args is not None:
        provider = getattr(args, "provider", None)
    if not provider:
        provider = get_env("PROVIDER", default="ollama")

    if provider not in _PROVIDER_DEFS:
        raise ValueError(
            f"Unknown provider '{provider}'. "
            f"Supported: {', '.join(PROVIDERS)}"
        )

    return _resolve_one_provider(provider, args)
