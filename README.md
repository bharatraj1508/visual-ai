# Visual AI — Monorepo

Conversational data-analyst product: upload any CSV and explore it in plain
language — ask questions, generate charts, and produce multi-section reports.

This is a **Turborepo** monorepo managed with **yarn workspaces**.

```
visual-ai/
├── apps/
│   ├── api/     # FastAPI + Gemini backend (Python)   — see apps/api/README.md
│   └── web/     # Next.js 14 frontend (TypeScript)
├── packages/    # shared packages (future)
├── turbo.json
└── package.json
```

## Tech

| Layer | Stack |
|-------|-------|
| Frontend | Next.js 14 (App Router), React 18, TypeScript |
| State | Redux Toolkit + redux-persist (access token) |
| Data fetching | TanStack React Query v5 (enum query keys) |
| HTTP | axios with a Bearer-token interceptor |
| Styling | Tailwind CSS v3 |
| Backend | FastAPI, LangGraph + Gemini, DuckDB/Parquet, Postgres |
| Tooling | Turborepo, yarn workspaces, Prettier |

## Prerequisites

- Node **>= 22** (`.nvmrc` → 22) and Yarn 1.x (via `corepack enable`)
- Python 3.12+ and Docker (for the backend + Postgres)

## Getting started

```bash
# 1. Install JS deps for all workspaces
corepack enable
yarn install

# 2. Backend: Python env + database (see apps/api/README.md for detail)
cd apps/api
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
cp .env.example .env            # set GOOGLE_API_KEY + SECRET_KEY
cd ../.. && docker compose up -d db
cd apps/api && .venv/bin/alembic upgrade head && cd ../..

# 3. Frontend env
cp apps/web/.env.example apps/web/.env.local   # set NEXT_PUBLIC_BASE_API_URL

# 4. Run everything (turbo runs api + web together)
yarn dev
# web → http://localhost:3000    api → http://localhost:8000
```

## Common commands

```bash
yarn dev            # turbo run dev  (all apps)
yarn build          # turbo run build
yarn lint           # turbo run lint
yarn test           # turbo run test
yarn workspace @visual-ai/web dev     # run a single workspace
yarn workspace @visual-ai/api test
```

See [`apps/api/README.md`](apps/api/README.md) for the full backend docs and API
reference.
