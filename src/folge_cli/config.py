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
PROVIDERS = ["ollama", "lmstudio", "jan", "llamacpp", "openrouter", "openai", "gemini", "anthropic"]
LOCAL_PROVIDERS = {"ollama", "lmstudio", "jan", "llamacpp"}

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


# ── Project (guide) directories ─────────────────────────────────────────
# Each guide lives in its own folder under the user's Documents directory
# (~/Documents/FolgeProjects/<project>/).  The folder holds the guide JSON
# (any name — it must be the only top-level JSON file), an ``images/``
# folder with the step screenshots, and an ``output/`` folder that all
# generated files are written into.  Override the base with the
# ``FOLGE_PROJECTS_DIR`` environment variable or ``paths.projects_dir`` in
# ``config.yaml``.
PROJECTS_DIR = Path(
    get_env("FOLGE_PROJECTS_DIR")
    or load_yaml_config().get("paths", {}).get("projects_dir")
    or (Path.home() / "Documents" / "FolgeProjects")
).expanduser()


def list_projects():
    """Return sorted names of project folders under ``PROJECTS_DIR``.

    Returns
    -------
    list[str]
        Names of the immediate subdirectories of the projects directory,
        or an empty list when the directory does not exist yet.
    """
    if not PROJECTS_DIR.is_dir():
        return []
    return sorted(p.name for p in PROJECTS_DIR.iterdir() if p.is_dir())


def project_guide_file(project_dir):
    """Return the single top-level JSON file in a project folder.

    A project folder is expected to hold exactly one JSON file — the guide
    export from Folge, which may have any file name.

    Parameters
    ----------
    project_dir : str or Path
        Path to the project folder.

    Returns
    -------
    Path
        The resolved guide JSON path.

    Raises
    ------
    FileNotFoundError
        If the folder does not exist or contains no JSON file.
    ValueError
        If the folder contains more than one JSON file.
    """
    project_dir = Path(project_dir)
    matches = sorted(p for p in project_dir.glob("*.json") if p.is_file())
    if not matches:
        raise FileNotFoundError(
            f"No guide JSON found in {project_dir}. "
            "Export your guide from Folge and save it (with any name) in this folder."
        )
    if len(matches) > 1:
        raise ValueError(
            f"Multiple JSON files found in {project_dir}: "
            f"{', '.join(p.name for p in matches)}. "
            "Keep exactly one guide JSON file per project folder."
        )
    return matches[0].resolve()


def resolve_guide(guide=None, project=None):
    """Resolve the path to the guide JSON file.

    Resolution order: an explicit ``guide`` path always wins; otherwise
    ``project`` names a subfolder of ``PROJECTS_DIR`` whose single
    top-level JSON file is used.

    Parameters
    ----------
    guide : str or Path, optional
        Explicit path to a guide JSON file.
    project : str, optional
        Name of a project folder under ``PROJECTS_DIR``.

    Returns
    -------
    Path
        Absolute path to the guide JSON file.

    Raises
    ------
    ValueError
        If neither ``guide`` nor ``project`` is provided.
    """
    if guide:
        return Path(guide).expanduser().resolve()
    if project:
        return project_guide_file(PROJECTS_DIR / project)
    raise ValueError(
        "No guide specified. Pass a path to the guide JSON "
        "or use --project NAME."
    )


def project_base(guide_path):
    """Return the folder that owns a guide — base for ``images/`` and ``output/``.

    Parameters
    ----------
    guide_path : str or Path
        Path to the guide JSON file.

    Returns
    -------
    Path
        Absolute path to the project folder (the guide's parent directory).
    """
    return Path(guide_path).expanduser().resolve().parent


def project_images(guide_path):
    """Return the images folder for a guide (``<project>/images``).

    Parameters
    ----------
    guide_path : str or Path
        Path to the guide JSON file.

    Returns
    -------
    Path
        Absolute path to the project's ``images`` directory.
    """
    return project_base(guide_path) / "images"


def project_output(guide_path, output=None):
    """Return the output folder for a guide.

    Defaults to ``<project>/output``; an explicit ``output`` path (e.g. a
    CLI argument) is honored instead.

    Parameters
    ----------
    guide_path : str or Path
        Path to the guide JSON file.
    output : str or Path, optional
        Explicit output directory. Default is None.

    Returns
    -------
    Path
        Absolute output directory path.
    """
    if output:
        return Path(output).expanduser().resolve()
    return project_base(guide_path) / "output"


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
# The program defaults to ollama not for performance reasons, but rather
# to prevent accidental cost overruns from openrouter, etc.
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
            "timeout": 1800,
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
            "timeout": 1800,
            "retries": 3,
            "retry_delay": 5,
            "image_max_width": 1024,
        },
    },
    "jan": {
        "env_prefix": "JAN",
        "yaml_section": "jan",
        "needs_api_key": False,
        "needs_auth_header": False,
        "defaults": {
            "base_url": "http://localhost:1337/v1",
            "model": "",
            "workers": 2,
            "timeout": 1800,
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
            "timeout": 1800,
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
            "model": "moonshotai/kimi-k3",
            "workers": 4,
            "timeout": 300,
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
