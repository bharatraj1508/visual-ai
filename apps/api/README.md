# Visual AI — Conversational Data Analyst

Upload any CSV and explore it in plain language. Ask questions, generate charts,
and produce multi-section analytical reports — the way a data engineer would in a
notebook, but driven by prompts. Works on any tabular data: attendance sheets,
inventories, stock histories, sports datasets, anything.

This repository is the **Python / FastAPI backend**.

---

## What it does

- **Upload & profile CSVs** — the file is cached as Parquet and profiled (types,
  null counts, cardinality, ranges, sample values) on upload.
- **Chat with your data** — a Gemini-powered agent answers questions by writing
  and running queries, never by guessing. Responses stream live.
- **Generate any chart from a prompt** — bar, line, area, scatter, pie, histogram
  — returned as **Vega-Lite** specs the frontend renders interactively.
- **Advanced analysis** — an agent escape hatch runs sandboxed pandas for things
  SQL can't express (rolling windows, custom transforms, modeling).
- **Multi-section reports** — the agent plans sections, analyzes each, and
  assembles a narrative + charts, streamed as it's produced.
- **Multi-user** — JWT auth; every dataset, chat, and report is scoped to its
  owner.

### Why there's no RAG / no chunking

A CSV is *structured*, so retrieval over rows is the wrong tool. The LLM never
sees the raw data — it sees a compact **profile** (schema + stats + a few sample
values, a few hundred tokens). It then **writes queries/code** that run
deterministically in DuckDB/pandas over the full dataset. This keeps token cost
tiny and scales from tiny files to millions of rows.

---

## Tech stack

| Area | Choice |
|------|--------|
| API | FastAPI (async), Uvicorn |
| LLM | Google **Gemini** via `langchain-google-genai` |
| Agent | **LangGraph** `create_react_agent` (ReAct loop, streaming, tool-calling) |
| Data engine | **DuckDB** over **Parquet**, pandas, PyArrow |
| Charts | **Vega-Lite** specs (rendered client-side) |
| Streaming | Server-Sent Events (`sse-starlette`) |
| Database | PostgreSQL + SQLAlchemy 2.0 (async) + Alembic |
| Auth | JWT (`python-jose`) + bcrypt |
| Sandbox | isolated subprocess + AST guard + resource limits |
| Tests | pytest, pytest-asyncio, httpx |

---

## Architecture at a glance

```
Upload CSV ─▶ profile (pandas) ─▶ store Parquet + column profile in Postgres
                                        │  (only the profile feeds the LLM)
Prompt ─▶ LangGraph ReAct agent (Gemini) ─▶ picks tools:
              ├─ query_data      → DuckDB SQL over table `data`      (safe)
              ├─ describe_data / value_counts / correlate            (safe)
              ├─ create_chart    → validated Vega-Lite spec          (safe)
              └─ run_python      → sandboxed pandas escape hatch     (guarded)
          results stream over SSE ─▶ Next.js renders tokens + charts live
```

The data engine is doubly sandboxed for agent-written SQL: the Parquet is loaded
into an in-memory DuckDB table, then external access is disabled and the config
locked — so a query cannot read or write files. `run_python` runs in a separate
process with an AST guard, no imports, no network, no filesystem writes, and CPU
/ memory / wall-clock limits.

---

## Project structure

```
app/
├── main.py                 # FastAPI app + CORS
├── core/                   # config, database, logging, security (JWT)
├── models/                 # SQLAlchemy models (User, Dataset, ChatSession, …)
├── schemas/                # Pydantic DTOs
├── services/               # auth, storage, CSV ingestion, DuckDB data access
├── agent/                  # DatasetContext, prompts, LangGraph graph, streaming
│   ├── tools/              # query/describe/correlate, create_chart, run_python
│   └── report.py           # multi-section report orchestration
├── sandbox/                # isolated executor + child runner for run_python
├── migrations/             # Alembic migrations
└── api/v1/endpoints/       # auth, datasets, chat, reports, health
scripts/smoke_chat.py       # live agent smoke test
tests/                      # pytest suite
```

---

## Getting started

### Prerequisites
- Python 3.12+ (developed on 3.14)
- Docker (for PostgreSQL) — or your own Postgres
- A **Google Gemini API key** → https://aistudio.google.com/app/apikey

### 1. Install
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
# then edit .env — set GOOGLE_API_KEY and a strong SECRET_KEY
```

### 3. Database
```bash
docker compose up -d db        # starts Postgres 16 on localhost:5433
alembic upgrade head           # apply all migrations
```

### 4. Run
```bash
uvicorn app.main:app --reload
# API:  http://localhost:8000
# Docs: http://localhost:8000/api/v1/openapi.json  (Swagger at /docs)
```

### 5. Smoke-test the agent (optional)
```bash
python scripts/smoke_chat.py   # uploads a sample CSV and asks Gemini a question
```

---

## Environment variables

See [`.env.example`](.env.example). Summary:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://user:pass@host:port/db` |
| `GOOGLE_API_KEY` | ✅ (for agent) | Gemini API key |
| `SECRET_KEY` | ✅ (prod) | JWT signing key — generate a strong value |
| `GEMINI_MODEL` | | Default `gemini-2.5-flash` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | JWT lifetime (default 1440) |
| `STORAGE_DIR` | | Where uploads + Parquet live (default `storage`) |
| `BACKEND_CORS_ORIGINS` | | Comma-separated frontend origins |
| `ENV` | | `development` / `production` |

---

## API reference (`/api/v1`)

**Auth**
```
POST /auth/register           {email, password}
POST /auth/login              form: username(email), password  → JWT
GET  /auth/me                 (Bearer)
```

**Datasets**
```
POST   /datasets              multipart file=<csv>       → dataset (profiled)
GET    /datasets
GET    /datasets/{id}
GET    /datasets/{id}/profile → columns + stats
DELETE /datasets/{id}
```

**Chat** (SSE stream: `token`, `tool_start`, `tool_end`, `chart`, `done`)
```
POST   /chat/sessions                    {dataset_id, title?}
GET    /chat/sessions
GET    /chat/sessions/{id}/messages
POST   /chat/sessions/{id}/messages      {content}   ← SSE
DELETE /chat/sessions/{id}
```

**Reports** (SSE stream: `report_start`, `section_start`, `token`, `chart`, `section_end`, `report_done`)
```
POST   /reports              {dataset_id, goal, title?}   ← SSE
GET    /reports
GET    /reports/{id}
DELETE /reports/{id}
```

---

## Development

```bash
pytest                                   # run the test suite
alembic revision --autogenerate -m "…"   # new migration after model changes
alembic upgrade head                     # apply migrations
```

## Security notes

`run_python` executes model-generated code. The current guard (AST checks +
subprocess isolation + resource limits + no network/filesystem) is sound for a
semi-trusted, single-tenant MVP. **Before untrusted multi-tenant traffic, run the
sandbox subprocess inside a container / gVisor / microVM** for a real isolation
boundary.

## Roadmap

- Frontend (Next.js) rendering the SSE streams and Vega-Lite charts
- Report export (PDF/Markdown)
- Background job queue for very long reports
- Container-isolated sandbox
