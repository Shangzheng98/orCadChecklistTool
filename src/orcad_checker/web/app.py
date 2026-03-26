from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from orcad_checker.web.routes import agent, checks, clients, knowledge, rules, scripts, summary

app = FastAPI(title="OrCAD Checker", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(checks.router)
app.include_router(rules.router)
app.include_router(summary.router)
app.include_router(scripts.router)
app.include_router(knowledge.router)
app.include_router(clients.router)
app.include_router(agent.router)

# Serve Vue 2 frontend static files if built
frontend_dist = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
