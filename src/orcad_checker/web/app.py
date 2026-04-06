import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from orcad_checker.store.database import Database
from orcad_checker.store.config import OracleConfig
from orcad_checker.web.routes import agent, checks, clients, knowledge, rules, scripts, summary, tcl_results

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="OrCAD Checker", version="0.2.0")

allowed_origins = [
    o.strip() for o in os.environ.get(
        "ALLOWED_ORIGINS", "http://localhost:8080,http://localhost:3000"
    ).split(",")
]

# Security: disallow credentials with wildcard origins
_allow_credentials = "*" not in allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
logger.info("CORS configured: origins=%s, credentials=%s", allowed_origins, _allow_credentials)


oracle_config = OracleConfig.from_yaml()
app.state.db = Database(oracle_config)

app.include_router(checks.router)
app.include_router(rules.router)
app.include_router(summary.router)
app.include_router(scripts.router)
app.include_router(knowledge.router)
app.include_router(clients.router)
app.include_router(agent.router)
app.include_router(tcl_results.router)

# AI chat page (standalone HTML, no build needed)
_static_dir = Path(__file__).parent / "static"


@app.get("/ai-chat")
async def ai_chat_page():
    return FileResponse(str(_static_dir / "ai_chat.html"))


# Serve Vue 2 frontend static files if built
frontend_dist = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
