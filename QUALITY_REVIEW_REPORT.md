# OrCAD Checklist Tool -- 综合质量评审报告

**评审日期**: 2026-04-06  
**评审版本**: v0.1.0 (commit 8c6396a)  
**评审角色**: 质量审核员  
**评审范围**: TCL 前端 + Python 后端 + 前端 UI + 部署配置

---

## 1. 项目成熟度评估

**判定: Late Alpha / Early Beta**

| 维度 | 状态 | 说明 |
|------|------|------|
| 核心功能 | Beta | 19 个 TCL 检查器结构统一，DBO API 适配层经过实际验证 |
| 后端服务 | Alpha | FastAPI 路由完整，但无认证、无日志、无速率限制 |
| AI 功能 | Alpha | 基本对话可用，但无流式输出、无 token 计量、无错误恢复 |
| 前端 UI | Alpha | Tk GUI 功能完整但 732 行单文件；Vue 前端框架已搭建但页面不完整 |
| 测试 | Pre-Alpha | 仅 6 个测试文件，覆盖率约 10%，19 个检查器仅 2 个有单元测试 |
| 部署 | Beta | Docker 多阶段构建 + docker-compose + 健康检查，可用于开发环境 |
| 文档 | Alpha | CLAUDE.md 质量极高（DBO API 陷阱文档），但用户文档和 API 文档缺失 |

**总结**: 项目核心价值（OrCAD DBO TCL 检查器 + API 知识库）已达到 Beta 质量，但工程基础设施（测试、日志、安全）仍处于 Alpha。不建议在当前状态下投入生产使用。

---

## 2. 安全性评审

### 2.1 API 密钥处理 -- 评分: 7/10

**已做好的**:
- API 密钥通过环境变量读取（`os.environ.get`），未硬编码
- `.gitignore` 已排除 `.env` 文件
- Docker 环境变量默认值为空字符串

**风险点**:
- `Dockerfile` 第 46-52 行将 `ANTHROPIC_API_KEY=""` 写入镜像层的 ENV 中，虽然值为空，但如果通过 `docker build --build-arg` 传入密钥，密钥会被烘焙进镜像的中间层
- `openai_client.py:21` -- `api_key=api_key or "not-needed"` 允许无密钥调用，对内部部署合理，但应有明确文档说明

### 2.2 输入验证 -- 评分: 5/10

**已做好的**:
- Pydantic BaseModel 在 API 层提供了基本的类型验证（`TclResultUpload`, `ChatRequest` 等）
- SQL 查询全部使用参数化（`?` 占位符），**无 SQL 注入风险**

**风险点**:
- **CORS 配置过宽**: `app.py:14-26` 允许 `allow_credentials=True`，且 `ALLOWED_ORIGINS` 可通过环境变量设置为任意值，包括 `*`
- **无认证机制**: 所有 API 端点完全开放，任何人可以上传检查结果、删除知识库文档、执行 AI 对话
- **无输入长度限制**: `ChatRequest.message` 无最大长度限制，恶意用户可发送超大消息消耗 LLM tokens
- **TCL 代码注入**: `gui/main_window.tcl:446` 使用 `uplevel #0 $::ai_fetched_code` 直接执行从服务器获取的代码，虽有确认对话框，但代码内容完全不受限

### 2.3 敏感数据保护 -- 评分: 6/10

- 会话消息存储在 SQLite 中（`sessions` 表），包含完整对话历史，无加密
- 会话数量有上限（MAX_SESSIONS=200），但无单个会话的消息数量限制
- 无审计日志记录谁访问了什么数据

### 2.4 安全性总评: 5/10

**对于当前使用场景（内网工具）可接受，但不适合暴露到公网**。

---

## 3. 性能与可靠性评估 -- 评分: 6/10

### 3.1 性能

**TCL 端**:
- `build_net_components_map` 和 `collect_power_net_names` 有缓存机制，避免重复遍历设计数据
- 使用 `lsearch -exact` 检查列表成员（`checker_utils.tcl:71,83`），大量电源网络时 O(n) 查找效率低，应改用 dict/array
- `check_i2c_pullups.tcl:51` 嵌套遍历 `dict for` 全部网络来查找电阻器的其他连接，O(n*m) 复杂度

**Python 端**:
- `Database` 使用连接池（pool_size=5）+ WAL 模式，SQLite 并发性能合理
- `discover_checkers()` 在每次 GET `/api/v1/checkers` 时重新扫描模块，应缓存结果
- LLM 调用是同步阻塞的（通过 `run_in_threadpool` 包装），不支持流式响应

### 3.2 可靠性

**问题**:
- **无重试机制**: `http_client.tcl` 的 `http_get`/`http_post` 失败即抛异常，无重试逻辑
- **无超时配置**: HTTP GET 超时 15s，POST 超时 30s，固定值无法调整
- **无断线重连**: TCL 客户端与服务器断开后，无自动重连机制
- **无优雅降级**: AI 服务不可用时，`agent_chat` 路由返回错误字符串而非标准错误格式（`agent.py:89`）

**已做好的**:
- Docker 健康检查 + `restart: unless-stopped`
- `check_engine.tcl:82` 使用 `catch` 包裹每个检查器执行，单个检查器崩溃不影响其他
- DBO API 适配层全面使用 `catch` 保护，避免 SWIG 绑定异常传播

---

## 4. 错误处理与日志评估 -- 评分: 4/10

### 4.1 错误处理

**TCL 端** (6/10):
- DBO API 调用全面使用 `catch`，质量好
- 检查引擎捕获检查器异常并继续执行
- GUI 操作有 `tk_messageBox` 错误提示

**Python 端** (4/10):
- `agent.py:86-92`: 捕获所有异常并返回 `Error: {e}` 字符串，丢失堆栈信息，返回 HTTP 200 而非 4xx/5xx
- `checks.py:46-48`: `json.loads(content)` 解析失败会抛出未处理的 `JSONDecodeError`
- `database.py:57-58`: 数据库异常只 rollback，不记录日志

### 4.2 日志

**严重缺陷: 整个 Python 后端没有使用 `logging` 模块**。

经全文搜索确认，`src/orcad_checker/` 目录下无任何 `import logging` 或 `logger` 使用。所有错误信息要么被吞掉（`catch`），要么作为 HTTP 响应返回给客户端。这意味着：
- 生产环境无法排查问题
- 无法监控 API 调用频率
- 无法追踪 LLM 调用成本
- 无法审计用户操作

---

## 5. 可维护性与可测试性评估 -- 评分: 6/10

### 5.1 可维护性

**优势**:
- Python 端使用 Registry Pattern 和依赖注入（`get_db`），检查器扩展方便
- TCL 检查器模板统一（`check_result` + `finding` 结构），新增检查器有明确步骤
- DBO API 适配层隔离了 OrCAD SWIG 绑定的复杂性
- CLAUDE.md 详细记录了 API 陷阱和集成清单

**问题**:
- **TCL/Python 双重维护**: 检查器在两端都有实现（TCL 19 个 vs Python 7 个），规则逻辑不同步
- **GUI 单文件过大**: `main_window.tcl` 732 行包含 3 个 Tab 的全部逻辑，应拆分
- **全局变量污染**: TCL 端使用约 25 个 `::` 全局变量（检查器开关、会话状态、缓存等）

### 5.2 可测试性

- 测试文件: 6 个（`test_api.py`, `test_engine.py`, `test_parser.py`, `test_store.py`, `test_checkers/` 下 2 个）
- 19 个 TCL 检查器**零测试**（需要 OrCAD 环境，难以 mock）
- Python 检查器 7 个中有 2 个有测试
- 无集成测试、无端到端测试
- 无 CI/CD 配置文件

---

## 6. 配置管理与部署流程评估 -- 评分: 7/10

### 6.1 配置管理

**已做好的**:
- `pyproject.toml` 规范的 Python 包配置
- `docker-compose.yml` 使用环境变量和 `.env` 文件
- 规则配置支持 YAML 文件覆盖（`rule_loader.py`）
- SQLite 数据持久化通过 Docker volume

**缺失**:
- 无 `.env.example` 文件指导配置
- 无环境分离（dev/staging/prod）
- TCL 端 `server_url` 硬编码为 `localhost:8000`

### 6.2 部署流程

**已做好的**:
- 多阶段 Docker 构建，镜像精简
- 健康检查端点
- 数据卷持久化

**缺失**:
- 无 CI/CD 流水线（GitHub Actions / Jenkins）
- 无版本发布流程
- 无数据库迁移工具（表结构变更需手动处理）

---

## 7. 跨团队发现交叉验证

| 发现项 | 报告方 | 验证结果 |
|--------|--------|----------|
| 19 个 TCL 检查器达生产就绪（90%） | Task #1 | **部分同意**。结构统一且有 catch 保护，但 `check_i2c_pullups.tcl:55` 存在 `dict get` 访问 list 类型的 Critical Bug，实际为 85% |
| AI 功能完成度 60% | Task #2 | **同意**。基本对话链路通，但无流式、无 token 计量、知识搜索仅用 SQL LIKE |
| 代码注释覆盖率 7.7% | Task #3 | **同意**。Python 端有类型注解和 docstring，但 TCL 端主要依赖函数名自解释 |
| 全局变量污染 | Task #4 | **同意且更严重**。实际统计约 25+ 个 `::` 全局变量，部分在 GUI 中初始化但在其他文件中使用 |
| Critical Bug: dict get 访问 list | Task #5 | **确认**。`check_i2c_pullups.tcl:55` 的 `[dict get $other_comp refdes]` 应为 `[lindex $other_comp 0]`，这是运行时崩溃 Bug |
| 500+ 行重复代码 | Task #5 | **需要细化**。检查器间有模式重复（遍历 pages/parts/pins），但非逐行复制，更适合归类为可提取公共模式而非重复代码 |
| 架构评分 7/10 | Task #4 | **同意**。三层架构清晰，但通信层缺乏韧性（无重试、无超时配置），实际可执行性打折 |
| 测试覆盖率 10.5% | Task #5 | **同意**。6 个测试文件，2/19 检查器有测试，Python 端约 7 个检查器中 2 个有测试 |

### 遗漏项

各团队报告均**未提及**以下重要问题：
1. **零日志**: Python 后端完全没有 logging，这是生产环境的致命缺陷
2. **CORS 安全风险**: `allow_credentials=True` 配合可配置 origins 存在 CSRF 风险
3. **无 .env.example**: 新开发者无法知道需要配置哪些环境变量
4. **AI 响应返回 HTTP 200 包裹错误**: `agent.py:89` 将异常包装为正常响应返回

---

## 8. 综合评分

| 维度 | 评分 (1-10) | 权重 | 加权分 |
|------|-------------|------|--------|
| 功能完整性 | 7 | 20% | 1.40 |
| 代码质量 | 6 | 15% | 0.90 |
| 架构设计 | 7 | 15% | 1.05 |
| 安全性 | 5 | 15% | 0.75 |
| 可靠性 | 6 | 10% | 0.60 |
| 可测试性 | 4 | 10% | 0.40 |
| 错误处理与日志 | 4 | 5% | 0.20 |
| 文档 | 7 | 5% | 0.35 |
| 部署与运维 | 7 | 5% | 0.35 |
| **总体** | | **100%** | **6.0/10** |

**总体评级: C+ (Late Alpha)**

与各团队成员评分对比：
- 功能产品经理: 85% -> 本报告: 70% (考虑了 Bug 和安全缺陷)
- 架构师: 7/10 -> 本报告: 7/10 (一致)
- 代码编写员: 6/10 -> 本报告: 6/10 (一致)
- 文档编写员: 8.1/10 -> 本报告: 7/10 (CLAUDE.md 优秀但用户文档缺失严重)

---

## 9. 改进优先级排序

### P0 -- 必须立即修复（阻碍可用性）

| # | 行动项 | 涉及文件 | 预估工时 |
|---|--------|----------|----------|
| 1 | 修复 `dict get` 访问 list 类型 Bug | `tcl/checkers/check_i2c_pullups.tcl:55` | 0.5h |
| 2 | 添加 Python logging 基础设施 | `src/orcad_checker/web/app.py` + 各路由 | 4h |
| 3 | 修复 AI 错误响应返回 HTTP 200 | `src/orcad_checker/web/routes/agent.py:86-92` | 1h |
| 4 | 添加 API 认证（至少 API Key） | `src/orcad_checker/web/` | 4h |

### P1 -- 应尽快完成（影响可靠性）

| # | 行动项 | 涉及文件 | 预估工时 |
|---|--------|----------|----------|
| 5 | 添加 ChatRequest.message 长度限制 | `agent.py`, `knowledge.py` | 1h |
| 6 | HTTP 客户端添加重试机制 | `tcl/engine/http_client.tcl` | 3h |
| 7 | 核心检查器单元测试（至少覆盖 P0 级 5 个） | `tests/test_checkers/` | 8h |
| 8 | 创建 `.env.example` | 项目根目录 | 0.5h |
| 9 | CORS 配置收紧（生产环境禁止通配符） | `src/orcad_checker/web/app.py` | 1h |
| 10 | `discover_checkers()` 结果缓存 | `src/orcad_checker/engine/registry.py` | 1h |

### P2 -- 中期改进（提升可维护性）

| # | 行动项 | 涉及文件 | 预估工时 |
|---|--------|----------|----------|
| 11 | GUI 拆分为多个文件（check_tab/ai_tab/scripts_tab） | `tcl/gui/` | 4h |
| 12 | TCL 全局变量改为 namespace 封装 | `tcl/` 全局 | 8h |
| 13 | CI/CD 流水线（GitHub Actions: lint + test + build） | `.github/workflows/` | 4h |
| 14 | 知识库搜索从 SQL LIKE 升级为 FTS5 | `database.py` | 4h |
| 15 | 统一 TCL/Python 检查器规则定义（YAML 驱动） | 架构重构 | 16h |
| 16 | API 文档（OpenAPI 增强 + 使用示例） | `src/orcad_checker/web/routes/` | 4h |

### P3 -- 长期优化（提升用户体验）

| # | 行动项 | 涉及文件 | 预估工时 |
|---|--------|----------|----------|
| 17 | AI 流式响应（SSE） | `agent.py` + 前端 | 8h |
| 18 | LLM token 计量与成本监控 | `ai/` | 6h |
| 19 | 数据库迁移工具（alembic 或自建） | `store/` | 4h |
| 20 | 检查结果导出（PDF/Excel） | 新模块 | 8h |
| 21 | 完善 Vue 前端仪表盘 | `frontend/` | 20h |

---

## 10. 风险矩阵

| 风险 | 概率 | 影响 | 等级 | 缓解措施 |
|------|------|------|------|----------|
| TCL `dict get` Bug 导致检查器运行时崩溃 | 高 | 高 | **Critical** | 立即修复 P0-1 |
| 无认证 API 被未授权访问 | 中（内网低，公网高） | 高 | **High** | 添加 API Key 认证 |
| LLM API 密钥泄露 | 低 | 高 | **Medium** | 当前环境变量方案可接受，确保不写入镜像层 |
| 无日志导致生产问题难以排查 | 高 | 中 | **High** | P0-2 添加 logging |
| AI 会话无限增长消耗 token/存储 | 中 | 中 | **Medium** | 添加消息数量限制和定期清理 |
| OrCAD SWIG 绑定崩溃（segfault） | 低 | 高 | **Medium** | 已通过 CLAUDE.md 文档化危险 API，现有 catch 保护良好 |
| 单 SQLite 文件并发瓶颈 | 低（当前用户量） | 低 | **Low** | WAL 模式 + 连接池已缓解，用户量大时考虑 PostgreSQL |
| TCL/Python 检查器规则不同步 | 高 | 中 | **High** | P2-15 统一规则定义 |
| 前端框架不完整影响用户体验 | 中 | 中 | **Medium** | Tk GUI 作为主要入口可用，Vue 前端作为增强 |

---

## 附录: 代码验证摘要

以下为评审过程中实际阅读并验证的关键代码文件：

- `tcl/lib/orcad_api.tcl` (439 行) -- DBO 适配层，catch 保护全面，质量优秀
- `tcl/lib/checker_utils.tcl` (147 行) -- 缓存机制实现正确
- `tcl/engine/check_engine.tcl` (158 行) -- 结构清晰，优先级体系合理
- `tcl/engine/http_client.tcl` (127 行) -- 功能完整但缺重试
- `tcl/gui/main_window.tcl` (732 行) -- 功能完整但过大
- `tcl/checkers/check_decoupling_caps.tcl` (49 行) -- 检查器模板典范
- `tcl/checkers/check_i2c_pullups.tcl` (77 行) -- 确认第 55 行 Bug
- `src/orcad_checker/web/app.py` (53 行) -- CORS 配置需收紧
- `src/orcad_checker/web/routes/agent.py` (147 行) -- 错误处理不当
- `src/orcad_checker/web/routes/tcl_results.py` (91 行) -- Pydantic 验证完善
- `src/orcad_checker/web/routes/checks.py` (57 行) -- 缺 JSON 解析错误处理
- `src/orcad_checker/store/database.py` (489 行) -- SQL 参数化安全，连接池设计合理
- `src/orcad_checker/ai/tcl_agent.py` (212 行) -- 多轮对话实现正确
- `src/orcad_checker/ai/openai_client.py` (40 行) -- 简洁正确
- `src/orcad_checker/ai/anthropic_client.py` (33 行) -- 简洁正确
- `src/orcad_checker/engine/registry.py` (47 行) -- Registry Pattern 实现规范
- `src/orcad_checker/engine/runner.py` (83 行) -- 检查运行器逻辑清晰
- `Dockerfile` (59 行) -- 多阶段构建规范
- `docker-compose.yml` (31 行) -- 配置合理
- `pyproject.toml` (34 行) -- 依赖声明规范
- `.gitignore` -- 已排除 `.env` 和 `*.db`
