# OrCAD Checker Tool - 部署文档

## 目录

- [架构概览](#架构概览)
- [环境要求](#环境要求)
- [快速部署](#快速部署)
- [数据库配置](#数据库配置)
- [配置说明](#配置说明)
- [OrCAD 客户端配置](#orcad-客户端配置)
- [CLI 客户端使用](#cli-客户端使用)
- [运维管理](#运维管理)
- [生产环境部署](#生产环境部署)
- [常见问题](#常见问题)

---

## 架构概览

```
┌──────────────────────────────────────────────────────────┐
│                  Docker Container                        │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐                      │
│  │  FastAPI     │  │  Vue 2 前端   │                      │
│  │  REST API    │  │  (静态文件)   │                      │
│  └──────┬───────┘  └──────────────┘                      │
│         │  :8000                                         │
└─────────┼────────────────────────────────────────────────┘
          │
    ┌─────┴──────────────────────────┐
    │            网络访问              │
    ├──────────┬──────────┬──────────┤
    │          │          │          │
    ▼          ▼          ▼          ▼
 浏览器     OrCAD       CLI      Oracle DB
 (前端)    (Tk GUI)   (终端)   (内部数据库)
```

**数据库**: 使用内部 Oracle 数据库（10+），通过 `oracledb` Python 驱动连接，支持 10-20 用户并发。

---

## 环境要求

| 组件 | 最低版本 | 说明 |
|------|---------|------|
| Docker | 20.10+ | 容器运行时 |
| Docker Compose | 2.0+ | 容器编排 |
| Oracle Database | 10g+ | 已有 DBA 管理的实例 |
| 内存 | 512 MB | 容器最低需求 |
| 磁盘 | 200 MB | 镜像 + 日志 |

**Oracle 连接前提**:
- DBA 已创建用户/Schema
- 网络可达（容器能访问 Oracle 主机的 1521 端口）
- 拥有 JDBC 连接信息（host:port:SID 或 host:port/service_name）

---

## 快速部署

### 1. 克隆仓库

```bash
git clone https://github.com/Shangzheng98/orCadChecklistTool.git
cd orCadChecklistTool
```

### 2. 配置数据库连接

```bash
cp config/database.yaml.example config/database.yaml
```

编辑 `config/database.yaml`：

```yaml
oracle:
  jdbc_url: "jdbc:oracle:thin:@your-oracle-host:1521:YOUR_SID"
  user: "orcad_checker"
  password: "your_password"
  pool_min: 2      # 连接池最小连接数
  pool_max: 10     # 连接池最大连接数 (10-20 并发用户建议 10)
```

> **安全提示**: `config/database.yaml` 包含数据库密码，已加入 `.gitignore`，不会被提交到 Git。

### 3. 配置 AI 提供者

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```ini
# 方式 A: 使用 Anthropic Claude（外网）
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# 方式 B: 使用内网 OpenAI 兼容模型
# AI_PROVIDER=openai_compatible
# OPENAI_BASE_URL=http://192.168.1.100:8000/v1
# OPENAI_API_KEY=your-internal-key
# OPENAI_MODEL=your-model-name
```

### 4. 一键启动

```bash
docker compose up -d
```

### 5. 验证

```bash
# 检查容器状态
docker compose ps

# 检查日志（确认 Oracle 连接成功）
docker compose logs orcad-checker

# 测试 API
curl http://localhost:8000/api/v1/checkers
```

浏览器访问: **http://your-server-ip:8000**

---

## 数据库配置

### 配置文件

数据库连接通过 YAML 配置文件管理，**不使用环境变量**。

| 文件 | 说明 |
|------|------|
| `config/database.yaml.example` | 配置模板（提交到 Git） |
| `config/database.yaml` | 实际配置（含密码，不提交到 Git） |

### JDBC URL 格式

支持两种连接格式：

```yaml
# 格式 1: SID
jdbc_url: "jdbc:oracle:thin:@192.168.1.100:1521:ORCL"

# 格式 2: Service Name
jdbc_url: "jdbc:oracle:thin:@192.168.1.100:1521/orcl_service"
```

### 连接池参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `pool_min` | 2 | 连接池最小连接数（空闲时保持的连接） |
| `pool_max` | 10 | 连接池最大连接数（并发高峰时的上限） |

**并发用户数与连接池大小的关系**:
- 10 用户: `pool_min: 2, pool_max: 5`
- 20 用户: `pool_min: 2, pool_max: 10`
- 连接池获取超时: 5 秒（超时返回 503）

### 表结构

首次启动时自动创建以下 6 张表（如果已存在则跳过）：

| 表名 | 用途 |
|------|------|
| `scripts` | TCL 脚本元数据和代码 |
| `script_versions` | 脚本版本历史 |
| `knowledge_docs` | 知识库文档 |
| `clients` | OrCAD 客户端注册信息 |
| `sessions` | AI 对话会话 |
| `tcl_check_results` | TCL 检查结果上传记录 |

**数据类型映射**:
- 短文本字段 → `VARCHAR2(N)`
- 长文本字段（代码、内容、JSON） → `CLOB`
- 自增 ID → `NUMBER GENERATED ALWAYS AS IDENTITY`

### 手动建表（可选）

如果 DBA 不允许应用自动建表，可提前执行 DDL：

```sql
-- 示例：scripts 表
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

-- 完整 DDL 参见源码: src/orcad_checker/store/database.py
```

---

## 配置说明

### 环境变量（AI 相关）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | `8000` | 服务端口 |
| `AI_PROVIDER` | `anthropic` | AI 提供者: `anthropic` 或 `openai_compatible` |
| `ANTHROPIC_API_KEY` | - | Anthropic API Key |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Claude 模型 |
| `OPENAI_BASE_URL` | - | 内网模型地址（OpenAI 兼容） |
| `OPENAI_API_KEY` | - | 内网模型 Key |
| `OPENAI_MODEL` | - | 内网模型名称 |

### 文件挂载（Docker）

| 宿主机路径 | 容器路径 | 说明 |
|-----------|----------|------|
| `./config` | `/app/config` | 数据库配置文件（必需） |
| `./rules` | `/app/rules` | YAML 规则配置（支持热更新） |

### 修改端口

```bash
PORT=9000 docker compose up -d
```

---

## OrCAD 客户端配置

### 第一次使用

1. 将 `tcl/` 目录整体复制到每台 OrCAD 工作站（任意路径）：

```
C:\OrCAD_Checker\
├── orcad_checker.tcl      <- 主入口
├── engine\
├── checkers\
└── gui\
```

2. 在 OrCAD Capture 的 TCL 控制台设置服务器地址并加载：

```tcl
set ::server_url "http://192.168.1.50:8000"
source "C:/OrCAD_Checker/orcad_checker.tcl"
```

弹出工具窗口，包含三个 Tab：
- **Design Check** -- 直接在 OrCAD 内执行检查
- **AI Assistant** -- 跟 AI 对话生成 TCL 脚本，自动安全检查，可直接执行
- **Scripts** -- 浏览/安装服务器上的脚本

### 自动加载（推荐）

让 OrCAD 启动时自动加载工具：

```
复制到: %CDS_ROOT%\tools\capture\tclscripts\capAutoLoad\orcad_checker_init.tcl
```

`orcad_checker_init.tcl` 内容：

```tcl
set ::server_url "http://192.168.1.50:8000"
source "C:/OrCAD_Checker/orcad_checker.tcl"
```

### 团队批量部署

1. 将 `tcl/` 放到共享网络路径：`\\fileserver\tools\orcad_checker\`
2. 每台机器的 `capAutoLoad` 下放一个加载脚本：

```tcl
set ::server_url "http://192.168.1.50:8000"
source "//fileserver/tools/orcad_checker/orcad_checker.tcl"
```

脚本更新时只需更新共享目录，所有客户端重启 OrCAD 即生效。

---

## CLI 客户端使用

### 安装

```bash
pip install -e .
```

### 常用命令

```bash
# -- 设计检查（Python 侧，用于 CI/CD）--
orcad-check run design_export.json
orcad-check run design_export.json --json    # JSON 输出

# -- 启动服务器（开发模式）--
orcad-check serve --port 8000

# -- 脚本管理 --
orcad-check scripts list                     # 查看本地脚本
orcad-check scripts install <script_id>      # 从服务器安装
orcad-check scripts push my.tcl --name "BOM导出"  # 推送到服务器
orcad-check scripts deploy <script_id>       # 部署到 OrCAD

# -- OTA 更新 --
orcad-check ota register                     # 注册客户端
orcad-check ota check                        # 检查更新
orcad-check ota update                       # 拉取所有更新
```

---

## 运维管理

### 日志查看

```bash
# 实时日志
docker compose logs -f orcad-checker

# 最近 100 行
docker compose logs --tail 100 orcad-checker

# 筛选数据库相关日志
docker compose logs orcad-checker | grep -i "oracle\|table\|connect"
```

### 更新部署

```bash
git pull
docker compose build --no-cache
docker compose up -d
```

### 数据库维护

数据存储在 Oracle 中，由 DBA 统一管理备份和恢复。

```bash
# 查看已注册客户端
curl http://localhost:8000/api/v1/clients

# 查看 OrCAD 上报的检查历史
curl http://localhost:8000/api/v1/check-results/history

# 查看知识库文档
curl http://localhost:8000/api/v1/knowledge
```

### 连接池监控

应用日志中会记录连接池状态。如果频繁出现 `DPY-4011: the connection pool has timed out` 错误，说明并发超过 `pool_max`，需要调大配置：

```yaml
oracle:
  pool_max: 20    # 增大最大连接数
```

---

## 生产环境部署

### 使用 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name orcad-checker.yourcompany.com;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }
}
```

### docker-compose.prod.yml

```yaml
version: "3.8"

services:
  orcad-checker:
    build: .
    container_name: orcad-checker-server
    ports:
      - "127.0.0.1:8000:8000"  # 只监听 localhost，由 Nginx 代理
    volumes:
      - ./config:/app/config:ro      # 数据库配置（只读）
      - ./rules:/app/rules           # 规则配置（支持热更新）
    env_file:
      - .env
    restart: always
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 256M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - orcad-checker
    restart: always
```

启动：

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 内网无外网环境

如果服务器无法访问外网：

1. 在有网络的机器上构建镜像：

```bash
docker compose build
docker save orcad-checker-server > orcad-checker.tar
```

2. 传输到内网服务器：

```bash
docker load < orcad-checker.tar
docker compose up -d
```

3. AI 配置使用内网模型：

```ini
AI_PROVIDER=openai_compatible
OPENAI_BASE_URL=http://内网模型地址:8000/v1
OPENAI_API_KEY=your-key
OPENAI_MODEL=your-model
```

---

## 常见问题

### Q: 容器启动失败

```bash
docker compose logs orcad-checker
```

常见原因：
- 端口被占用 -> 修改 `PORT` 环境变量
- Oracle 连接失败 -> 检查 `config/database.yaml` 中的连接信息
- 镜像构建失败 -> 检查网络

### Q: Oracle 连接失败

1. 确认 Oracle 主机可达：

```bash
# 从容器内测试
docker compose exec orcad-checker python3 -c "
import oracledb
conn = oracledb.connect(user='your_user', password='your_pass', dsn='host:1521/service')
print('Connected:', conn.version)
conn.close()
"
```

2. 常见错误：
   - `DPY-6005: cannot connect to database` -> 检查 host/port 是否可达
   - `ORA-01017: invalid username/password` -> 检查用户名密码
   - `ORA-12514: TNS:listener does not know of service` -> 检查 SID/Service Name

3. 确认容器能访问 Oracle 网络（可能需要 `docker-compose.yml` 配置 `network_mode: host`）

### Q: 数据库连接池耗尽

日志中出现 `DPY-4011` 超时错误：

```bash
# 检查当前配置
cat config/database.yaml

# 增大连接池
# pool_max: 15 或 20
```

修改后重启容器：`docker compose restart`

### Q: OrCAD 连不上服务器

1. 确认服务器防火墙开放了端口（默认 8000）
2. 在 OrCAD TCL 控制台测试：

```tcl
package require http
set token [http::geturl "http://192.168.1.50:8000/api/v1/checkers" -timeout 5000]
puts [http::data $token]
http::cleanup $token
```

3. 确认 `::server_url` 设置正确

### Q: AI 功能不可用

- 检查 `.env` 中 API Key 是否配置
- 内网模型需确认 `OPENAI_BASE_URL` 可达
- 查看日志：`docker compose logs orcad-checker | grep -i error`

### Q: 如何初始化知识库

首次启动时，访问前端 Knowledge Base 页面手动添加，或通过 API：

```bash
curl -X POST http://localhost:8000/api/v1/knowledge \
  -H "Content-Type: application/json" \
  -d '{"title":"GetParts API","category":"api","content":"...","tags":["parts"]}'
```

项目自带 `data/seed_knowledge.json`，包含 7 篇 TCL API 参考文档。

### Q: config/database.yaml 不小心提交了怎么办

```bash
# 从 Git 历史中移除（保留本地文件）
git rm --cached config/database.yaml
git commit -m "chore: remove database config from tracking"

# 确认 .gitignore 包含 config/database.yaml
grep "database.yaml" .gitignore
```
