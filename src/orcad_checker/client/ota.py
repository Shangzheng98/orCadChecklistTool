"""OTA update client — check server for updates and sync scripts."""
from __future__ import annotations

import json
import socket

import httpx

from orcad_checker.client.config import load_client_config
from orcad_checker.client.script_manager import get_installed_ids, install_script


def get_server_url() -> str:
    config = load_client_config()
    return config.get("server_url", "http://localhost:8000")


def register_with_server() -> dict:
    """Register this client with the server."""
    config = load_client_config()
    url = f"{get_server_url()}/api/v1/clients/register"
    payload = {
        "client_id": config["client_id"],
        "hostname": socket.gethostname(),
        "username": _get_username(),
        "orcad_version": _detect_orcad_version(),
        "installed_scripts": get_installed_ids(),
    }
    resp = httpx.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def check_for_updates() -> dict:
    """Check server for OTA updates.

    Returns:
        Dict with 'updates' list of scripts that need updating.
    """
    config = load_client_config()
    client_id = config["client_id"]
    url = f"{get_server_url()}/api/v1/scripts/ota/manifest?client_id={client_id}"

    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    manifest = resp.json()

    installed = set(get_installed_ids())
    updates = []
    for script_meta in manifest.get("scripts", []):
        sid = script_meta.get("id", "")
        if sid:
            updates.append(script_meta)

    return {"manifest": manifest, "updates": updates}


def pull_script(script_id: str) -> dict:
    """Download and install a script from the server."""
    url = f"{get_server_url()}/api/v1/scripts/ota/download/{script_id}"
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    meta = data.get("meta", {})
    code = data.get("code", "")
    install_script(script_id, meta, code)

    return {"status": "installed", "script_id": script_id, "version": meta.get("version")}


def pull_all_updates() -> list[dict]:
    """Pull all available updates from server."""
    result = check_for_updates()
    installed = []
    for script_meta in result["updates"]:
        try:
            r = pull_script(script_meta["id"])
            installed.append(r)
        except Exception as e:
            installed.append({"status": "error", "script_id": script_meta["id"], "error": str(e)})
    return installed


def push_script(script_id: str, code: str, name: str, description: str = "",
                author: str = "", category: str = "custom", tags: list[str] | None = None) -> dict:
    """Push a local script to the server for distribution."""
    url = f"{get_server_url()}/api/v1/scripts"
    payload = {
        "name": name,
        "description": description,
        "category": category,
        "author": author or _get_username(),
        "tags": tags or [],
        "code": code,
    }
    resp = httpx.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _get_username() -> str:
    import os
    return os.environ.get("USER", os.environ.get("USERNAME", "unknown"))


def _detect_orcad_version() -> str:
    import os
    cds_root = os.environ.get("CDS_ROOT", "")
    if "17.4" in cds_root:
        return "17.4"
    if "17.2" in cds_root:
        return "17.2"
    return "unknown"
