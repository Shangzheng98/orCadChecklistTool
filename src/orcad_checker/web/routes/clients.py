"""Client management API — registration, sync tracking."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from orcad_checker.models.scripts import ClientInfo
from orcad_checker.store.database import Database
from orcad_checker.web.deps import get_db

router = APIRouter(prefix="/api/v1/clients", tags=["clients"])


@router.post("/register")
async def register_client(info: ClientInfo, db: Database = Depends(get_db)):
    return await run_in_threadpool(db.register_client, info)


@router.get("")
async def list_clients(db: Database = Depends(get_db)):
    return await run_in_threadpool(db.list_clients)


@router.get("/{client_id}")
async def get_client(client_id: str, db: Database = Depends(get_db)):
    client = await run_in_threadpool(db.get_client, client_id)
    if not client:
        raise HTTPException(404, "Client not found")
    return client
