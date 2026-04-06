"""Seed the knowledge base with default TCL API docs and examples."""
from __future__ import annotations

import json
from pathlib import Path

from orcad_checker.models.scripts import KnowledgeDoc
from orcad_checker.store.database import Database

SEED_FILE = Path(__file__).parent.parent.parent.parent / "data" / "seed_knowledge.json"


def seed_knowledge(db: Database | None = None):
    """Load seed knowledge docs into the database if empty."""
    if db is None:
        from orcad_checker.store.config import OracleConfig
        db = Database(OracleConfig.from_env())

    existing = db.list_docs()
    if existing:
        return  # Already seeded

    if not SEED_FILE.exists():
        return

    docs = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    for doc_data in docs:
        doc = KnowledgeDoc(**doc_data)
        db.create_doc(doc)
    print(f"Seeded {len(docs)} knowledge documents.")
