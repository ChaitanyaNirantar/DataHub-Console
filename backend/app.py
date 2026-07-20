"""
DataHub Console — single service exposing:
  - the dataset catalog + query API (from the ingestion pipeline)
  - the natural-language query agent API
  - the static frontend

Run with:  uvicorn app:app --reload --port 8000
Then open http://127.0.0.1:8000
"""

import json
import logging
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import os as _os

from db import init_db, query_repos, row_count, distinct_languages

# LLM_PROVIDER=gemini (default, free) or claude
LLM_PROVIDER = _os.environ.get("LLM_PROVIDER", "gemini").lower()
if LLM_PROVIDER == "claude":
    from agent import QueryAgent
else:
    from agent_gemini import QueryAgent

logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).parent.parent
CATALOG_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="DataHub Console API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_agent = None


def get_agent() -> QueryAgent:
    """Constructed on first use, not at import time, so the rest of the
    app (catalog, browse) still works even if no API key is configured yet."""
    global _agent
    if _agent is None:
        _agent = QueryAgent()
    return _agent


class RepoOut(BaseModel):
    repo_id: int
    full_name: str
    description: Optional[str] = None
    language: Optional[str] = None
    stars: int
    forks: int
    open_issues: int
    created_at: str
    pushed_at: str
    license: Optional[str] = None
    url: str


class AskRequest(BaseModel):
    question: str


@app.on_event("startup")
def startup():
    init_db()


# ---------- Catalog + dataset API ----------

@app.get("/api/health")
def health():
    return {"status": "ok", "total_rows": row_count()}


@app.get("/api/datasets")
def list_datasets():
    catalogs = sorted(CATALOG_DIR.glob("*_catalog.json"))
    return [c.stem.replace("_catalog", "") for c in catalogs]


@app.get("/api/datasets/{name}/catalog")
def get_catalog(name: str):
    path = CATALOG_DIR / f"{name}_catalog.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No catalog entry for dataset '{name}'")
    return json.loads(path.read_text())


@app.get("/api/datasets/github_repos/languages")
def get_languages():
    return distinct_languages()


@app.get("/api/datasets/github_repos/query", response_model=List[RepoOut])
def query_github_repos(
    language: Optional[str] = Query(None),
    min_stars: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
):
    return query_repos(language=language, min_stars=min_stars, limit=limit)


# ---------- NL query agent API ----------

@app.post("/api/ask")
def ask(req: AskRequest):
    try:
        return get_agent().ask(req.question)
    except RuntimeError as e:
        # e.g. missing API key — surfaced to the frontend as a clear message
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Frontend ----------

app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
