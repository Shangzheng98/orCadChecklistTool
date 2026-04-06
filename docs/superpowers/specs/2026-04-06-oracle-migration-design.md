# SQLite to Oracle Database Migration Design

**Date:** 2026-04-06
**Status:** Approved

## Goal

将 OrCAD Checker 的数据库从 SQLite 迁移到 Oracle，支持 10-20 个内部用户并发使用。

## Context

- **当前状态:** SQLite 单文件数据库，自制 Queue 连接池（5 连接），raw SQL
- **目标状态:** Oracle 10+，oracledb 连接池，命名参数 SQL
- **Oracle 环境:** 已有 DBA 管理的实例，已分配 schema/用户，JDBC URL 连接
- **数据迁移:** 不需要，全新开始
- **SQLite 兼容:** 不保留，完全替换

## Architecture

### Connection Configuration

通过环境变量配置：

```
ORACLE_JDBC_URL=jdbc:oracle:thin:@host:1521:SID
ORACLE_USER=orcad_checker
ORACLE_PASSWORD=xxx
ORACLE_POOL_MIN=2
ORACLE_POOL_MAX=10
```

新增 `src/orcad_checker/store/config.py` 解析 JDBC URL，提取 host、port、SID/service_name，构造 oracledb DSN。

```python
@dataclass
class OracleConfig:
    host: str
    port: int
    sid: str
    user: str
    password: str
    pool_min: int = 2
    pool_max: int = 10

    @classmethod
    def from_env(cls) -> "OracleConfig":
        jdbc_url = os.environ["ORACLE_JDBC_URL"]
        # 解析 jdbc:oracle:thin:@host:port:SID
        ...
```

### Connection Pool

替换现有 `Queue` 手工池，使用 `oracledb.ConnectionPool`：

```python
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
```

- `min=2, max=10` — 10-20 并发用户够用
- 超时 5 秒 — 替代现有 Queue 的无限等待

### Transaction Management

保持 `_get_conn()` context manager 模式：

```python
@contextmanager
def _get_conn(self):
    conn = self._pool.acquire()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        self._pool.release(conn)
```

### Async Compatibility

不变。Database 方法保持同步，FastAPI 路由继续通过 `run_in_threadpool` 包装。oracledb 连接池本身线程安全。

---

## SQL Adaptation

### DDL Type Mapping

| SQLite | Oracle | 说明 |
|--------|--------|------|
| `TEXT` (短字段) | `VARCHAR2(N)` | name/version/status/author 等 |
| `TEXT` (长字段) | `CLOB` | code/content/messages/data/tags |
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `NUMBER GENERATED ALWAYS AS IDENTITY` | script_versions.id |
| `CREATE TABLE IF NOT EXISTS` | PL/SQL + ORA-00955 异常捕获 | 初始化逻辑 |
| `PRAGMA journal_mode=WAL` | 删除 | Oracle 自带 redo log |

### DML Changes

| SQLite | Oracle | 影响范围 |
|--------|--------|----------|
| `?` 占位符 | `:name` 命名参数 | 所有 ~20 个查询 |
| `INSERT OR REPLACE INTO` | `MERGE INTO ... USING DUAL ON ... WHEN MATCHED THEN UPDATE WHEN NOT MATCHED THEN INSERT` | clients, sessions (2 处) |
| `ORDER BY ... LIMIT ?` | `FETCH FIRST :n ROWS ONLY` (Oracle 12c+) | list_tcl_results, search |
| `LIKE '%xxx%'` | 不变 | search 查询 |
| JSON 存为 TEXT | JSON 存为 CLOB | 不变，保持 json.dumps/loads |

### Table Definitions

```sql
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
);

CREATE TABLE script_versions (
    id            NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    script_id     VARCHAR2(8)    NOT NULL REFERENCES scripts(id),
    version       VARCHAR2(20)   NOT NULL,
    code          CLOB           NOT NULL,
    changelog     CLOB           DEFAULT '',
    checksum      VARCHAR2(64)   DEFAULT '',
    created_at    VARCHAR2(50)   NOT NULL
);

CREATE TABLE knowledge_docs (
    id            VARCHAR2(8)    PRIMARY KEY,
    title         VARCHAR2(500)  NOT NULL,
    category      VARCHAR2(50)   DEFAULT 'api',
    content       CLOB           NOT NULL,
    tags          CLOB           DEFAULT '[]',
    created_at    VARCHAR2(50)   NOT NULL,
    updated_at    VARCHAR2(50)   NOT NULL
);

CREATE TABLE clients (
    client_id         VARCHAR2(50)   PRIMARY KEY,
    hostname          VARCHAR2(200)  DEFAULT '',
    username          VARCHAR2(100)  DEFAULT '',
    orcad_version     VARCHAR2(20)   DEFAULT '',
    last_sync         VARCHAR2(50)   DEFAULT '',
    installed_scripts CLOB           DEFAULT '[]'
);

CREATE TABLE sessions (
    id            VARCHAR2(20)   PRIMARY KEY,
    messages      CLOB           DEFAULT '[]',
    created_at    VARCHAR2(50)   NOT NULL,
    last_active   VARCHAR2(50)   NOT NULL
);

CREATE TABLE tcl_check_results (
    result_id     VARCHAR2(50)   PRIMARY KEY,
    design_name   VARCHAR2(200)  DEFAULT '',
    source        VARCHAR2(50)   DEFAULT '',
    timestamp     VARCHAR2(50)   NOT NULL,
    data          CLOB           NOT NULL
);
```

### Parameter Binding Example

```python
# SQLite (before):
conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,))

# Oracle (after):
cursor.execute("SELECT * FROM scripts WHERE id = :id", {"id": script_id})
```

### MERGE INTO Example (replaces INSERT OR REPLACE)

```python
# SQLite (before):
conn.execute("INSERT OR REPLACE INTO sessions (id, messages, ...) VALUES (?, ?, ...)")

# Oracle (after):
cursor.execute("""
    MERGE INTO sessions s
    USING DUAL ON (s.id = :id)
    WHEN MATCHED THEN UPDATE SET
        s.messages = :messages, s.last_active = :last_active
    WHEN NOT MATCHED THEN INSERT
        (id, messages, created_at, last_active)
        VALUES (:id, :messages, :created_at, :last_active)
""", {"id": session_id, "messages": messages_json, ...})
```

---

## Table Initialization

Oracle 没有 `CREATE TABLE IF NOT EXISTS`，使用异常捕获：

```python
def _init_tables(self):
    ddl_statements = [("scripts", CREATE_SCRIPTS_DDL), ...]
    with self._get_conn() as conn:
        cursor = conn.cursor()
        for table_name, ddl in ddl_statements:
            try:
                cursor.execute(ddl)
            except oracledb.DatabaseError as e:
                if e.args[0].code == 955:  # ORA-00955: name already used
                    pass
                else:
                    raise
```

---

## Error Handling

| 场景 | Oracle 错误 | 处理 |
|------|------------|------|
| 连接池超时 | `oracledb.PoolError` | 返回 HTTP 503 |
| 唯一键冲突 | ORA-00001 `IntegrityError` | 上层业务处理 |
| 表已存在 | ORA-00955 | 初始化时 pass |
| 连接断开 | pool 自动 ping + 重连 | 透明恢复 |

---

## Row Factory

SQLite 用 `sqlite3.Row`（dict-like 访问 `row["field"]`）。Oracle 用 cursor + namedtuple 或手工转换：

```python
def _execute_query(self, sql: str, params: dict = None) -> list[dict]:
    with self._get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params or {})
        columns = [col[0].lower() for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
```

所有现有的 `row["field"]` 访问保持不变（dict key 访问）。

---

## CLOB Handling

oracledb 默认将 CLOB 作为 `oracledb.LOB` 对象返回（需要 `.read()`）。配置为自动转 string：

```python
def _type_handler(cursor, metadata):
    if metadata.type_code is oracledb.DB_TYPE_CLOB:
        return cursor.var(str, arraysize=cursor.arraysize)

# 在 acquire 连接后设置
conn.outputtypehandler = _type_handler
```

这样所有 CLOB 字段自动作为 Python str 返回，不需要改动上层代码。

---

## File Changes

| Action | File | Description |
|--------|------|-------------|
| Create | `src/orcad_checker/store/config.py` | OracleConfig 数据类 + JDBC URL 解析 |
| Rewrite | `src/orcad_checker/store/database.py` | sqlite3 → oracledb, 所有 SQL 适配 |
| Modify | `src/orcad_checker/web/app.py` | Database 初始化传入 OracleConfig |
| Modify | `pyproject.toml` | 添加 `oracledb>=2.0` 依赖 |
| Modify | `tests/test_store.py` | Oracle 测试 fixture + TRUNCATE 清理 |
| Modify | `tests/conftest.py` | Oracle 跳过逻辑 |
| No change | `src/orcad_checker/web/deps.py` | 已是注入模式 |
| No change | `src/orcad_checker/web/routes/*.py` | 不直接依赖 sqlite3 |
| No change | `src/orcad_checker/ai/tcl_agent.py` | 通过 Database 接口调用 |

---

## Testing Strategy

| 场景 | 策略 |
|------|------|
| CI/本地有 Oracle | 用 `ORACLE_TEST_*` 环境变量指向测试 schema，测试后 TRUNCATE |
| 无 Oracle | `pytest.mark.skipif` 跳过数据库测试 |

```python
import pytest
import os

SKIP_ORACLE = not os.environ.get("ORACLE_TEST_JDBC_URL")

@pytest.fixture
def db():
    if SKIP_ORACLE:
        pytest.skip("Oracle not configured")
    config = OracleConfig.from_env(prefix="ORACLE_TEST_")
    database = Database(config)
    yield database
    database.truncate_all()
```

---

## Dependencies

```toml
# pyproject.toml
dependencies = [
    # ... existing ...
    "oracledb>=2.0",
]
```

Remove: no explicit sqlite3 removal needed (it's stdlib, just stop importing it).

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ORACLE_JDBC_URL` | Yes | — | `jdbc:oracle:thin:@host:port:SID` |
| `ORACLE_USER` | Yes | — | Oracle 用户名 |
| `ORACLE_PASSWORD` | Yes | — | Oracle 密码 |
| `ORACLE_POOL_MIN` | No | `2` | 连接池最小连接数 |
| `ORACLE_POOL_MAX` | No | `10` | 连接池最大连接数 |
