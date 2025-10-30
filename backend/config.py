"""Configuration helpers for contradiction finder backend."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

try:  # Python 3.11+
    import tomllib as toml_parser
except ModuleNotFoundError:  # pragma: no cover - fallback for older stdlib
    import toml as toml_parser  # type: ignore

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULTS: Dict[str, Any] = {
    "DATA_DIR": "data",
    "SAMPLE_DIR": "samples/media",
    "HF_NLI_MODEL": "cross-encoder/nli-deberta-v3-xsmall",
    "NLI_BACKEND": "hf",
}


def _load_env_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    data: Dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _load_toml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("rb") as handle:
            loaded = toml_parser.load(handle)  # type: ignore[attr-defined]
    except Exception as exc:
        raise RuntimeError(f"Unable to load config.toml: {exc}") from exc
    flattened: Dict[str, Any] = {}
    for key, value in loaded.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                flattened[f"{key.upper()}_{sub_key.upper()}"] = sub_value
        else:
            flattened[key.upper()] = value
    return flattened


def get_config() -> Dict[str, Any]:
    """Return resolved configuration values.

    Precedence: defaults < config.toml < .env < environment variables.
    """
    config: Dict[str, Any] = dict(DEFAULTS)
    config_path = REPO_ROOT / "config.toml"
    env_path = REPO_ROOT / ".env"

    # config.toml overrides defaults
    config.update(_load_toml(config_path))
    # .env overrides config.toml
    config.update(_load_env_file(env_path))
    # Environment variables take highest priority
    for key in DEFAULTS.keys():
        if key in os.environ:
            config[key] = os.environ[key]

    # Normalize to strings for JSON output compatibility
    normalized = {k: str(v) for k, v in config.items()}
    return normalized


def ensure_dirs() -> Dict[str, Any]:
    config = get_config()
    data_dir = REPO_ROOT / config["DATA_DIR"]
    transcripts = data_dir / "transcripts"
    uploads = data_dir / "uploads"
    db_dir = data_dir / "db"
    raw_dir = data_dir / "raw"
    samples_dir = REPO_ROOT / config["SAMPLE_DIR"]

    for path in (data_dir, transcripts, uploads, db_dir, raw_dir):
        path.mkdir(parents=True, exist_ok=True)

    samples_dir.mkdir(parents=True, exist_ok=True)

    return config


if __name__ == "__main__":
    resolved = ensure_dirs()
    print(json.dumps(resolved, indent=2))
