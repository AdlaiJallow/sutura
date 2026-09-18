# Personal Finance & Salary Distribution Application
## AI Development Specification

## 1. Role

Act as a senior software architect, product engineer, UI/UX engineer, security engineer, database designer, and QA engineer.

Build this application as a production-quality personal finance and salary distribution system.

Do not jump directly into coding. First understand the requirements, design the architecture and data model, identify ambiguities and edge cases, then implement the system in logical phases.

The application must be maintainable, secure, testable, scalable, and easy for a non-financial expert to use.

---

# 2. Product Vision

The application is a personal financial management system focused on:

- Salary
- Allowances
- Other monthly income
- Expenses
- Flexible income distribution rules
- Category budgets
- Automatic calculation of unused allocations
- Final savings
- Manual savings
- Bank/account management
- Savings distribution
- Monthly financial history
- Financial analytics and reporting

The application should behave like a personal financial distribution assistant rather than a simple spreadsheet.

The user should be able to answer:

1. How much money did I receive this month?
2. Where is my money supposed to go?
3. How much have I spent?
4. How much remains in each category?
5. How much did I actually save?
6. Where did my savings go?
7. How much was allocated to each bank/account?
8. How has my financial position changed over time?

---

# 3. Definitive Technology Stack

Do not substitute the technology stack without a strong technical reason.

## Web Frontend

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui
- Recharts for charts

## Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy

## Database

- PostgreSQL
- Use `NUMERIC/DECIMAL` for monetary values
- Never use floating-point values for financial calculations

## Database Migrations

- Alembic

## Background Processing

- Redis
- Celery

Use background processing only where appropriate, such as:

- Recurring financial records
- Monthly processing
- Notifications
- Report generation
- Scheduled jobs

## Mobile

- Flutter
- Dart

Flutter should consume the same FastAPI backend.

Do not duplicate financial business logic between the web and mobile applications.

## API

- REST API
- OpenAPI documentation through FastAPI

## Authentication

Use a secure authentication solution supporting modern authentication practices such as:

- Email/password
- Email verification
- Password reset
- OAuth/OIDC where appropriate
- Secure sessions/tokens
- MFA support if implemented

## File Storage

Use S3-compatible object storage for receipts and financial documents.

## Infrastructure

- Docker
- Docker Compose for local development
- GitHub Actions for CI/CD
- Nginx or equivalent reverse proxy where appropriate

## Testing

Backend:

- Pytest

Frontend/E2E:

- Playwright

Additional frontend unit/component testing may use an appropriate TypeScript testing framework.

## Monitoring

- Sentry
- Structured application logging
- Health checks

---

# 4. Architecture

Use a modular monolith initially.

Do NOT start with microservices.

Recommended architecture:

```text
                    ┌─────────────────────┐
                    │      Next.js        │
                    │       Web           │
                    └──────────┬──────────┘
                               │
                               │ REST API
                               ▼
                    ┌─────────────────────┐
                    │       FastAPI       │
                    │                     │
                    │ Authentication      │
                    │ Users               │
                    │ Financial Periods   │
                    │ Salary              │
                    │ Allowances          │
                    │ Income              │
                    │ Expenses            │
                    │ Distribution        │
                    │ Savings             │
                    │ Banks               │
                    │ Transactions        │
                    │ Reports             │
                    └──────────┬──────────┘
                               │
                  ┌────────────┴────────────┐
                  ▼                         ▼
           ┌──────────────┐          ┌─────────────┐
           │ PostgreSQL   │          │    Redis    │
           │              │          │             │
           │ Financial    │          │ Background  │
           │ Data         │          │ Jobs        │
           └──────────────┘          └─────────────┘
                  ▲
                  │
            ┌─────┴─────┐
            │           │
            │ Flutter   │
            │ Mobile    │
            │ Android/iOS
            └───────────┘
```

The same backend must serve both web and mobile clients.

---

# 5. Financial Period

Introduce a first-class `FinancialPeriod` concept.

A financial period normally represents one calendar month.

Example:

```text
September 2026
```

A financial period contains:

```text
Financial Period
│
├── Income
├── Salary
├── Allowances
├── Expenses
├── Distribution Plan
├── Distribution Categories
├── Category Items
├── Final Savings
└── Bank/Savings Allocations
```

Users must be able to view previous periods.

The system should not mix records from different financial periods unless explicitly requested for analytics.

---

# 6. Salary

Create a Salary module.

A user should be able to record their monthly net salary.

Fields should include at least:

- Financial period
- Net salary
- Currency
- Notes
- Status
- Created date
- Updated date

The salary is the user's primary salary income.

---

# 7. Allowances

Allow users to add unlimited allowances.

Examples:

- Housing
- Transport
- Communication
- Medical
- Responsibility
- Overtime
- Meal
- Other

Fields:

- Name
- Amount
- Financial period
- Date
- Recurring / one-time
- Notes

Calculate:

```text
Total Allowances = Sum(All Allowances)
```

Then:

```text
Total Salary Income =
Net Salary + Total Allowances
```

This must update automatically.

---

# 8. Other Income

Users must be able to record unlimited income entries.

Income types should include:

- Salary
- Allowance
- In-country payment
- Per diem
- Freelance
- Business
- Investment
- Other

Fields:

- Description
- Type
- Amount
- Date received
- Source
- Recurring / one-time
- Financial period
- Notes

Calculate:

```text
Total Other Income = Sum(Other Income)
```

And:

```text
Total Monthly Income =
Salary Income + Other Income
```

Avoid double-counting salary and allowances.

The data model must clearly distinguish salary/allowance records from generic income records.

---

# 9. Expenses

Users can add unlimited expenses.

Suggested categories:

- Rent
- Food
- Transportation
- Electricity
- Water
- Internet
- Phone
- Education
- Healthcare
- Family support
- Entertainment
- Shopping
- Debt repayment
- Other

Fields:

- Name
- Category
- Amount
- Date
- Payment method
- Account used
- Financial period
- Notes
- Optional receipt/document

Calculate:

```text
Total Expenses = Sum(All Expenses)
```

---

# 10. Distribution Rules

Users must be able to create flexible income distribution rules.

A default example is:

```text
Needs     50%
Savings   30%
Wants     20%
```

But this must NOT be hardcoded.

Users can create their own rules.

Examples:

```text
60 / 20 / 20
50 / 30 / 20
70 / 20 / 10
```

Or completely custom categories:

```text
Rent              30%
Family             10%
Daily Expenses     25%
Savings            25%
Entertainment      10%
```

Distribution percentages must normally total exactly 100%.

Prevent saving a distribution rule whose total is not 100%, unless an explicit "Unallocated" category is introduced.

Rules should have:

- Name
- Description
- Categories
- Percentage per category
- Active/inactive status
- Default status

A user should be able to select a rule for a financial period.

---

# 11. Automatic Distribution

Calculate each category allocation using:

```text
Category Allocation =
Total Monthly Income × Category Percentage
```

Example:

```text
Total Income = D14,000

Needs     50% = D7,000
Savings   30% = D4,200
Wants     20% = D2,800
```

Whenever eligible income changes, the system should recalculate the plan.

Whenever a distribution rule changes, the system should recalculate affected allocations.

Historical financial records must remain auditable.

Do not silently rewrite closed historical periods.

---

# 12. Items Under Distribution Categories

Users can add individual items under each category.

Example:

```text
Needs Allocation = D7,000

Rent            D2,500
Food            D1,500
Transport       D800
Electricity     D500
```

Calculate:

```text
Category Used =
Sum(Category Items)
```

And:

```text
Category Remaining =
Category Allocation - Category Used
```

Show:

- Allocated
- Used
- Remaining
- Overspent

---

# 13. Overspending

The application must not silently prevent or hide overspending.

Example:

```text
Needs Allocation = D5,000
Needs Spending   = D5,500

Overspent = D500
```

The UI should clearly show:

- Allocation
- Actual spending
- Difference
- Overspending status

Define whether overspending affects other categories or final savings.

Recommended default behavior:

Overspending remains visible as a negative category balance and does not automatically steal money from another category unless the user explicitly reallocates funds.

---

# 14. Unused Allocation and Automatic Savings

Unused amounts must be tracked.

Example:

```text
Needs:
Allocated = D5,000
Used      = D4,500
Remaining = D500
```

The D500 should be eligible to become final savings.

Similarly:

```text
Savings:
Allocated = D3,000
Used      = D2,700
Remaining = D300
```

```text
Wants:
Allocated = D2,000
Used      = D1,800
Remaining = D200
```

Then:

```text
Automatic Savings =
D500 + D300 + D200

Automatic Savings = D1,000
```

The application must explicitly define which category types contribute their unused balances to final savings.

This must be configurable rather than hidden in code.

---

# 15. Final Savings

Create a dedicated Final Savings module.

Final Savings should track:

1. Automatically generated savings
2. Manually added savings
3. Savings allocated to accounts
4. Savings remaining undistributed

Example:

```text
Automatic Savings      D1,000
Manual Savings          D500
                       ───────
Final Savings           D1,500
```

Then:

```text
Bank A                  D800
Bank B                  D400
Emergency Fund          D200
Undistributed            D100
```

---

# 16. Manual Final Savings

Users can manually add savings items.

Examples:

- Emergency fund
- Investment
- Vacation fund
- Bank savings
- Long-term savings
- Other

Fields:

- Name
- Amount
- Date
- Financial period
- Destination
- Notes

Clearly distinguish manual savings from automatically generated savings.

---

# 17. Bank and Financial Accounts

Create a Bank/Account module.

Users can add:

- Bank accounts
- Mobile money accounts
- Cash
- Savings accounts
- Investment accounts
- Other financial accounts

Fields:

- Account name
- Institution/provider
- Account type
- Account identifier
- Currency
- Opening balance
- Current balance
- Active/inactive
- Notes

Sensitive identifiers must be masked in the UI.

Do not expose full account numbers unnecessarily.

---

# 18. Bank Transactions

Use transaction-based accounting rather than simply changing balances.

Example:

```text
Income
  ↓
Allocation
  ↓
Savings
  ↓
Bank Transaction
  ↓
Bank Account
```

Transactions should have:

- Account
- Type
- Amount
- Date
- Financial period
- Source/reference
- Description
- Related financial record
- Created date

Types may include:

- Deposit
- Withdrawal
- Transfer
- Adjustment

Bank balances should be derived from a reliable transaction history where practical.

---

# 19. Savings Distribution to Banks

Allow users to distribute final savings across accounts.

Example:

```text
Final Savings = D5,000

Trust Bank     D2,000
GTBank         D1,500
QMoney         D1,000
Cash             D500
```

Validate:

```text
Total Distributed <= Available Final Savings
```

Never allow silent over-allocation.

Show:

```text
Final Savings             D5,000
Distributed               D5,000
Undistributed                 D0
```

---

# 20. Automatic Savings Distribution Rules

Allow users to create savings distribution rules.

Example:

```text
Bank A            40%
Bank B            30%
Emergency Fund    20%
Investment        10%
```

If Final Savings is D10,000:

```text
Bank A            D4,000
Bank B            D3,000
Emergency Fund    D2,000
Investment        D1,000
```

The rule must validate to 100%.

Users should be able to override automatic allocations manually.

---

# 21. Dashboard

Build a clear financial dashboard.

Show:

## Income

- Net salary
- Total allowances
- Other income
- Total monthly income

## Distribution

- Needs allocation
- Savings allocation
- Wants allocation
- Custom categories

## Spending

- Total expenses
- Spending by category
- Planned vs actual

## Savings

- Planned savings
- Automatic savings
- Manual savings
- Final savings
- Distributed savings
- Undistributed savings

## Accounts

- Current account balances
- Deposits this month
- Savings allocated per account

Use cards, tables, progress indicators, and charts.

---

# 22. Monthly Summary

Generate a summary for every financial period.

Example:

```text
September 2026

Total Income              D20,000
Total Expenses            D12,000
Planned Savings            D6,000
Automatic Savings          D2,000
Manual Savings              D500
Final Savings               D2,500
Bank Deposits               D2,000
Undistributed Savings         D500
```

The exact terminology and calculation must avoid double-counting.

---

# 23. Historical Financial Data

Users must be able to select a previous month and view:

- Income
- Salary
- Allowances
- Expenses
- Distribution plan
- Actual spending
- Remaining allocations
- Savings
- Bank allocations
- Transactions

Do not allow later rule changes to corrupt the historical interpretation of a closed period.

Maintain snapshots or immutable financial-period records where appropriate.

---

# 24. Analytics

Provide:

- Monthly income trend
- Monthly expense trend
- Monthly savings trend
- Savings rate
- Spending by category
- Income by source
- Planned vs actual spending
- Bank savings growth
- Unused allocations
- Category overspending
- Month-to-month comparison

Possible future analytics:

- Forecasting
- Savings projections
- Cash-flow forecasting
- Spending anomaly detection
- Budget recommendations

Do not implement advanced ML until the core accounting model is stable.

---

# 25. Currency

The initial application should support the Gambian Dalasi (GMD/D).

Design the data model so multiple currencies can be supported later.

Do not hardcode currency assumptions throughout the business logic.

Monetary values must use decimal arithmetic.

---

# 26. Financial Calculation Rules

Use exact decimal arithmetic.

Recommended:

Python:

```text
Decimal
```

PostgreSQL:

```text
NUMERIC
```

Never rely on binary floating-point for financial calculations.

Core formulas:

```text
Total Allowances =
SUM(Allowances)
```

```text
Total Salary Income =
Net Salary + Total Allowances
```

```text
Total Monthly Income =
Total Salary Income + Other Income
```

```text
Category Allocation =
Total Monthly Income × Category Percentage
```

```text
Category Used =
SUM(Category Items)
```

```text
Category Remaining =
Category Allocation - Category Used
```

```text
Automatic Savings =
SUM(Eligible Positive Category Remaining Values)
```

```text
Final Savings =
Automatic Savings + Manual Savings
```

```text
Undistributed Savings =
Final Savings - Savings Distributed
```

Define and test every formula explicitly.

---

# 27. Important Accounting Consideration

Avoid double-counting.

For example, if a Housing Allowance is already included in the salary/allowance calculation, it must not also be counted as separate "Other Income".

Likewise, an expense recorded under a category must not be counted twice simply because it also appears as a bank transaction.

Separate:

- Financial event
- Budget allocation
- Actual expense
- Account transaction

Use relationships/references between them where appropriate.

---

# 28. Suggested Database Entities

At minimum, consider:

```text
User
FinancialPeriod
Salary
Allowance
Income
Expense
DistributionRule
DistributionCategory
DistributionItem
Savings
SavingsItem
BankAccount
BankTransaction
SavingsAllocation
MonthlyFinancialSummary
Attachment
AuditLog
```

The final schema may be improved by the architect.

---

# 29. Suggested Backend Modules

```text
backend/
├── app/
│   ├── auth/
│   ├── users/
│   ├── financial_periods/
│   ├── salary/
│   ├── allowances/
│   ├── income/
│   ├── expenses/
│   ├── distribution/
│   ├── savings/
│   ├── banks/
│   ├── transactions/
│   ├── reports/
│   ├── analytics/
│   ├── attachments/
│   ├── audit/
│   └── common/
│
├── tests/
├── alembic/
├── requirements/
└── Dockerfile
```

Use clear separation between:

- API routes/controllers
- Schemas/DTOs
- Business services
- Data access/repositories
- Domain calculations
- Database models

---

# 30. Financial Calculation Engine

Keep financial calculations in a dedicated, highly tested domain/service layer.

Example conceptual structure:

```text
financial_engine/
├── income_calculator
├── distribution_calculator
├── expense_calculator
├── savings_calculator
├── bank_allocation_calculator
└── monthly_summary_calculator
```

Do not put critical financial calculations directly inside frontend components.

The backend is the source of truth.

---

# 31. API Design

Create REST endpoints with consistent naming.

Examples:

```text
GET    /api/v1/financial-periods
POST   /api/v1/financial-periods

GET    /api/v1/financial-periods/{id}/summary

GET    /api/v1/salaries
POST   /api/v1/salaries

GET    /api/v1/allowances
POST   /api/v1/allowances

GET    /api/v1/income
POST   /api/v1/income

GET    /api/v1/expenses
POST   /api/v1/expenses

GET    /api/v1/distribution-rules
POST   /api/v1/distribution-rules

GET    /api/v1/distributions/{period_id}

GET    /api/v1/savings
POST   /api/v1/savings

GET    /api/v1/bank-accounts
POST   /api/v1/bank-accounts

GET    /api/v1/bank-transactions
POST   /api/v1/bank-transactions
```

Use pagination, filtering, sorting, validation, and consistent error responses.

---

# 32. Frontend Pages

At minimum:

```text
/
 /login
 /register
 /dashboard
 /financial-periods
 /financial-periods/[id]
 /salary
 /allowances
 /income
 /expenses
 /distribution
 /savings
 /bank-accounts
 /transactions
 /reports
 /analytics
 /settings
```

Use reusable components.

Do not duplicate forms and calculation UI unnecessarily.

---

# 33. UX Principles

The application must be understandable to someone without accounting knowledge.

Prefer:

```text
Money Available
Remaining
Spent
Saved
Planned
Actual
```

over unnecessarily technical financial terminology.

The dashboard should answer the user's main questions immediately.

Forms should:

- Validate immediately
- Explain errors
- Show calculated totals
- Prevent invalid financial states
- Confirm destructive actions

The application must be responsive and mobile-friendly even before the Flutter app is built.

---

# 34. Security

Financial information is sensitive.

Implement:

- Secure authentication
- Authorization
- User data isolation
- Server-side validation
- Secure password handling
- Rate limiting where appropriate
- CSRF protection where applicable
- Secure HTTP headers
- Input validation
- SQL injection protection through ORM/parameterized queries
- Secure file uploads
- File type and size validation
- Audit logging
- Secret management
- No secrets committed to Git
- Production HTTPS

A user must never be able to access another user's financial records by changing an ID in a request.

---

# 35. Privacy

Only collect data that is needed.

Bank identifiers should be masked.

Do not log:

- Passwords
- Authentication tokens
- Full bank account numbers
- Sensitive financial information unnecessarily

Be careful with error reporting and third-party monitoring.

---

# 36. Auditability

Important financial changes should be auditable.

Track:

- Who made the change
- What changed
- Previous value
- New value
- Timestamp
- Related record

Especially audit:

- Income
- Expenses
- Distribution rules
- Savings
- Bank transactions
- Transfers
- Financial-period closing/reopening

---

# 37. Financial Period Closing

Implement a concept of:

```text
Open
Closed
```

A closed financial period should not be casually modified.

If editing closed periods is supported:

- Require explicit action
- Record an audit event
- Recalculate affected summaries
- Clearly indicate the period was modified

Do not silently alter historical financial results.

---

# 38. Edge Cases

Explicitly design and test:

1. Salary with no allowances
2. Allowances with no other income
3. Other income with no salary
4. Multiple income payments in one month
5. Multiple allowances
6. No income
7. Zero income
8. Zero expenses
9. Category with no items
10. Entire category unused
11. Category overspending
12. Savings category fully unused
13. Manual savings without automatic savings
14. Partial bank allocation
15. Attempted bank over-allocation
16. Multiple bank accounts
17. Transfers between accounts
18. Deleted income
19. Edited income
20. Edited expense
21. Changed distribution rule
22. Additional income after distribution
23. Recurring income
24. Recurring expenses
25. Different currencies in future
26. Closed financial period
27. Duplicate transactions
28. Decimal rounding
29. Very large amounts
30. Concurrent updates
31. Failed bank allocation
32. Deleted/inactive bank account
33. Account balance mismatch
34. Negative category remaining
35. Negative final savings

Document how every important edge case behaves.

---

# 39. Testing Strategy

Tests are mandatory.

## Unit Tests

Test every core financial formula.

Examples:

```text
salary + allowances
total income
percentage distribution
category remaining
automatic savings
final savings
bank allocation
undistributed savings
```

Include rounding tests.

## Integration Tests

Test:

```text
API
 ↓
Business Logic
 ↓
Database
```

## End-to-End Tests

Use Playwright to test complete user flows.

Example:

```text
Register
 ↓
Create September period
 ↓
Enter salary
 ↓
Add allowances
 ↓
Add other income
 ↓
Create distribution rule
 ↓
Add expenses
 ↓
Review remaining allocations
 ↓
Review final savings
 ↓
Add bank accounts
 ↓
Allocate savings
 ↓
Review monthly summary
```

## Security Tests

Test:

- Unauthorized access
- Cross-user access
- Invalid IDs
- Malicious input
- File upload abuse
- Authentication failures
- Rate limits where applicable

---

# 40. Example Complete Scenario

Input:

```text
Net Salary = D10,000

Housing Allowance = D2,000
Transport Allowance = D1,000

Per Diem = D500
Freelance = D500
```

Total:

```text
Salary income = D13,000
Other income  = D1,000

Total Income = D14,000
```

Distribution:

```text
Needs     50% = D7,000
Savings   30% = D4,200
Wants     20% = D2,800
```

Actual category spending:

```text
Needs:
D6,500 used
D500 remaining

Savings:
D3,900 used
D300 remaining

Wants:
D2,300 used
D500 remaining
```

Automatic savings:

```text
D500 + D300 + D500
= D1,300
```

Then the user can distribute:

```text
Trust Bank = D700
GTBank     = D400
Emergency  = D200
```

Result:

```text
Final Savings        D1,300
Distributed          D1,300
Undistributed        D0
```

The application must be able to reproduce this calculation exactly.

---

# 41. Recurring Records

Support recurring records where appropriate.

Examples:

- Monthly salary
- Monthly housing allowance
- Monthly rent
- Monthly internet bill

Recurring records should generate financial-period records rather than blindly sharing one mutable record across all months.

A change in October should not rewrite September's historical record.

---

# 42. Reports

Provide:

- Monthly financial summary
- Income report
- Expense report
- Distribution report
- Savings report
- Bank/account report
- Planned vs actual report
- Historical comparison

Allow export where appropriate:

- PDF
- CSV
- Excel

Reports must use backend-calculated financial data.

---

# 43. Notifications

Future-ready architecture should support notifications for:

- Salary received
- Budget nearing limit
- Category overspent
- Savings target reached
- Monthly period closing
- Recurring payment due

Do not make notifications a core dependency of the financial engine.

---

# 44. Performance

Design for:

- Fast dashboard loading
- Pagination on large lists
- Efficient database queries
- Appropriate indexes
- Avoiding N+1 queries
- Caching only where beneficial
- Background report generation when expensive

Do not prematurely optimize.

---

# 45. Database Design Requirements

Use foreign keys and constraints.

Examples:

- Financial records belong to a user.
- Financial records belong to a financial period where applicable.
- Distribution categories belong to distribution rules.
- Distribution items belong to categories.
- Bank transactions belong to accounts.
- Savings allocations reference savings and destinations.

Use indexes for common queries.

Use database constraints for important invariants where possible.

---

# 46. Data Integrity

The backend must be the source of truth.

Never trust calculated values sent by the frontend.

For example, the frontend may display:

```text
Total Income = D14,000
```

but the backend should calculate/verify this from persisted records.

Do not allow the client to simply submit:

```text
total_income = 14000
```

and treat it as authoritative.

---

# 47. Implementation Process

Follow this sequence.

## Phase 1 — Discovery

Before coding:

1. Analyze requirements.
2. Identify ambiguities.
3. Identify financial rules.
4. Identify edge cases.
5. Produce architecture.
6. Produce database ERD.
7. Produce API specification.
8. Produce frontend route structure.

## Phase 2 — Foundation

Implement:

- Project structure
- Docker
- PostgreSQL
- FastAPI
- SQLAlchemy
- Alembic
- Authentication
- User model
- CI/CD
- Testing foundation

## Phase 3 — Financial Core

Implement:

- Financial periods
- Salary
- Allowances
- Income
- Expenses
- Distribution rules
- Distribution engine
- Savings engine

## Phase 4 — Accounts

Implement:

- Bank accounts
- Transactions
- Savings allocations
- Account balances

## Phase 5 — Web UI

Implement:

- Dashboard
- Financial period UI
- Income UI
- Expense UI
- Distribution UI
- Savings UI
- Bank UI
- Reports

## Phase 6 — Testing

Complete:

- Unit tests
- Integration tests
- E2E tests
- Security tests
- Calculation tests

## Phase 7 — Mobile

Build Flutter application against the existing API.

## Phase 8 — Production

Implement:

- Production Docker configuration
- HTTPS
- Backups
- Monitoring
- Logging
- CI/CD
- Deployment documentation

---

# 48. Developer Rules

1. Do not invent financial behavior when the specification is ambiguous.
2. If a business rule materially affects financial calculations, identify it before implementation.
3. Keep financial calculations centralized and testable.
4. Do not duplicate core financial logic in the frontend.
5. Never use floating-point arithmetic for money.
6. Never trust client-provided totals.
7. Never silently overwrite historical financial records.
8. Do not start with microservices.
9. Keep the system modular.
10. Write tests for every important financial calculation.
11. Use migrations for database changes.
12. Keep secrets out of source control.
13. Follow secure coding practices.
14. Prefer simple solutions over unnecessary complexity.
15. Document important architectural decisions.
16. Use meaningful names.
17. Keep API responses consistent.
18. Handle errors explicitly.
19. Make the UI responsive.
20. Build for maintainability, not just a demo.

---

# 49. Definition of Done

The application is not considered complete when the UI merely displays forms.

A feature is complete when:

- Database model exists
- API exists
- Validation exists
- Business logic exists
- UI exists
- Error handling exists
- Authorization exists
- Tests exist
- Documentation exists
- Edge cases are addressed

For financial features, the calculation must be independently tested.

---

# 50. Final Product Goal

Build a polished personal finance application where a user can go from:

```text
Salary
  +
Allowances
  +
Other Income
       ↓
Total Monthly Income
       ↓
Distribution Rule
       ↓
Category Allocations
       ↓
Expenses / Category Items
       ↓
Remaining Amounts
       ↓
Automatic Savings
       +
Manual Savings
       ↓
Final Savings
       ↓
Bank / Account Allocation
       ↓
Monthly Financial Summary
       ↓
Historical Analytics
```

The application should feel like a reliable personal financial assistant.

The system must prioritize:

- Accuracy
- Transparency
- Security
- Auditability
- Simplicity
- Maintainability
- Excellent UX
- Correct financial calculations

Start by producing the architecture, ERD/database schema, domain model, API contract, user flows, and implementation plan before writing the production code.
