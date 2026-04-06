# OrCAD Checker

OrCAD Capture 原理图设计规则检查与 TCL 脚本自动化平台。支持可配置的规则检查、AI 辅助 TCL 脚本生成、脚本市场与 OTA 分发。

## 架构概览

三层架构：

```
[Vue 2 前端] ──HTTP──▶ [FastAPI 后端] ◀──HTTP── [OrCAD TCL 客户端]
                              │
                    ┌─────────┴─────────┐
               [Oracle DB]        [LLM Provider]
              (内部数据库)       (Anthropic / OpenAI)
```

- **后端**：Python 3.10+，FastAPI，Oracle 10+（oracledb 驱动）
- **前端**：Vue 2 + Element UI，4 个功能 Tab
- **TCL 客户端**：运行在 OrCAD Capture 内，内嵌 Tk GUI，直接调用 OrCAD TCL API

## 功能

### 设计规则检查（DRC）

7 个内置检查器，均可通过 `rules/default_rules.yaml` 启用/禁用和配置参数：

| 检查器 | 严重级别 | 说明 |
|--------|----------|------|
| `duplicate_refdes` | ERROR | 重复位号 |
| `footprint_validation` | ERROR | 缺少封装 |
| `missing_attributes` | WARNING | 缺少必要属性（默认：footprint / value / part_number） |
| `unconnected_pins` | WARNING | 未连接的管脚（自动跳过 NC/N/C/DNC） |
| `power_net_naming` | WARNING | 电源网络命名不符合规范 |
| `single_pin_nets` | WARNING | 单引脚网络（通常是连线错误） |
| `net_naming` | INFO | 自动生成的网络名未重命名 |

### AI 辅助

- **TCL 脚本生成**：通过自然语言对话生成 TCL 脚本，自动注入知识库上下文
- **脚本安全检查**：自动检测生成脚本中的崩溃 API、语法隐患和模板合规性（详见下方 TCL Linter）
- **检查结果摘要**：AI 对 DRC 报告进行优先级排序、原因分析和修复建议
- **知识库**：存储 OrCAD TCL API 文档与示例，作为 AI 上下文

### 脚本市场

- 创建、版本管理、发布 TCL 脚本
- OTA 分发：客户端通过 manifest + download 接口自动同步已发布脚本
- 分类/状态/全文检索过滤

## 快速开始

### Docker（推荐）

```bash
# 1. 配置数据库连接
cp config/database.yaml.example config/database.yaml
# 编辑 config/database.yaml 填入 Oracle 连接信息

# 2. 配置 AI Key
cp .env.example .env
# 编辑 .env 填入 API Key

# 3. 启动
docker compose up -d
```

访问 `http://localhost:8000`。

### 本地开发

**后端：**

```bash
pip install -e ".[dev]"
cp config/database.yaml.example config/database.yaml
# 编辑 config/database.yaml 填入 Oracle 连接信息
orcad-check serve
```

**前端（开发模式，API 代理到 :8000）：**

```bash
cd frontend
npm install
npm run serve
```

## 配置

### 数据库配置（config/database.yaml）

```yaml
oracle:
  jdbc_url: "jdbc:oracle:thin:@your-host:1521:SID"
  user: "orcad_checker"
  password: "your_password"
  pool_min: 2
  pool_max: 10
```

> `config/database.yaml` 含密码，已加入 `.gitignore`。模板见 `config/database.yaml.example`。

### 环境变量（AI 相关）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AI_PROVIDER` | `anthropic` | `anthropic` 或 `openai_compatible` |
| `ANTHROPIC_API_KEY` | — | Anthropic API Key |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | 模型 ID |
| `OPENAI_BASE_URL` | — | OpenAI 兼容接口地址 |
| `OPENAI_API_KEY` | — | OpenAI API Key |
| `OPENAI_MODEL` | — | 模型 ID |
| `PORT` | `8000` | 服务端口 |

## OrCAD TCL 客户端

在 OrCAD Capture 的 TCL 控制台中加载：

```tcl
source "path/to/tcl/orcad_checker.tcl"
orcad_checker_gui
```

弹出 Tk GUI，包含三个 Tab：
- **Design Check**：选择检查项，运行，上传结果到服务器
- **AI Assistant**：对话生成 TCL 脚本，可直接在 OrCAD 中执行
- **Script Manager**：浏览服务器脚本，安装/OTA 更新

### OTA 脚本更新（CLI）

```bash
orcad-check ota register          # 注册客户端
orcad-check ota check             # 检查可用更新
orcad-check ota update            # 拉取所有更新
orcad-check scripts deploy <id>   # 部署到 OrCAD autoload 目录
```

## CLI 命令

```bash
orcad-check run design.json --rules rules/default_rules.yaml --json
orcad-check list
orcad-check serve --host 0.0.0.0 --port 8000
orcad-check scripts list
orcad-check scripts push file.tcl --name "My Script"
```

## API

所有接口前缀 `/api/v1`。主要端点：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/checkers` | 列出所有检查器 |
| `POST` | `/check` | 上传设计 JSON，执行检查 |
| `GET/PUT` | `/rules` | 读取/更新规则配置 |
| `POST` | `/summarize` | AI 生成检查摘要 |
| `GET/POST` | `/scripts` | 脚本列表 / 创建 |
| `GET` | `/scripts/ota/manifest` | OTA 清单 |
| `POST` | `/agent/chat` | AI 对话（含自动 lint 检查） |
| `POST` | `/clients/register` | 客户端注册 |

完整文档见 `docs/architecture.md` 和 `docs/features.md`，或访问 `/docs`（Swagger UI）。

## 项目结构

```
src/orcad_checker/           # Python 后端
  linter/                    # TCL 脚本安全检查器（Linter）
frontend/                    # Vue 2 前端
tcl/                         # TCL 客户端（OrCAD 内运行）
config/                      # 配置文件
  database.yaml.example      # Oracle 数据库连接配置模板
rules/                       # 规则配置 YAML
  default_rules.yaml         # DRC 检查器规则
  tcl_safety_rules.yaml      # TCL 安全规则（崩溃 API / 语法 / 约定）
data/                        # 知识库种子数据
schemas/                     # JSON Schema
docs/                        # 详细文档
tests/
  fixtures/
    golden_test_design.json  # 黄金测试设计（回归测试用）
```

## 开发

```bash
pip install -e ".[dev]"
pytest
```
