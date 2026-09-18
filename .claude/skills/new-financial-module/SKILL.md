---
name: new-financial-module
description: Scaffold a new backend domain module (e.g. a new financial_periods, savings, or banks-style module) with the standard layered structure - SQLAlchemy model, Pydantic schemas, service layer, repository, API router, Alembic migration stub, and Pytest test file - consistent with Sutura's modular monolith. Use when asked to add a new backend module/entity/resource, not for editing an existing one.
---

# New Financial Module Scaffold

Use this skill to create a new backend module under `backend/app/` (or the equivalent path if the project layout has diverged — check first) following Sutura's established layering. Read `/CLAUDE.md` first for the non-negotiable rules this scaffold must respect.

## Before scaffolding

1. Confirm the module doesn't already exist (grep `backend/app/` for the entity name).
2. Confirm with the financial-architect perspective: does this entity belong to a `FinancialPeriod`? Does it belong to a `User`? What foreign keys and constraints does it need (spec §45)? If this is genuinely a new financial concept not covered by the spec's entity list (spec §28), flag that as a decision to confirm rather than guessing.
3. Determine whether this module contains any monetary calculation. If it does, the calculation belongs in `financial_engine/`, called by this module's service layer — not implemented inline here.

## Structure to generate

For a module named `<name>`:

```
backend/app/<name>/
├── __init__.py
├── models.py        # SQLAlchemy model(s); NUMERIC for money, FKs to user/financial_period
├── schemas.py        # Pydantic request/response DTOs — never accept a client-computed total as authoritative
├── repository.py     # data access, always scoped to the owning user
├── service.py        # business logic; calls financial_engine for any math
├── router.py         # FastAPI routes under /api/v1/<name>, consistent pagination/filtering/error shape
└── dependencies.py   # module-local FastAPI dependencies, if needed

backend/alembic/versions/<timestamp>_<name>.py   # migration for the new table(s)
backend/tests/<name>/
├── test_service.py
├── test_router.py
└── test_repository.py   # include an explicit cross-user isolation test
```

## Rules while scaffolding

- Every list endpoint supports pagination/filtering/sorting per the conventions already used in existing modules (check `backend/app/expenses/` or `backend/app/income/` if present, for the established pattern — don't invent a new convention).
- Every repository query is scoped by `user_id` (and `financial_period_id` where applicable) — write the cross-user isolation test as part of the scaffold, not as an afterthought.
- Audit-worthy mutations (create/update/delete on income, expenses, distribution rules, savings, bank transactions, period close/reopen) call into the audit module.
- Every monetary field is `NUMERIC` in the model and `Decimal` in the schema.
- Include at least a happy-path test and a validation-failure test in the generated test files — this is a scaffold, not a finished feature; leave clear `# TODO` markers only for things that genuinely need the requester's input (e.g. specific business rules), not as a substitute for writing the obvious tests.

## After scaffolding

List what was generated, what still needs a decision (e.g. "does this need its own distribution eligibility flag?"), and remind the caller this isn't done until it passes the Definition of Done in `/CLAUDE.md`.
