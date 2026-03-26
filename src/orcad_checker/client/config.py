"""Client-side configuration management."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

DEFAULT_CONFIG_DIR = Path.home() / ".orcad_checker"
DEFAULT_SCRIPTS_DIR = DEFAULT_CONFIG_DIR / "scripts"


def get_config_dir() -> Path:
    d = DEFAULT_CONFIG_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_scripts_dir() -> Path:
    d = DEFAULT_SCRIPTS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_client_config() -> dict:
    config_file = get_config_dir() / "config.json"
    if not config_file.exists():
        default = {
            "client_id": str(uuid.uuid4())[:8],
            "server_url": "http://localhost:8000",
            "auto_update": True,
            "check_interval_minutes": 30,
        }
        config_file.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default

    return json.loads(config_file.read_text(encoding="utf-8"))


def save_client_config(config: dict):
    config_file = get_config_dir() / "config.json"
    config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")
