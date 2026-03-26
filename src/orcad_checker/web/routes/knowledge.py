"""Knowledge base API — TCL API docs & examples management."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from orcad_checker.models.scripts import KnowledgeDoc
from orcad_checker.store.database import Database

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

_db = Database()


class CreateDocRequest(BaseModel):
    title: str
    category: str = "api"  # api, example, guide
    content: str
    tags: list[str] = []


@router.get("")
def list_docs(category: str | None = None, search: str | None = None):
    return _db.list_docs(category=category, search=search)


@router.post("", status_code=201)
def create_doc(req: CreateDocRequest):
    doc = KnowledgeDoc(
        title=req.title, category=req.category,
        content=req.content, tags=req.tags,
    )
    return _db.create_doc(doc)


@router.get("/{doc_id}")
def get_doc(doc_id: str):
    doc = _db.get_doc(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.put("/{doc_id}")
def update_doc(doc_id: str, req: CreateDocRequest):
    doc = KnowledgeDoc(
        title=req.title, category=req.category,
        content=req.content, tags=req.tags,
    )
    result = _db.update_doc(doc_id, doc)
    if not result:
        raise HTTPException(404, "Document not found")
    return result


@router.delete("/{doc_id}")
def delete_doc(doc_id: str):
    if not _db.delete_doc(doc_id):
        raise HTTPException(404, "Document not found")
    return {"status": "deleted"}


@router.get("/search/{query}")
def search_docs(query: str, limit: int = 10):
    return _db.search_knowledge(query, limit=limit)
