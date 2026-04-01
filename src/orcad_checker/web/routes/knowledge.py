"""Knowledge base API — TCL API docs & examples management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from orcad_checker.models.scripts import KnowledgeDoc
from orcad_checker.store.database import Database
from orcad_checker.web.deps import get_db

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


class CreateDocRequest(BaseModel):
    title: str
    category: str = "api"  # api, example, guide
    content: str
    tags: list[str] = []


@router.get("")
async def list_docs(
    category: str | None = None,
    search: str | None = None,
    db: Database = Depends(get_db),
):
    return await run_in_threadpool(db.list_docs, category, search)


@router.post("", status_code=201)
async def create_doc(req: CreateDocRequest, db: Database = Depends(get_db)):
    doc = KnowledgeDoc(
        title=req.title, category=req.category,
        content=req.content, tags=req.tags,
    )
    return await run_in_threadpool(db.create_doc, doc)


@router.get("/{doc_id}")
async def get_doc(doc_id: str, db: Database = Depends(get_db)):
    doc = await run_in_threadpool(db.get_doc, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.put("/{doc_id}")
async def update_doc(doc_id: str, req: CreateDocRequest, db: Database = Depends(get_db)):
    doc = KnowledgeDoc(
        title=req.title, category=req.category,
        content=req.content, tags=req.tags,
    )
    result = await run_in_threadpool(db.update_doc, doc_id, doc)
    if not result:
        raise HTTPException(404, "Document not found")
    return result


@router.delete("/{doc_id}")
async def delete_doc(doc_id: str, db: Database = Depends(get_db)):
    deleted = await run_in_threadpool(db.delete_doc, doc_id)
    if not deleted:
        raise HTTPException(404, "Document not found")
    return {"status": "deleted"}


@router.get("/search/{query}")
async def search_docs(query: str, limit: int = 10, db: Database = Depends(get_db)):
    return await run_in_threadpool(db.search_knowledge, query, limit)
