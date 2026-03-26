"""Local script management — install, list, remove, sync with OrCAD."""
from __future__ import annotations

import json
from pathlib import Path

from orcad_checker.client.config import get_scripts_dir


def list_local_scripts() -> list[dict]:
    """List all locally installed scripts."""
    scripts_dir = get_scripts_dir()
    scripts = []
    for meta_file in sorted(scripts_dir.glob("*/meta.json")):
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        meta["local_path"] = str(meta_file.parent)
        scripts.append(meta)
    return scripts


def install_script(script_id: str, meta: dict, code: str) -> Path:
    """Install a script locally."""
    script_dir = get_scripts_dir() / script_id
    script_dir.mkdir(parents=True, exist_ok=True)

    # Write meta
    meta_file = script_dir / "meta.json"
    meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # Write TCL code
    tcl_file = script_dir / f"{meta.get('name', script_id)}.tcl"
    tcl_file.write_text(code, encoding="utf-8")

    return script_dir


def remove_script(script_id: str) -> bool:
    """Remove a locally installed script."""
    script_dir = get_scripts_dir() / script_id
    if not script_dir.exists():
        return False
    import shutil
    shutil.rmtree(script_dir)
    return True


def get_local_script(script_id: str) -> dict | None:
    """Get a locally installed script's metadata and code."""
    script_dir = get_scripts_dir() / script_id
    meta_file = script_dir / "meta.json"
    if not meta_file.exists():
        return None

    meta = json.loads(meta_file.read_text(encoding="utf-8"))

    # Find the TCL file
    tcl_files = list(script_dir.glob("*.tcl"))
    code = tcl_files[0].read_text(encoding="utf-8") if tcl_files else ""

    return {"meta": meta, "code": code}


def get_installed_ids() -> list[str]:
    """Get list of installed script IDs."""
    return [d.name for d in get_scripts_dir().iterdir() if d.is_dir()]


def get_orcad_tcl_dir() -> Path | None:
    """Try to find OrCAD Capture's TCL auto-load directory."""
    import os
    cds_root = os.environ.get("CDS_ROOT")
    if cds_root:
        tcl_dir = Path(cds_root) / "tools" / "capture" / "tclscripts" / "capAutoLoad"
        if tcl_dir.exists():
            return tcl_dir

    # Common install paths on Windows
    common_paths = [
        Path("C:/Cadence/SPB_17.4/tools/capture/tclscripts/capAutoLoad"),
        Path("C:/Cadence/SPB_17.2/tools/capture/tclscripts/capAutoLoad"),
    ]
    for p in common_paths:
        if p.exists():
            return p
    return None


def deploy_to_orcad(script_id: str) -> str:
    """Deploy a local script to OrCAD Capture's auto-load directory."""
    script = get_local_script(script_id)
    if not script:
        return "Script not found locally"

    orcad_dir = get_orcad_tcl_dir()
    if not orcad_dir:
        return "OrCAD TCL directory not found. Set CDS_ROOT environment variable."

    name = script["meta"].get("name", script_id)
    target = orcad_dir / f"{name}.tcl"
    target.write_text(script["code"], encoding="utf-8")
    return f"Deployed to {target}"
