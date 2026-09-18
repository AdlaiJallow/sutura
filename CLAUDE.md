# Sutura — Personal Finance & Salary Distribution App

Full spec: [personal_finance_salary_distribution_ai_build_spec.md](personal_finance_salary_distribution_ai_build_spec.md). This file is the load-bearing summary — read the full spec before making any architectural or financial-logic decision it might cover.

## What this is

A personal finance and salary distribution system: salary + allowances + other income → a user-defined distribution rule → category allocations → expenses against those allocations → automatic + manual savings → bank/account allocation → monthly summary → historical analytics. It must work for someone with no accounting background, and the backend is the sole source of truth for every number shown.

## Tech stack (fixed — do not substitute without a strong technical reason, and say so explicitly if you do)

- **Web**: Next.js, TypeScript, Tailwind CSS, shadcn/ui, Recharts
- **Backend**: Python, FastAPI, Pydantic, SQLAlchemy
- **DB**: PostgreSQL, `NUMERIC`/`DECIMAL` only for money — never floating point
- **Migrations**: Alembic
- **Background jobs**: Redis + Celery (recurring records, monthly processing, reports, notifications)
- **Mobile**: Flutter/Dart, consumes the same FastAPI backend — no duplicated financial logic
- **Auth**: email/password + verification + reset, OAuth/OIDC where appropriate, secure sessions, optional MFA
- **File storage**: S3-compatible, for receipts/documents
- **Infra**: Docker + Docker Compose (local), GitHub Actions CI/CD, Nginx reverse proxy
- **Testing**: Pytest (backend), Playwright (E2E), a TS framework for frontend unit/component tests
- **Monitoring**: Sentry, structured logging, health checks

## Architecture

Modular monolith. **Do not introduce microservices.** One FastAPI backend serves both the Next.js web app and the Flutter mobile app — never fork financial business logic between clients. Backend modules (see spec §29): `auth, users, financial_periods, salary, allowances, income, expenses, distribution, savings, banks, transactions, reports, analytics, attachments, audit, common`. Within each module keep API routes, schemas/DTOs, business services, data access, and DB models in separate layers.

Keep all financial math inside a dedicated, heavily unit-tested domain layer (`financial_engine/`: income, distribution, expense, savings, bank-allocation, monthly-summary calculators — spec §30). **Never** implement financial calculations in frontend components, and **never** trust a client-submitted total (e.g. a posted `total_income` field) as authoritative — always recompute server-side from persisted records (spec §46).

## FinancialPeriod is central

Everything hangs off a `FinancialPeriod` (normally one calendar month). Records from different periods must never mix except in explicit analytics queries. Periods have `Open`/`Closed` status; a closed period is not casually edited — editing requires an explicit action, an audit event, a summary recalculation, and a visible "modified" indicator. Never silently rewrite a closed historical period. Recurring records (salary, rent, etc.) generate a new record per period rather than sharing one mutable record — a change in October must never rewrite September's history (spec §5, §37, §41).

## Canonical formulas — implement and test these exactly (spec §26)

```
Total Allowances       = SUM(Allowances)
Total Salary Income     = Net Salary + Total Allowances
Total Monthly Income     = Total Salary Income + Other Income
Category Allocation     = Total Monthly Income × Category Percentage
Category Used           = SUM(Category Items)
Category Remaining      = Category Allocation - Category Used
Automatic Savings       = SUM(Eligible Positive Category Remaining Values)   # eligibility is configurable, not hardcoded
Final Savings           = Automatic Savings + Manual Savings
Undistributed Savings   = Final Savings - Savings Distributed
```

Distribution rule percentages must total exactly 100% (or explicitly include an "Unallocated" category) — reject saves otherwise. Never let bank/savings allocation exceed available Final Savings. Overspending on a category is shown as a visible negative remaining balance; it never silently steals from another category — only an explicit user reallocation moves money between categories (spec §13).

Avoid double-counting: salary/allowances, generic income, budget allocations, actual expenses, and account transactions are distinct entities linked by reference, never re-derived by re-summing across layers (spec §9, §27).

Use `Decimal` in Python and `NUMERIC` in Postgres for every monetary value, everywhere, with no exceptions.

## Non-negotiable developer rules (spec §48)

1. Don't invent financial behavior when the spec is ambiguous — flag it instead.
2. Any ambiguous rule that affects calculations gets identified and resolved before implementation, not during.
3. Centralize and test financial calculations; never duplicate them in the frontend or mobile app.
4. Never use floating-point arithmetic for money.
5. Never trust client-provided totals.
6. Never silently overwrite historical financial records.
7. No microservices at the start.
8. Keep the system modular.
9. Write tests for every important financial calculation, including rounding.
10. Use migrations for every schema change.
11. No secrets in source control.
12. Follow secure coding practice by default (see Security below).
13. Prefer simple solutions over speculative complexity — no premature abstraction, no unused flexibility.
14. Document non-obvious architectural decisions.
15. Consistent API responses and explicit error handling.
16. Responsive, plain-language UI (prefer "Money Available / Remaining / Spent / Saved" over technical accounting terms).
17. Build for maintainability, not a demo.

## Security & privacy (spec §34–36)

- A user must never be able to reach another user's records by changing an ID — enforce ownership checks on every query, not just at the route layer.
- Mask bank/account identifiers in the UI and API responses; never log passwords, tokens, full account numbers, or unnecessary sensitive financial data.
- Validate all input server-side; rely on the ORM/parameterized queries; validate file type and size on uploads.
- Audit important financial changes (income, expenses, distribution rules, savings, bank transactions/transfers, period close/reopen) with who/what/before/after/when/related-record.

## Definition of done (spec §49)

A feature isn't done when the UI shows a form. It's done when it has: a DB model, an API, server-side validation, business logic in the domain layer, UI, explicit error handling, authorization/ownership checks, tests, and documented edge-case behavior. Financial calculations additionally need independent unit tests reproducing the spec's worked examples (spec §40).

## Edge cases to keep in mind

The spec lists 35 edge cases in §38 (zero income, category fully unused, overspending, bank over-allocation attempts, recurring records, closed-period edits, rounding, concurrent updates, etc.). Before marking any financial feature complete, check it against that list — the `edge-case-audit` skill automates this.

## Implementation sequence (spec §47)

Discovery (architecture/ERD/API contract/routes) → Foundation (Docker, Postgres, FastAPI, SQLAlchemy, Alembic, auth, CI) → Financial Core (periods, salary, allowances, income, expenses, distribution, savings engines) → Accounts (banks, transactions, savings allocation) → Web UI → Testing → Mobile (Flutter) → Production hardening. Don't skip ahead to UI polish before the financial core is correct and tested.
