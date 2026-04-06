"""Tests for the web API endpoints."""
import json
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SKIP_ORACLE = not os.environ.get("ORACLE_JDBC_URL")
pytestmark = pytest.mark.skipif(SKIP_ORACLE, reason="Oracle not configured (set ORACLE_JDBC_URL)")

if not SKIP_ORACLE:
    from orcad_checker.web.app import app
    client = TestClient(app)
else:
    app = None  # type: ignore[assignment]
    client = None  # type: ignore[assignment]


def test_get_checkers():
    resp = client.get("/api/v1/checkers")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 7
    ids = {c["id"] for c in data}
    assert "duplicate_refdes" in ids


def test_run_check():
    fixture = Path(__file__).parent / "fixtures" / "sample_design.json"
    with open(fixture, "rb") as f:
        resp = client.post("/api/v1/check", files={"file": ("design.json", f, "application/json")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["design_name"] == "TestBoard"
    assert data["summary"]["total_checks"] >= 7


def test_list_scripts_empty():
    resp = client.get("/api/v1/scripts")
    assert resp.status_code == 200


def test_create_and_get_script():
    resp = client.post("/api/v1/scripts", json={
        "name": "API Test Script",
        "description": "Created from test",
        "category": "utility",
        "code": "puts {hello from API test}",
    })
    assert resp.status_code == 201
    data = resp.json()
    script_id = data["meta"]["id"]

    resp2 = client.get(f"/api/v1/scripts/{script_id}")
    assert resp2.status_code == 200
    assert resp2.json()["code"] == "puts {hello from API test}"


def test_publish_script():
    resp = client.post("/api/v1/scripts", json={
        "name": "Publish Test",
        "code": "puts ok",
    })
    script_id = resp.json()["meta"]["id"]

    resp2 = client.post(f"/api/v1/scripts/{script_id}/publish")
    assert resp2.status_code == 200
    assert resp2.json()["meta"]["status"] == "published"


def test_knowledge_crud():
    # Create
    resp = client.post("/api/v1/knowledge", json={
        "title": "Test Doc",
        "category": "api",
        "content": "Some TCL API documentation",
        "tags": ["test"],
    })
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    # List
    resp2 = client.get("/api/v1/knowledge")
    assert resp2.status_code == 200
    assert any(d["id"] == doc_id for d in resp2.json())

    # Get
    resp3 = client.get(f"/api/v1/knowledge/{doc_id}")
    assert resp3.status_code == 200
    assert resp3.json()["title"] == "Test Doc"


def test_client_registration():
    resp = client.post("/api/v1/clients/register", json={
        "client_id": "test-api-001",
        "hostname": "testhost",
        "username": "tester",
    })
    assert resp.status_code == 200
    assert resp.json()["client_id"] == "test-api-001"


def test_ota_manifest():
    resp = client.get("/api/v1/scripts/ota/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert "server_version" in data
    assert "scripts" in data
