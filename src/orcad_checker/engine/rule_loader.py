from __future__ import annotations

from pathlib import Path

import yaml


def load_rules(path: str | Path | None = None) -> dict[str, dict]:
    """Load YAML rule config file and return a dict keyed by rule_id.

    Returns empty dict if no path given or file doesn't exist.
    """
    if path is None:
        return {}

    path = Path(path)
    if not path.exists():
        return {}

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    rules_list = data.get("rules", [])
    return {r["id"]: r for r in rules_list if "id" in r}
