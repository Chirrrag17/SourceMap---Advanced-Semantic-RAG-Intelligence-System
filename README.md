# SourceMap backend

SourceMap is an AI-assisted codebase search backend concept. This repository contains a runnable local prototype plus optional integration points for GitHub OAuth, FastAPI, embeddings, Pinecone, LangGraph, and Redis. Website and frontend work are outside this repository's scope.

## What works locally

- Indexes common code and documentation files into line-addressable chunks.
- Ranks search results using lexical relevance and symbol/path context.
- Returns source paths, line ranges, snippets, and a confidence indicator.
- Provides a FastAPI service when the `api` extra is installed.
- Persists local users, repositories, query history, and monthly usage in SQLite.
- Supports signed bearer tokens, per-user repository checks, request throttling, and data deletion.

## Quick start

Python 3.10+ is required. Install API dependencies, configure a development signing secret, then run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[api,dev]"
Copy-Item .env.example .env
# Set SOURCEMAP_JWT_SECRET to a long random value in .env
uvicorn sourcemap.api:app --reload
```

Open `http://127.0.0.1:8000/docs` for the generated OpenAPI page and `http://127.0.0.1:8000/health` for the health endpoint.

For a local no-server search demo:

```powershell
python -m codebase_context index C:\path\to\repository
python -m codebase_context search "authentication middleware" --index-path C:\path\to\repository\.context-engine\index.json
```

## Optional integrations

Install only what is needed:

```powershell
python -m pip install -e ".[api,ai,vector,parser,worker,postgres]"
```

Copy `.env.example` to `.env`. Live GitHub OAuth requires a GitHub OAuth App configured with the callback URL. Private repository cloning requires a narrowly scoped GitHub token; do not commit it. OpenAI embeddings require `OPENAI_API_KEY`. Pinecone, tree-sitter language packs, Celery/Redis, and PostgreSQL drivers have extension hooks/dependencies but are not required for the default lexical local demo.

Docker Compose is provided for API + Redis startup. The current API prototype performs reindexing inline; Celery worker wiring, retry policies, webhook sync, and production Redis-backed caching remain follow-up work.

## API routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/auth/github` | Begin GitHub OAuth |
| GET | `/auth/github/callback` | Exchange OAuth code and issue bearer token |
| POST | `/repos/connect` | Connect a GitHub repository |
| GET | `/repos` | List the authenticated user's repositories |
| POST | `/query` | Search indexed code and return cited sources |
| GET | `/query/{id}` | Read an owned query result |
| POST | `/repos/{id}/reindex` | Clone/update and index a repository |
| DELETE | `/repos/{id}` | Delete repository metadata and local index |

`POST /auth/dev-token` exists only when `SOURCEMAP_DEV_AUTH=1`; disable it outside local development. The `/auth/github` flow needs GitHub OAuth credentials. The prototype stores the GitHub app token only in process configuration and currently expects a configured `GITHUB_TOKEN` for private cloning; a production OAuth-token vault is not implemented.

## Example local API session

1. Set `SOURCEMAP_JWT_SECRET` and `SOURCEMAP_DEV_AUTH=1`.
2. Request `POST /auth/dev-token` and copy the returned bearer token.
3. Send `POST /repos/connect` with `{"full_name":"owner/repository"}`.
4. Trigger `POST /repos/{id}/reindex`.
5. Send `POST /query` with `{"repo_id":"...","query":"where is authentication checked?"}`.

## Architecture

```text
GitHub → clone/fetch → parse/chunk → optional embeddings → local JSON index
                                              ↓
Query → lexical retrieval → rerank → optional LangGraph → cited response
```

The default prototype remains local and lexical. `tree-sitter-language-pack`, OpenAI embeddings, Pinecone retrieval, and LangGraph are optional dependencies. The current indexing pipeline chunks by line windows and detects common declarations; it does not yet use syntax-tree queries or write embeddings into Pinecone. The metadata model reserves those fields for the next implementation slice.

## Security and production gaps

- Use HTTPS at the deployment edge and a managed secrets store.
- Replace the local SQLite store with PostgreSQL and tenant-aware migrations for production.
- Add encrypted storage, OAuth token encryption/rotation, organization access controls, audit retention policy, and verified deletion across backups.
- Current rate limiting is per-process memory and will not coordinate multiple workers.
- Current token counting is a character-based estimate; use the provider tokenizer for billing.
- The listed response confidence is a retrieval score heuristic, not calibrated probability.
- Production multi-hop query decomposition, provider LLM synthesis, GitHub webhooks, Celery jobs, incremental changed-file indexing, team roles, and CI deployment are not complete.
- No security scan or compliance certification is claimed.

## Project layout

- `sourcemap/api.py` — FastAPI routes and request handling.
- `sourcemap/github.py` — OAuth and GitHub API calls.
- `sourcemap/indexing.py` — repository cloning, chunking, parser/embedding hooks.
- `sourcemap/retrieval.py`, `sourcemap/graph.py` — retrieval and optional orchestration.
- `sourcemap/db.py`, `sourcemap/security.py` — local persistence and bearer-token helpers.
- `codebase_context/` — dependency-free CLI indexer and BM25-style search.
- `tests/` — unit tests for the local retrieval engine.

## Tests

```powershell
python -m unittest discover -s tests -v
```
