"""FastAPI REST API for SourceMap. Install the api extra to run it."""

from __future__ import annotations

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import calendar
import hashlib
import json
import secrets
import threading
import time
import urllib.parse
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

try:
    from fastapi import Depends, FastAPI, Header, HTTPException, Request
    from fastapi.responses import RedirectResponse
    from pydantic import BaseModel, Field
except ImportError as exc:
    raise RuntimeError("Install SourceMap API dependencies with: pip install -e .[api]") from exc

from . import github, indexing
from .config import settings
from .db import Store
from .graph import answer_query
from .security import issue_token, token_estimate, verify_token

app = FastAPI(title="SourceMap API", version="0.2.0", description="Semantic codebase search API. Website is out of scope.")
store = Store(str(Path(settings.data_dir) / "sourcemap.db"))
oauth_states: dict[str, tuple[str, float]] = {}
rate_events: dict[str, deque[float]] = defaultdict(deque)
rate_lock = threading.Lock()
MAX_REQUESTS_PER_MINUTE = 60


class ConnectRepo(BaseModel):
    full_name: str = Field(min_length=3, max_length=200, pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    clone_url: str | None = None
    private: bool = False


class QueryRequest(BaseModel):
    repo_id: str
    query: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=15)
    conversation_id: str | None = None


def _rate_limit(subject: str):
    now = time.monotonic()
    with rate_lock:
        events = rate_events[subject]
        while events and now - events[0] > 60:
            events.popleft()
        if len(events) >= MAX_REQUESTS_PER_MINUTE:
            raise HTTPException(429, "Rate limit exceeded; retry shortly")
        events.append(now)


def current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Bearer token required")
    try:
        return verify_token(authorization.split(" ", 1)[1], settings.jwt_secret)
    except ValueError as exc:
        raise HTTPException(401, str(exc)) from exc


@app.get("/health")
def health():
    return {"status": "ok", "service": "sourcemap-api", "version": app.version}


@app.get("/auth/github")
def github_login():
    try:
        url, state = github.authorization_url(settings.github_client_id, settings.github_callback_url)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    oauth_states[state] = ("", time.time() + 600)
    return RedirectResponse(url)


@app.get("/auth/github/callback")
def github_callback(code: str, state: str):
    saved = oauth_states.pop(state, None)
    if not saved or saved[1] < time.time():
        raise HTTPException(400, "Invalid or expired OAuth state")
    try:
        token_result = github.exchange_code(settings.github_client_id, settings.github_client_secret, code)
        access_token = token_result.get("access_token")
        if not access_token:
            raise ValueError("GitHub did not return an access token")
        profile = github.github_user(access_token)
        subject = str(profile["id"])
        store.upsert_user(subject, profile["login"])
        jwt = issue_token(subject, settings.jwt_secret, settings.jwt_ttl_seconds)
        return {"access_token": jwt, "token_type": "bearer", "expires_in": settings.jwt_ttl_seconds, "github_login": profile["login"]}
    except (ValueError, KeyError, OSError) as exc:
        raise HTTPException(502, f"GitHub authentication failed: {exc}") from exc


@app.post("/auth/dev-token")
def dev_token():
    """Local development only. Disabled unless SOURCEMAP_DEV_AUTH=1."""
    import os
    if os.getenv("SOURCEMAP_DEV_AUTH") != "1":
        raise HTTPException(404, "Not found")
    if not settings.jwt_secret:
        raise HTTPException(503, "Configure SOURCEMAP_JWT_SECRET")
    store.upsert_user("local-dev", "local-dev")
    return {"access_token": issue_token("local-dev", settings.jwt_secret, settings.jwt_ttl_seconds), "token_type": "bearer"}


@app.post("/repos/connect")
def connect_repo(body: ConnectRepo, user: dict = Depends(current_user)):
    _rate_limit(user["sub"])
    full_name = body.full_name
    clone_url = body.clone_url or f"https://github.com/{full_name}.git"
    if not clone_url.startswith("https://github.com/"):
        raise HTTPException(400, "Only GitHub HTTPS clone URLs are supported")
    if body.private and not settings.github_token:
        raise HTTPException(400, "Private repository cloning needs an authorized GitHub token")
    repo_id = hashlib.sha256(f"{user['sub']}:{full_name}".encode()).hexdigest()[:24]
    store.connect_repo(repo_id, user["sub"], full_name, clone_url, body.private)
    return {"id": repo_id, "full_name": full_name, "private": body.private, "status": "connected"}


@app.get("/repos")
def list_repos(user: dict = Depends(current_user)):
    _rate_limit(user["sub"])
    return {"repositories": store.list_repos(user["sub"])}


def _repo_chunks(repo: dict) -> list[dict]:
    root = Path(settings.data_dir) / "repos" / repo["id"]
    index_file = Path(settings.data_dir) / "indexes" / f"{repo['id']}.json"
    if not index_file.exists():
        raise HTTPException(409, "Repository is connected but not indexed; trigger reindex")
    try:
        return json.loads(index_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(500, f"Could not load repository index: {exc}") from exc


@app.post("/query")
def query_repo(body: QueryRequest, user: dict = Depends(current_user)):
    _rate_limit(user["sub"])
    repo = store.get_repo(body.repo_id, user["sub"])
    if not repo:
        raise HTTPException(404, "Repository not found")
    chunks = _repo_chunks(repo)
    response = answer_query(body.query, chunks, body.top_k)
    now = datetime.now(timezone.utc)
    month = f"{now.year:04d}-{now.month:02d}"
    used = token_estimate(body.query + response["answer"] + "".join(s["code_snippet"] for s in response["sources"]))
    monthly_total = store.add_usage(user["sub"], month, used)
    if monthly_total > settings.free_monthly_tokens:
        raise HTTPException(429, "Monthly free-tier token allowance exceeded")
    query_id = secrets.token_urlsafe(12)
    response.update({"id": query_id, "tokens_used": used, "monthly_tokens_used": monthly_total})
    store.save_query(query_id, user["sub"], body.repo_id, body.query, response, used)
    return response


@app.get("/query/{query_id}")
def get_query(query_id: str, user: dict = Depends(current_user)):
    result = store.get_query(query_id, user["sub"])
    if not result:
        raise HTTPException(404, "Query not found")
    return result


@app.post("/repos/{repo_id}/reindex", status_code=202)
def reindex_repo(repo_id: str, user: dict = Depends(current_user)):
    _rate_limit(user["sub"])
    repo = store.get_repo(repo_id, user["sub"])
    if not repo:
        raise HTTPException(404, "Repository not found")
    # Local prototype runs the job inline. Celery worker integration is a documented extension point.
    destination = Path(settings.data_dir) / "repos" / repo_id
    try:
        root = indexing.clone_repository(repo["clone_url"], destination, settings.github_token or None)
        chunks = indexing.chunk_repository(root, repo_id)
        if settings.openai_api_key:
            chunks = indexing.embed_chunks(chunks, settings.openai_api_key, settings.openai_embedding_model)
        index_file = Path(settings.data_dir) / "indexes" / f"{repo_id}.json"
        index_file.parent.mkdir(parents=True, exist_ok=True)
        temp = index_file.with_suffix(".tmp")
        temp.write_text(json.dumps([c.to_dict() for c in chunks]), encoding="utf-8")
        temp.replace(index_file)
        return {"repo_id": repo_id, "status": "indexed", "files": len({c.file_path for c in chunks}), "chunks": len(chunks), "revision": chunks[0].revision if chunks else "empty"}
    except Exception as exc:
        raise HTTPException(502, f"Indexing failed: {exc}") from exc


@app.delete("/repos/{repo_id}", status_code=204)
def delete_repo(repo_id: str, user: dict = Depends(current_user)):
    repo = store.get_repo(repo_id, user["sub"])
    if not repo:
        raise HTTPException(404, "Repository not found")
    store.delete_repo(repo_id, user["sub"])
    import shutil
    shutil.rmtree(Path(settings.data_dir) / "repos" / repo_id, ignore_errors=True)
    (Path(settings.data_dir) / "indexes" / f"{repo_id}.json").unlink(missing_ok=True)
    return None
