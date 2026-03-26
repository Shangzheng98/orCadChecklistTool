"""Client management API — registration, sync tracking."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from orcad_checker.models.scripts import ClientInfo
from orcad_checker.store.database import Database

router = APIRouter(prefix="/api/v1/clients", tags=["clients"])

_db = Database()


@router.post("/register")
def register_client(info: ClientInfo):
    return _db.register_client(info)


@router.get("")
def list_clients():
    return _db.list_clients()


@router.get("/{client_id}")
def get_client(client_id: str):
    client = _db.get_client(client_id)
    if not client:
        raise HTTPException(404, "Client not found")
    return client
