"""Oracle-based storage for scripts, versions, knowledge docs, clients, sessions, and TCL results."""
from __future__ import annotations

import hashlib
import json
import logging
import uuid

logger = logging.getLogger(__name__)
from contextlib import contextmanager
from datetime import datetime, timezone

import oracledb

from orcad_checker.models.scripts import (
    ClientInfo,
    KnowledgeDoc,
    OTAManifest,
    ScriptContent,
    ScriptMeta,
    ScriptStatus,
    ScriptVersion,
)
from orcad_checker.store.config import OracleConfig


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _checksum(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]


def _clob_type_handler(cursor, metadata):
    """将 CLOB 自动转换为 Python str，避免返回 LOB 对象。"""
    if metadata.type_code is oracledb.DB_TYPE_CLOB:
        return cursor.var(str, arraysize=cursor.arraysize)


# ── DDL ─────────────────────────────────────────────────────────

_DDL_SCRIPTS = """
CREATE TABLE scripts (
    id            VARCHAR2(8)    PRIMARY KEY,
    name          VARCHAR2(200)  NOT NULL,
    description   VARCHAR2(4000) DEFAULT '',
    version       VARCHAR2(20)   DEFAULT '1.0.0',
    category      VARCHAR2(50)   DEFAULT 'custom',
    status        VARCHAR2(20)   DEFAULT 'draft',
    author        VARCHAR2(100)  DEFAULT '',
    tags          CLOB           DEFAULT '[]',
    code          CLOB           DEFAULT '',
    checksum      VARCHAR2(64)   DEFAULT '',
    created_at    VARCHAR2(50)   NOT NULL,
    updated_at    VARCHAR2(50)   NOT NULL
)"""

_DDL_SCRIPT_VERSIONS = """
CREATE TABLE script_versions (
    id            NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    script_id     VARCHAR2(8)    NOT NULL REFERENCES scripts(id),
    version       VARCHAR2(20)   NOT NULL,
    code          CLOB           NOT NULL,
    changelog     CLOB           DEFAULT '',
    checksum      VARCHAR2(64)   DEFAULT '',
    created_at    VARCHAR2(50)   NOT NULL
)"""

_DDL_KNOWLEDGE_DOCS = """
CREATE TABLE knowledge_docs (
    id            VARCHAR2(8)    PRIMARY KEY,
    title         VARCHAR2(500)  NOT NULL,
    category      VARCHAR2(50)   DEFAULT 'api',
    content       CLOB           NOT NULL,
    tags          CLOB           DEFAULT '[]',
    created_at    VARCHAR2(50)   NOT NULL,
    updated_at    VARCHAR2(50)   NOT NULL
)"""

_DDL_CLIENTS = """
CREATE TABLE clients (
    client_id         VARCHAR2(50)   PRIMARY KEY,
    hostname          VARCHAR2(200)  DEFAULT '',
    username          VARCHAR2(100)  DEFAULT '',
    orcad_version     VARCHAR2(20)   DEFAULT '',
    last_sync         VARCHAR2(50)   DEFAULT '',
    installed_scripts CLOB           DEFAULT '[]'
)"""

_DDL_SESSIONS = """
CREATE TABLE sessions (
    id            VARCHAR2(20)   PRIMARY KEY,
    messages      CLOB           DEFAULT '[]',
    created_at    VARCHAR2(50)   NOT NULL,
    last_active   VARCHAR2(50)   NOT NULL
)"""

_DDL_TCL_CHECK_RESULTS = """
CREATE TABLE tcl_check_results (
    result_id     VARCHAR2(50)   PRIMARY KEY,
    design_name   VARCHAR2(200)  DEFAULT '',
    source        VARCHAR2(50)   DEFAULT '',
    timestamp     VARCHAR2(50)   NOT NULL,
    data          CLOB           NOT NULL
)"""

_ALL_DDL = [
    ("scripts", _DDL_SCRIPTS),
    ("script_versions", _DDL_SCRIPT_VERSIONS),
    ("knowledge_docs", _DDL_KNOWLEDGE_DOCS),
    ("clients", _DDL_CLIENTS),
    ("sessions", _DDL_SESSIONS),
    ("tcl_check_results", _DDL_TCL_CHECK_RESULTS),
]


class Database:
    """Oracle 数据库访问层。

    提供脚本、版本、知识库文档、客户端、会话和检查结果的 CRUD 操作。
    使用 oracledb 连接池管理连接，支持并发访问。
    """

    def __init__(self, config: OracleConfig):
        self._config = config
        dsn = config.make_dsn()
        self._pool = oracledb.create_pool(
            user=config.user,
            password=config.password,
            dsn=dsn,
            min=config.pool_min,
            max=config.pool_max,
            increment=1,
            getmode=oracledb.POOL_GETMODE_TIMEDWAIT,
            wait_timeout=5000,
        )
        self._init_tables()

    @contextmanager
    def _get_conn(self):
        """获取连接并自动管理事务。成功时 commit，异常时 rollback。"""
        conn = self._pool.acquire()
        conn.outputtypehandler = _clob_type_handler
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.release(conn)

    def _init_tables(self):
        """创建数据库表。如果表已存在则跳过 (ORA-00955)。"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            for table_name, ddl in _ALL_DDL:
                try:
                    cursor.execute(ddl)
                    logger.info("Created table: %s", table_name)
                except oracledb.DatabaseError as e:
                    error_obj = e.args[0]
                    if error_obj.code == 955:  # ORA-00955: name is already used
                        pass
                    else:
                        raise

    def _execute_query(self, sql: str, params: dict | None = None) -> list[dict]:
        """执行查询并返回 dict 列表。列名自动转小写。"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params or {})
            if cursor.description is None:
                return []
            columns = [col[0].lower() for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _execute_one(self, sql: str, params: dict | None = None) -> dict | None:
        """执行查询并返回第一行 (dict) 或 None。"""
        rows = self._execute_query(sql, params)
        return rows[0] if rows else None

    def close(self):
        """关闭连接池。"""
        self._pool.close()

    def truncate_all(self):
        """清空所有表数据。用于测试清理。"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            for table in ["script_versions", "scripts", "knowledge_docs",
                          "clients", "sessions", "tcl_check_results"]:
                cursor.execute(f"DELETE FROM {table}")

    # ── Scripts CRUD ─────────────────────────────────────────────

    def create_script(self, meta: ScriptMeta, code: str) -> ScriptContent:
        script_id = meta.id or str(uuid.uuid4())[:8]
        now = _now()
        cs = _checksum(code)
        tags_json = json.dumps(meta.tags)

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO scripts
                   (id, name, description, version, category, status, author, tags, code, checksum, created_at, updated_at)
                   VALUES (:id, :name, :description, :version, :category, :status, :author, :tags, :code, :checksum, :created_at, :updated_at)""",
                {
                    "id": script_id, "name": meta.name, "description": meta.description,
                    "version": meta.version, "category": meta.category.value,
                    "status": meta.status.value, "author": meta.author,
                    "tags": tags_json, "code": code, "checksum": cs,
                    "created_at": now, "updated_at": now,
                },
            )
            cursor.execute(
                """INSERT INTO script_versions (script_id, version, code, changelog, checksum, created_at)
                   VALUES (:script_id, :version, :code, :changelog, :checksum, :created_at)""",
                {
                    "script_id": script_id, "version": meta.version,
                    "code": code, "changelog": "Initial version",
                    "checksum": cs, "created_at": now,
                },
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
        row = self._execute_one("SELECT * FROM scripts WHERE id = :id", {"id": script_id})
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
        params: dict = {}
        if status:
            query += " AND status = :status"
            params["status"] = status
        if category:
            query += " AND category = :category"
            params["category"] = category
        if search:
            query += " AND (name LIKE :s1 OR description LIKE :s2 OR tags LIKE :s3)"
            like = f"%{search}%"
            params["s1"] = like
            params["s2"] = like
            params["s3"] = like
        query += " ORDER BY updated_at DESC"
        rows = self._execute_query(query, params)
        return [self._row_to_meta(r) for r in rows]

    def update_script(self, script_id: str, meta: ScriptMeta | None = None,
                      code: str | None = None, changelog: str = "") -> ScriptContent | None:
        existing = self.get_script(script_id)
        if not existing:
            return None

        now = _now()
        updates = []
        params: dict = {}

        if meta:
            if meta.name:
                updates.append("name = :p_name"); params["p_name"] = meta.name
            if meta.description:
                updates.append("description = :p_desc"); params["p_desc"] = meta.description
            if meta.category:
                updates.append("category = :p_cat"); params["p_cat"] = meta.category.value
            if meta.status:
                updates.append("status = :p_status"); params["p_status"] = meta.status.value
            if meta.author:
                updates.append("author = :p_author"); params["p_author"] = meta.author
            if meta.tags:
                updates.append("tags = :p_tags"); params["p_tags"] = json.dumps(meta.tags)

        new_version = existing.meta.version
        cs = ""
        if code is not None:
            cs = _checksum(code)
            new_version = self._bump_version(existing.meta.version)
            updates.extend(["code = :p_code", "version = :p_ver", "checksum = :p_cs"])
            params["p_code"] = code
            params["p_ver"] = new_version
            params["p_cs"] = cs

        updates.append("updated_at = :p_updated")
        params["p_updated"] = now
        params["p_id"] = script_id

        with self._get_conn() as conn:
            cursor = conn.cursor()
            if code is not None:
                cursor.execute(
                    """INSERT INTO script_versions (script_id, version, code, changelog, checksum, created_at)
                       VALUES (:script_id, :version, :code, :changelog, :checksum, :created_at)""",
                    {
                        "script_id": script_id, "version": new_version,
                        "code": code, "changelog": changelog,
                        "checksum": cs, "created_at": now,
                    },
                )
            cursor.execute(
                f"UPDATE scripts SET {', '.join(updates)} WHERE id = :p_id", params
            )

        return self.get_script(script_id)

    def delete_script(self, script_id: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM script_versions WHERE script_id = :id", {"id": script_id})
            cursor.execute("DELETE FROM scripts WHERE id = :id", {"id": script_id})
            return cursor.rowcount > 0

    def get_script_versions(self, script_id: str) -> list[ScriptVersion]:
        rows = self._execute_query(
            "SELECT * FROM script_versions WHERE script_id = :id ORDER BY created_at DESC",
            {"id": script_id},
        )
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
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO knowledge_docs (id, title, category, content, tags, created_at, updated_at)
                   VALUES (:id, :title, :category, :content, :tags, :created_at, :updated_at)""",
                {
                    "id": doc_id, "title": doc.title, "category": doc.category,
                    "content": doc.content, "tags": tags_json,
                    "created_at": now, "updated_at": now,
                },
            )
        doc.id = doc_id
        doc.created_at = now
        doc.updated_at = now
        return doc

    def get_doc(self, doc_id: str) -> KnowledgeDoc | None:
        row = self._execute_one("SELECT * FROM knowledge_docs WHERE id = :id", {"id": doc_id})
        if not row:
            return None
        return self._row_to_doc(row)

    def list_docs(self, category: str | None = None, search: str | None = None) -> list[KnowledgeDoc]:
        query = "SELECT * FROM knowledge_docs WHERE 1=1"
        params: dict = {}
        if category:
            query += " AND category = :category"
            params["category"] = category
        if search:
            query += " AND (title LIKE :s1 OR content LIKE :s2 OR tags LIKE :s3)"
            like = f"%{search}%"
            params["s1"] = like
            params["s2"] = like
            params["s3"] = like
        query += " ORDER BY updated_at DESC"
        rows = self._execute_query(query, params)
        return [self._row_to_doc(r) for r in rows]

    def update_doc(self, doc_id: str, doc: KnowledgeDoc) -> KnowledgeDoc | None:
        now = _now()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE knowledge_docs SET title=:title, category=:category,
                   content=:content, tags=:tags, updated_at=:updated_at
                   WHERE id=:id""",
                {
                    "title": doc.title, "category": doc.category,
                    "content": doc.content, "tags": json.dumps(doc.tags),
                    "updated_at": now, "id": doc_id,
                },
            )
            if cursor.rowcount == 0:
                return None
        return self.get_doc(doc_id)

    def delete_doc(self, doc_id: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM knowledge_docs WHERE id = :id", {"id": doc_id})
            return cursor.rowcount > 0

    def search_knowledge(self, query: str, limit: int = 10) -> list[KnowledgeDoc]:
        """Search knowledge base by keyword relevance."""
        return self.list_docs(search=query)[:limit]

    # ── Clients ──────────────────────────────────────────────────

    def register_client(self, info: ClientInfo) -> ClientInfo:
        now = _now()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """MERGE INTO clients c
                   USING DUAL ON (c.client_id = :client_id)
                   WHEN MATCHED THEN UPDATE SET
                       hostname = :hostname, username = :username,
                       orcad_version = :orcad_version, last_sync = :last_sync,
                       installed_scripts = :installed_scripts
                   WHEN NOT MATCHED THEN INSERT
                       (client_id, hostname, username, orcad_version, last_sync, installed_scripts)
                       VALUES (:client_id, :hostname, :username, :orcad_version, :last_sync, :installed_scripts)""",
                {
                    "client_id": info.client_id, "hostname": info.hostname,
                    "username": info.username, "orcad_version": info.orcad_version,
                    "last_sync": now,
                    "installed_scripts": json.dumps(info.installed_scripts),
                },
            )
        info.last_sync = now
        return info

    def get_client(self, client_id: str) -> ClientInfo | None:
        row = self._execute_one("SELECT * FROM clients WHERE client_id = :id", {"id": client_id})
        if not row:
            return None
        return ClientInfo(
            client_id=row["client_id"], hostname=row["hostname"],
            username=row["username"], orcad_version=row["orcad_version"],
            last_sync=row["last_sync"],
            installed_scripts=json.loads(row["installed_scripts"] or "[]"),
        )

    def list_clients(self) -> list[ClientInfo]:
        rows = self._execute_query("SELECT * FROM clients ORDER BY last_sync DESC")
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
            cursor = conn.cursor()
            cursor.execute(
                """MERGE INTO sessions s
                   USING DUAL ON (s.id = :id)
                   WHEN MATCHED THEN UPDATE SET
                       messages = :messages, last_active = :last_active
                   WHEN NOT MATCHED THEN INSERT
                       (id, messages, created_at, last_active)
                       VALUES (:id, :messages, :created_at, :last_active)""",
                {
                    "id": session_id, "messages": messages_json,
                    "created_at": now, "last_active": now,
                },
            )

    def get_session(self, session_id: str) -> list[dict] | None:
        row = self._execute_one("SELECT messages FROM sessions WHERE id = :id", {"id": session_id})
        if not row:
            return None
        return json.loads(row["messages"])

    def delete_oldest_session(self) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """DELETE FROM sessions WHERE id = (
                    SELECT id FROM sessions ORDER BY last_active ASC FETCH FIRST 1 ROWS ONLY
                )"""
            )

    def count_sessions(self) -> int:
        row = self._execute_one("SELECT COUNT(*) as cnt FROM sessions")
        return row["cnt"] if row else 0

    # ── TCL Check Results ────────────────────────────────────────

    def save_tcl_result(self, result_id: str, design_name: str, source: str,
                        timestamp: str, data: dict) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO tcl_check_results (result_id, design_name, source, timestamp, data)
                   VALUES (:result_id, :design_name, :source, :timestamp, :data)""",
                {
                    "result_id": result_id, "design_name": design_name,
                    "source": source, "timestamp": timestamp,
                    "data": json.dumps(data),
                },
            )

    def get_tcl_result(self, result_id: str) -> dict | None:
        row = self._execute_one(
            "SELECT * FROM tcl_check_results WHERE result_id = :id", {"id": result_id}
        )
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
        rows = self._execute_query(
            "SELECT * FROM tcl_check_results ORDER BY timestamp DESC FETCH FIRST :lim ROWS ONLY",
            {"lim": limit},
        )
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
            cursor = conn.cursor()
            cursor.execute(
                """DELETE FROM tcl_check_results WHERE result_id = (
                    SELECT result_id FROM tcl_check_results ORDER BY timestamp ASC FETCH FIRST 1 ROWS ONLY
                )"""
            )

    # ── OTA Manifest ─────────────────────────────────────────────

    def build_ota_manifest(self, client_id: str | None = None) -> OTAManifest:
        published = self.list_scripts(status="published")
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

    def _row_to_meta(self, row: dict) -> ScriptMeta:
        return ScriptMeta(
            id=row["id"], name=row["name"], description=row["description"],
            version=row["version"], category=row["category"], status=row["status"],
            author=row["author"], tags=json.loads(row["tags"] or "[]"),
            created_at=row["created_at"], updated_at=row["updated_at"],
            checksum=row["checksum"],
        )

    def _row_to_script_content(self, row: dict) -> ScriptContent:
        return ScriptContent(meta=self._row_to_meta(row), code=row["code"])

    def _row_to_doc(self, row: dict) -> KnowledgeDoc:
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
