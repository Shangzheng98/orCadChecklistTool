"""Tests for TCL result upload API."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "database.yaml"
SKIP_ORACLE = not _CONFIG_PATH.exists()
pytestmark = pytest.mark.skipif(SKIP_ORACLE, reason="Oracle not configured (config/database.yaml not found)")

if not SKIP_ORACLE:
    from orcad_checker.web.app import app
    client = TestClient(app)
else:
    app = None  # type: ignore[assignment]
    client = None  # type: ignore[assignment]


def test_upload_tcl_results():
    resp = client.post("/api/v1/check-results/upload", json={
        "design_name": "TestBoard",
        "source": "orcad_tcl",
        "results": [
            {
                "rule_id": "duplicate_refdes",
                "severity": "ERROR",
                "status": "FAIL",
                "findings": [
                    {"message": "Duplicate RefDes 'R1' on pages: PAGE1, PAGE2", "refdes": "R1"}
                ],
            },
            {
                "rule_id": "power_net_naming",
                "severity": "WARNING",
                "status": "PASS",
                "findings": [],
            },
        ],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["design_name"] == "TestBoard"
    assert data["total_checks"] == 2
    assert data["errors"] == 1
    assert data["warnings"] == 0


def test_get_history():
    # Upload one first
    client.post("/api/v1/check-results/upload", json={
        "design_name": "HistoryTest",
        "results": [],
    })
    resp = client.get("/api/v1/check-results/history")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_result_by_id():
    resp = client.post("/api/v1/check-results/upload", json={
        "design_name": "ByIdTest",
        "results": [
            {"rule_id": "net_naming", "severity": "INFO", "status": "PASS", "findings": []},
        ],
    })
    result_id = resp.json()["result_id"]

    resp2 = client.get(f"/api/v1/check-results/{result_id}")
    assert resp2.status_code == 200
    assert resp2.json()["design_name"] == "ByIdTest"
