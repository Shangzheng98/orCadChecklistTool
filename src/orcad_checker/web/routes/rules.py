from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import APIRouter, Body

router = APIRouter(prefix="/api/v1", tags=["rules"])

RULES_PATH = Path(__file__).parent.parent.parent.parent.parent / "rules" / "default_rules.yaml"


@router.get("/rules")
def get_rules():
    """Get current rules YAML content."""
    if not RULES_PATH.exists():
        return {"content": ""}
    return {"content": RULES_PATH.read_text(encoding="utf-8")}


@router.put("/rules")
def update_rules(content: str = Body(..., media_type="text/plain")):
    """Update rules YAML content."""
    # Validate YAML syntax
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        return {"error": f"Invalid YAML: {e}"}

    RULES_PATH.write_text(content, encoding="utf-8")
    return {"status": "ok"}
