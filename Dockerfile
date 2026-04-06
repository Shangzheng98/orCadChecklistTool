# ============== Build Stage: Frontend ==============
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --registry https://registry.npmmirror.com
COPY frontend/ ./
RUN npm run build

# ============== Build Stage: Backend ==============
FROM python:3.11-slim AS backend-builder

WORKDIR /app
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir . -i https://pypi.tuna.tsinghua.edu.cn/simple

# ============== Runtime ==============
FROM python:3.11-slim

LABEL maintainer="OrCAD Checker Team"
LABEL description="OrCAD Capture Schematic Checklist Tool - Server"

WORKDIR /app

# Install dependencies (includes oracledb)
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir . -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && rm -rf /root/.cache/pip

# Copy project files
COPY rules/ ./rules/
COPY schemas/ ./schemas/
COPY data/seed_knowledge.json ./data/seed_knowledge.json
COPY tcl/ ./tcl/

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Config directory (database.yaml mounted at runtime)
RUN mkdir -p /app/config

# Environment defaults (AI only, database config via YAML file)
ENV AI_PROVIDER=anthropic \
    ANTHROPIC_API_KEY="" \
    ANTHROPIC_MODEL="claude-sonnet-4-20250514" \
    OPENAI_BASE_URL="" \
    OPENAI_API_KEY="" \
    OPENAI_MODEL="" \
    HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/checkers').raise_for_status()"

CMD ["sh", "-c", "uvicorn orcad_checker.web.app:app --host ${HOST} --port ${PORT}"]
