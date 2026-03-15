from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from orcad_checker.models.design import Design


def parse_design_file(path: str | Path) -> Design:
    """Load a JSON export file and return a validated Design model."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Design file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    return parse_design_dict(data)


def parse_design_dict(data: dict) -> Design:
    """Parse a dict (from JSON) into a validated Design model."""
    try:
        return Design.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Invalid design data: {e}") from e
