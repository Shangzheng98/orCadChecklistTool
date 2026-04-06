"""SQLite-based storage for scripts, versions, knowledge docs, clients, sessions, and TCL results."""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
import uuid

logger = logging.getLogger(__name__)
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue

from orcad_checker.models.scripts import (
    ClientInfo,
    KnowledgeDoc,
    OTAManifest,
    ScriptContent,
    ScriptMeta,
    ScriptStatus,
    ScriptVersion,
)

_DEFAULT_DB = Path(__file__).parent.parent.parent.parent / "data" / "orcad_checker.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _checksum(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]


class Database:
    def __init__(self, db_path: str | Path | None = None, pool_size: int = 5):
        self.db_path = str(db_path or _DEFAULT_DB)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._pool: Queue[sqlite3.Connection] = Queue(maxsize=pool_size)
        self._pool_lock = threading.Lock()
        for _ in range(pool_size):
            self._pool.put(self._create_conn())
        self._init_tables()

    def _create_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    @contextmanager
    def _get_conn(self):
        conn = self._pool.get()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.put(conn)

    def _init_tables(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS scripts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    version TEXT DEFAULT '1.0.0',
                    category TEXT DEFAULT 'custom',
                    status TEXT DEFAULT 'draft',
                    author TEXT DEFAULT '',
                    tags TEXT DEFAULT '[]',
                    code TEXT DEFAULT '',
                    checksum TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS script_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    script_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    code TEXT NOT NULL,
                    changelog TEXT DEFAULT '',
                    checksum TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (script_id) REFERENCES scripts(id)
                );

                CREATE TABLE IF NOT EXISTS knowledge_docs (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT DEFAULT 'api',
                    content TEXT NOT NULL,
                    tags TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS clients (
                    client_id TEXT PRIMARY KEY,
                    hostname TEXT DEFAULT '',
                    username TEXT DEFAULT '',
                    orcad_version TEXT DEFAULT '',
                    last_sync TEXT DEFAULT '',
                    installed_scripts TEXT DEFAULT '[]'
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    messages TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    last_active TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tcl_check_results (
                    result_id TEXT PRIMARY KEY,
                    design_name TEXT DEFAULT '',
                    source TEXT DEFAULT '',
                    timestamp TEXT NOT NULL,
                    data TEXT NOT NULL
                );
            """)

    # ── Scripts CRUD ─────────────────────────────────────────────

    def create_script(self, meta: ScriptMeta, code: str) -> ScriptContent:
        script_id = meta.id or str(uuid.uuid4())[:8]
        now = _now()
        cs = _checksum(code)
        tags_json = json.dumps(meta.tags)

        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO scripts
                   (id, name, description, version, category, status, author, tags, code, checksum, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (script_id, meta.name, meta.description, meta.version,
                 meta.category.value, meta.status.value, meta.author,
                 tags_json, code, cs, now, now),
            )
            # Also save as first version
            conn.execute(
                """INSERT INTO script_versions (script_id, version, code, changelog, checksum, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (script_id, meta.version, code, "Initial version", cs, now),
            )

        return ScriptContent(
            meta=ScriptMeta(
                id=script_id, name=meta.name, description=meta.description,
                version=meta.version, category=meta.category, status=meta.status,
                author=meta.author, tags=meta.tags,
                created_at=now, updated_at=now, checksum=cs,
            ),
            code=code,
        )

    def get_script(self, script_id: str) -> ScriptContent | None:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,)).fetchone()
        if not row:
            return None
        return self._row_to_script_content(row)

    def list_scripts(
        self,
        status: str | None = None,
        category: str | None = None,
        search: str | None = None,
    ) -> list[ScriptMeta]:
        query = "SELECT * FROM scripts WHERE 1=1"
        params: list = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if category:
            query += " AND category = ?"
            params.append(category)
        if search:
            query += " AND (name LIKE ? OR description LIKE ? OR tags LIKE ?)"
            like = f"%{search}%"
            params.extend([like, like, like])
        query += " ORDER BY updated_at DESC"

        with self._get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_meta(r) for r in rows]

    def update_script(self, script_id: str, meta: ScriptMeta | None = None,
                      code: str | None = None, changelog: str = "") -> ScriptContent | None:
        existing = self.get_script(script_id)
        if not existing:
            return None

        now = _now()
        updates = []
        params: list = []

        if meta:
            if meta.name:
                updates.append("name = ?"); params.append(meta.name)
            if meta.description:
                updates.append("description = ?"); params.append(meta.description)
            if meta.category:
                updates.append("category = ?"); params.append(meta.category.value)
            if meta.status:
                updates.append("status = ?"); params.append(meta.status.value)
            if meta.author:
                updates.append("author = ?"); params.append(meta.author)
            if meta.tags:
                updates.append("tags = ?"); params.append(json.dumps(meta.tags))

        if code is not None:
            cs = _checksum(code)
            new_version = self._bump_version(existing.meta.version)
            updates.extend(["code = ?", "version = ?", "checksum = ?"])
            params.extend([code, new_version, cs])

        updates.append("updated_at = ?"); params.append(now)
        params.append(script_id)

        # Single transaction for both version history and script update
        with self._get_conn() as conn:
            if code is not None:
                conn.execute(
                    """INSERT INTO script_versions (script_id, version, code, changelog, checksum, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (script_id, new_version, code, changelog, cs, now),
                )
            conn.execute(f"UPDATE scripts SET {', '.join(updates)} WHERE id = ?", params)

        return self.get_script(script_id)

    def delete_script(self, script_id: str) -> bool:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM script_versions WHERE script_id = ?", (script_id,))
            cur = conn.execute("DELETE FROM scripts WHERE id = ?", (script_id,))
        return cur.rowcount > 0

    def get_script_versions(self, script_id: str) -> list[ScriptVersion]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM script_versions WHERE script_id = ? ORDER BY created_at DESC",
                (script_id,),
            ).fetchall()
        return [
            ScriptVersion(
                version=r["version"], code=r["code"],
                changelog=r["changelog"], checksum=r["checksum"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def publish_script(self, script_id: str) -> ScriptContent | None:
        return self.update_script(
            script_id,
            meta=ScriptMeta(name="", status=ScriptStatus.PUBLISHED),
        )

    # ── Knowledge Docs ───────────────────────────────────────────

    def create_doc(self, doc: KnowledgeDoc) -> KnowledgeDoc:
        doc_id = doc.id or str(uuid.uuid4())[:8]
        now = _now()
        tags_json = json.dumps(doc.tags)

        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO knowledge_docs (id, title, category, content, tags, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (doc_id, doc.title, doc.category, doc.content, tags_json, now, now),
            )
        doc.id = doc_id
        doc.created_at = now
        doc.updated_at = now
        return doc

    def get_doc(self, doc_id: str) -> KnowledgeDoc | None:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM knowledge_docs WHERE id = ?", (doc_id,)).fetchone()
        if not row:
            return None
        return self._row_to_doc(row)

    def list_docs(self, category: str | None = None, search: str | None = None) -> list[KnowledgeDoc]:
        query = "SELECT * FROM knowledge_docs WHERE 1=1"
        params: list = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if search:
            query += " AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)"
            like = f"%{search}%"
            params.extend([like, like, like])
        query += " ORDER BY updated_at DESC"

        with self._get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_doc(r) for r in rows]

    def update_doc(self, doc_id: str, doc: KnowledgeDoc) -> KnowledgeDoc | None:
        now = _now()
        with self._get_conn() as conn:
            cur = conn.execute(
                """UPDATE knowledge_docs SET title=?, category=?, content=?, tags=?, updated_at=?
                   WHERE id=?""",
                (doc.title, doc.category, doc.content, json.dumps(doc.tags), now, doc_id),
            )
        if cur.rowcount == 0:
            return None
        return self.get_doc(doc_id)

    def delete_doc(self, doc_id: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM knowledge_docs WHERE id = ?", (doc_id,))
        return cur.rowcount > 0

    def search_knowledge(self, query: str, limit: int = 10) -> list[KnowledgeDoc]:
        """Search knowledge base by keyword relevance."""
        return self.list_docs(search=query)[:limit]

    # ── Clients ──────────────────────────────────────────────────

    def register_client(self, info: ClientInfo) -> ClientInfo:
        now = _now()
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO clients
                   (client_id, hostname, username, orcad_version, last_sync, installed_scripts)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (info.client_id, info.hostname, info.username,
                 info.orcad_version, now, json.dumps(info.installed_scripts)),
            )
        info.last_sync = now
        return info

    def get_client(self, client_id: str) -> ClientInfo | None:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,)).fetchone()
        if not row:
            return None
        return ClientInfo(
            client_id=row["client_id"], hostname=row["hostname"],
            username=row["username"], orcad_version=row["orcad_version"],
            last_sync=row["last_sync"],
            installed_scripts=json.loads(row["installed_scripts"] or "[]"),
        )

    def list_clients(self) -> list[ClientInfo]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM clients ORDER BY last_sync DESC").fetchall()
        return [
            ClientInfo(
                client_id=r["client_id"], hostname=r["hostname"],
                username=r["username"], orcad_version=r["orcad_version"],
                last_sync=r["last_sync"],
                installed_scripts=json.loads(r["installed_scripts"] or "[]"),
            )
            for r in rows
        ]

    # ── Sessions ─────────────────────────────────────────────────

    def save_session(self, session_id: str, messages: list[dict]) -> None:
        now = _now()
        messages_json = json.dumps(messages)
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO sessions (id, messages, created_at, last_active)
                   VALUES (?, ?, COALESCE((SELECT created_at FROM sessions WHERE id = ?), ?), ?)""",
                (session_id, messages_json, session_id, now, now),
            )

    def get_session(self, session_id: str) -> list[dict] | None:
        with self._get_conn() as conn:
            row = conn.execute("SELECT messages FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            return None
        return json.loads(row["messages"])

    def delete_oldest_session(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM sessions WHERE id = (SELECT id FROM sessions ORDER BY last_active ASC LIMIT 1)"
            )

    def count_sessions(self) -> int:
        with self._get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM sessions").fetchone()
        return row["cnt"]

    # ── TCL Check Results ────────────────────────────────────────

    def save_tcl_result(self, result_id: str, design_name: str, source: str,
                        timestamp: str, data: dict) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO tcl_check_results (result_id, design_name, source, timestamp, data)
                   VALUES (?, ?, ?, ?, ?)""",
                (result_id, design_name, source, timestamp, json.dumps(data)),
            )

    def get_tcl_result(self, result_id: str) -> dict | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM tcl_check_results WHERE result_id = ?", (result_id,)
            ).fetchone()
        if not row:
            return None
        return {
            "result_id": row["result_id"],
            "design_name": row["design_name"],
            "source": row["source"],
            "timestamp": row["timestamp"],
            "results": json.loads(row["data"]),
        }

    def list_tcl_results(self, limit: int = 20) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM tcl_check_results ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {
                "result_id": r["result_id"],
                "design_name": r["design_name"],
                "source": r["source"],
                "timestamp": r["timestamp"],
                "results": json.loads(r["data"]),
            }
            for r in rows
        ]

    def evict_oldest_tcl_result(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM tcl_check_results WHERE result_id = "
                "(SELECT result_id FROM tcl_check_results ORDER BY timestamp ASC LIMIT 1)"
            )

    # ── OTA Manifest ─────────────────────────────────────────────

    def build_ota_manifest(self, client_id: str | None = None) -> OTAManifest:
        """Build OTA manifest of all published scripts."""
        published = self.list_scripts(status="published")

        # If client given, only include scripts newer than client's last sync
        if client_id:
            client = self.get_client(client_id)
            if client and client.last_sync:
                published = [s for s in published if s.updated_at > client.last_sync]

        return OTAManifest(
            server_version="0.1.0",
            scripts=published,
            timestamp=_now(),
        )

    # ── Helpers ──────────────────────────────────────────────────

    def _row_to_meta(self, row) -> ScriptMeta:
        return ScriptMeta(
            id=row["id"], name=row["name"], description=row["description"],
            version=row["version"], category=row["category"], status=row["status"],
            author=row["author"], tags=json.loads(row["tags"] or "[]"),
            created_at=row["created_at"], updated_at=row["updated_at"],
            checksum=row["checksum"],
        )

    def _row_to_script_content(self, row) -> ScriptContent:
        return ScriptContent(meta=self._row_to_meta(row), code=row["code"])

    def _row_to_doc(self, row) -> KnowledgeDoc:
        return KnowledgeDoc(
            id=row["id"], title=row["title"], category=row["category"],
            content=row["content"], tags=json.loads(row["tags"] or "[]"),
            created_at=row["created_at"], updated_at=row["updated_at"],
        )

    @staticmethod
    def _bump_version(version: str) -> str:
        parts = version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)
