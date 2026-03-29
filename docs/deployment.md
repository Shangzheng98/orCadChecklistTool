# OrCAD Checker Tool - Docker 部署文档

## 目录

- [架构概览](#架构概览)
- [环境要求](#环境要求)
- [快速部署](#快速部署)
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
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  FastAPI     │  │  Vue 2 前端   │  │  SQLite DB     │  │
│  │  REST API    │  │  (静态文件)   │  │  (Volume 持久化)│  │
│  └──────┬───────┘  └──────────────┘  └────────────────┘  │
│         │  :8000                                         │
└─────────┼────────────────────────────────────────────────┘
          │
    ┌─────┴──────────────────────────┐
    │            网络访问              │
    ├──────────┬──────────┬──────────┤
    │          │          │          │
    ▼          ▼          ▼          ▼
 浏览器     OrCAD       CLI       其他服务
 (前端)    (Tk GUI)   (终端)    (CI/CD等)
```

## 环境要求

| 组件 | 最低版本 |
|------|---------|
| Docker | 20.10+ |
| Docker Compose | 2.0+ |
| 内存 | 512 MB |
| 磁盘 | 200 MB |

## 快速部署

### 1. 克隆仓库

```bash
git clone https://github.com/Shangzheng98/orCadChecklistTool.git
cd orCadChecklistTool
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```ini
# ── 选择 AI 提供者 ──────────────────────────

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

### 3. 一键启动

```bash
docker compose up -d
```

### 4. 验证

```bash
# 检查容器状态
docker compose ps

# 检查健康状态
docker compose logs orcad-checker

# 测试 API
curl http://localhost:8000/api/v1/checkers
```

浏览器访问: **http://your-server-ip:8000**

---

## 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | `8000` | 服务端口 |
| `AI_PROVIDER` | `anthropic` | AI 提供者: `anthropic` 或 `openai_compatible` |
| `ANTHROPIC_API_KEY` | - | Anthropic API Key |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Claude 模型 |
| `OPENAI_BASE_URL` | - | 内网模型地址（OpenAI 兼容） |
| `OPENAI_API_KEY` | - | 内网模型 Key |
| `OPENAI_MODEL` | - | 内网模型名称 |

### 数据持久化

| 路径 | 说明 |
|------|------|
| `orcad-data` volume → `/app/data` | SQLite 数据库（脚本仓库、知识库、客户端信息） |
| `./rules` → `/app/rules` | YAML 规则配置（挂载到宿主机，支持热更新） |

### 修改端口

```bash
# .env 或命令行
PORT=9000 docker compose up -d
```

---

## OrCAD 客户端配置

### 第一次使用

1. 将 `tcl/` 目录整体复制到每台 OrCAD 工作站（任意路径）：

```
C:\OrCAD_Checker\
├── orcad_checker.tcl      ← 主入口
├── engine\
├── checkers\
└── gui\
```

2. 在 OrCAD Capture 的 TCL 控制台设置服务器地址并加载：

```tcl
set ::server_url "http://192.168.1.50:8000"
source "C:/OrCAD_Checker/orcad_checker.tcl"
```

这将弹出一个包含三个 Tab 的工具窗口：
- **Design Check** — 直接在 OrCAD 内执行检查
- **AI Assistant** — 跟 AI 对话生成 TCL 脚本，可直接执行
- **Scripts** — 浏览/安装服务器上的脚本

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
# ── 设计检查（Python 侧，用于 CI/CD）──
orcad-check run design_export.json
orcad-check run design_export.json --json    # JSON 输出

# ── 启动服务器（开发模式）──
orcad-check serve --port 8000

# ── 脚本管理 ──
orcad-check scripts list                     # 查看本地脚本
orcad-check scripts install <script_id>      # 从服务器安装
orcad-check scripts push my.tcl --name "BOM导出"  # 推送到服务器
orcad-check scripts deploy <script_id>       # 部署到 OrCAD

# ── OTA 更新 ──
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
```

### 更新部署

```bash
git pull
docker compose build --no-cache
docker compose up -d
```

### 备份数据库

```bash
# 备份 SQLite DB
docker compose exec orcad-checker cp /app/data/orcad_checker.db /app/data/backup_$(date +%Y%m%d).db

# 或从宿主机备份 volume
docker cp orcad-checker-server:/app/data/orcad_checker.db ./backup.db
```

### 恢复数据库

```bash
docker cp ./backup.db orcad-checker-server:/app/data/orcad_checker.db
docker compose restart
```

### 查看已注册客户端

```bash
curl http://localhost:8000/api/v1/clients
```

### 查看 OrCAD 上报的检查历史

```bash
curl http://localhost:8000/api/v1/check-results/history
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
      - orcad-data:/app/data
      - ./rules:/app/rules
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

volumes:
  orcad-data:
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
- 端口被占用 → 修改 `PORT` 环境变量
- 镜像构建失败 → 检查网络，国内用户默认使用清华/淘宝镜像源

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

### Q: 数据库损坏怎么办

```bash
# 停止服务
docker compose down

# 删除旧数据库（会丢失数据，请先备份）
docker volume rm orcadchecklisttool_orcad-data

# 重新启动（自动创建新数据库）
docker compose up -d
```
