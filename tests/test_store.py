"""Tests for the database store layer."""
import tempfile
from pathlib import Path

import pytest

from orcad_checker.models.scripts import (
    ClientInfo,
    KnowledgeDoc,
    ScriptCategory,
    ScriptMeta,
    ScriptStatus,
)
from orcad_checker.store.database import Database


@pytest.fixture
def db(tmp_path):
    return Database(db_path=tmp_path / "test.db")


# ── Scripts ──────────────────────────────────────────────────

def test_create_and_get_script(db):
    meta = ScriptMeta(name="Test Script", description="A test", category=ScriptCategory.UTILITY)
    result = db.create_script(meta, "puts hello")
    assert result.meta.id
    assert result.meta.name == "Test Script"
    assert result.code == "puts hello"
    assert result.meta.checksum

    fetched = db.get_script(result.meta.id)
    assert fetched is not None
    assert fetched.code == "puts hello"


def test_list_scripts(db):
    db.create_script(ScriptMeta(name="A"), "code_a")
    db.create_script(ScriptMeta(name="B"), "code_b")
    scripts = db.list_scripts()
    assert len(scripts) == 2


def test_list_scripts_with_filters(db):
    db.create_script(ScriptMeta(name="Draft One"), "code")
    s2 = db.create_script(ScriptMeta(name="Published One"), "code")
    db.publish_script(s2.meta.id)

    drafts = db.list_scripts(status="draft")
    assert len(drafts) == 1
    published = db.list_scripts(status="published")
    assert len(published) == 1


def test_update_script_code(db):
    result = db.create_script(ScriptMeta(name="Evolving"), "v1 code")
    assert result.meta.version == "1.0.0"

    updated = db.update_script(result.meta.id, code="v2 code", changelog="Added feature X")
    assert updated.meta.version == "1.0.1"
    assert updated.code == "v2 code"


def test_delete_script(db):
    result = db.create_script(ScriptMeta(name="Temp"), "temp code")
    assert db.delete_script(result.meta.id)
    assert db.get_script(result.meta.id) is None


def test_script_versions(db):
    result = db.create_script(ScriptMeta(name="Versioned"), "v1")
    db.update_script(result.meta.id, code="v2", changelog="Update")
    db.update_script(result.meta.id, code="v3", changelog="Another update")

    versions = db.get_script_versions(result.meta.id)
    assert len(versions) == 3
    assert versions[0].version == "1.0.2"  # Latest first
    assert versions[2].version == "1.0.0"  # Oldest last


def test_publish_script(db):
    result = db.create_script(ScriptMeta(name="Draft"), "code")
    assert result.meta.status == ScriptStatus.DRAFT

    published = db.publish_script(result.meta.id)
    assert published.meta.status == ScriptStatus.PUBLISHED


def test_search_scripts(db):
    db.create_script(ScriptMeta(name="BOM Exporter", description="Export bill of materials"), "code")
    db.create_script(ScriptMeta(name="Pin Checker"), "code")

    results = db.list_scripts(search="BOM")
    assert len(results) == 1
    assert results[0].name == "BOM Exporter"


# ── Knowledge Docs ───────────────────────────────────────────

def test_create_and_get_doc(db):
    doc = KnowledgeDoc(title="GetParts API", category="api", content="Description...", tags=["parts"])
    result = db.create_doc(doc)
    assert result.id

    fetched = db.get_doc(result.id)
    assert fetched.title == "GetParts API"
    assert fetched.tags == ["parts"]


def test_list_docs_by_category(db):
    db.create_doc(KnowledgeDoc(title="API Doc", category="api", content="..."))
    db.create_doc(KnowledgeDoc(title="Example", category="example", content="..."))

    api_docs = db.list_docs(category="api")
    assert len(api_docs) == 1


def test_search_knowledge(db):
    db.create_doc(KnowledgeDoc(title="Pin Access", category="api", content="GetPins returns all pins"))
    db.create_doc(KnowledgeDoc(title="Net Access", category="api", content="GetNets returns all nets"))

    results = db.search_knowledge("pins")
    assert len(results) >= 1


def test_delete_doc(db):
    doc = db.create_doc(KnowledgeDoc(title="Temp", category="api", content="..."))
    assert db.delete_doc(doc.id)
    assert db.get_doc(doc.id) is None


# ── Clients ──────────────────────────────────────────────────

def test_register_client(db):
    info = ClientInfo(client_id="test-001", hostname="workstation1", username="engineer1")
    result = db.register_client(info)
    assert result.last_sync

    fetched = db.get_client("test-001")
    assert fetched.hostname == "workstation1"


def test_list_clients(db):
    db.register_client(ClientInfo(client_id="c1", hostname="ws1"))
    db.register_client(ClientInfo(client_id="c2", hostname="ws2"))
    clients = db.list_clients()
    assert len(clients) == 2


# ── OTA Manifest ─────────────────────────────────────────────

def test_ota_manifest(db):
    s = db.create_script(ScriptMeta(name="Published Script"), "code")
    db.publish_script(s.meta.id)
    db.create_script(ScriptMeta(name="Draft Script"), "code")

    manifest = db.build_ota_manifest()
    assert manifest.server_version == "0.1.0"
    assert len(manifest.scripts) == 1  # Only published
    assert manifest.scripts[0].name == "Published Script"
