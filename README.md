# Sutura

Sutura is a personal finance and salary distribution app: turn your salary, allowances, and other
income into a clear monthly plan — what's allocated, what's spent, and what's saved. Built to work
for someone with no accounting background, with the backend as the sole source of truth for every
number shown.

Full product/technical specification: [personal_finance_salary_distribution_ai_build_spec.md](personal_finance_salary_distribution_ai_build_spec.md).
Project-wide engineering rules: [CLAUDE.md](CLAUDE.md).

## Status

Phase 1 (Discovery) and Phase 2 (Foundation) are complete — see [docs/](docs/) for the architecture,
ERD, API contract, frontend route structure, and the decision log resolving every ambiguity found in
the spec.

- **Backend**: auth and `financial_periods` are fully implemented (register/login/verify/reset,
  create/close/reopen with audit trail). `financial_engine` implements all 9 canonical formulas in
  exact `Decimal` arithmetic. The remaining modules (salary, allowances, income, expenses,
  distribution, savings, banks, transactions, reports, analytics, attachments) are CRUD-plus-audit
  scaffolds — their full validation matrix (100%-sum checks, optimistic locking, automatic savings
  wired end-to-end) is Phase 3 work.
- **Web**: the dashboard and auth pages (`/`, `/login`, `/register`, `/dashboard`) are fully built on
  a deliberate editorial-fintech design system. The remaining routes are stubs sharing the same
  layout/navigation.

## Tech stack

| Layer | Choice |
|---|---|
| Web | Next.js, TypeScript, Tailwind CSS, shadcn/ui, Recharts |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy |
| Database | PostgreSQL (`NUMERIC` for all money — never floating point) |
| Migrations | Alembic |
| Background jobs | Redis + Celery |
| Mobile (planned) | Flutter/Dart, against the same FastAPI backend |
| Testing | Pytest (backend), Vitest + React Testing Library (web), Playwright (E2E, planned) |

Architecture is a modular monolith — no microservices. One FastAPI backend serves both the web app
and the future Flutter app; no financial logic is duplicated between clients.

## Repository layout

```
backend/    FastAPI app, SQLAlchemy models, Alembic migrations, pytest suite
web/        Next.js app (App Router)
docs/       Architecture, ERD, API contract, frontend routes, decision log
.claude/    Claude Code project config — custom agents and skills for this codebase
```

## Running locally

### With Docker

```bash
cp backend/.env.example backend/.env   # fill in real secrets for anything beyond local dev
docker compose up --build
```

This starts Postgres, Redis, the backend (migrations run automatically on boot,
`http://localhost:8000`, OpenAPI docs at `/api/v1/docs`), and the web app (`http://localhost:3000`).

### Without Docker

**Backend** (requires Python 3.12 and a running Postgres — see `backend/.env.example` for the
expected connection string):

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
cp .env.example .env   # edit DATABASE_URL etc. to match your local Postgres
alembic upgrade head
uvicorn app.main:app --reload
```

Run the backend test suite:

```bash
cd backend && pytest -v
```

**Web** (requires Node 22+):

```bash
cd web
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL, defaults to http://localhost:8000
npm run dev
```

Run the web test suite:

```bash
cd web && npx vitest run
```

## CI

GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs the backend test suite
against a real Postgres service container, and lints/tests/builds the web app, on every push and
pull request.

## Contributing to this codebase with Claude Code

This repo ships Claude Code project config under `.claude/`: custom agents (`financial-architect`,
`backend-engineer`, `financial-engine-dev`, `frontend-engineer`, `qa-engineer`,
`security-reviewer`) scoped to this app's domain, and skills (`financial-formula-audit`,
`new-financial-module`, `edge-case-audit`) for the recurring checks this codebase needs. `CLAUDE.md`
holds the non-negotiable rules — read it before making any change that touches money.
