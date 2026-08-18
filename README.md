# AI-Powered Agentic Finance and Tax Assistant

An AI-powered agentic finance and tax assistant for England Income Tax estimation (Tax Year 2026/27) built with FastAPI, LangGraph, PostgreSQL, and Groq.

## Features

- **User Authentication**: JWT Bearer tokens with OWASP-compliant PBKDF2 password hashing
- **Financial Account Management**: Create and list user-owned GBP accounts
- **CSV Transaction Import**: Parse, validate, deduplicate, and import UK bank CSV files
- **AI Transaction Categorization**: Deterministic merchant rules + Groq LLM categorization via LangGraph
- **Budget Tracking**: Set spending budgets by category with real-time spending analysis and status alerts
- **Income Tax Estimation**: Deterministic England Income Tax (2026/27) engine with Personal Allowance taper
- **PDF Financial Reports**: Generate monthly summary reports with income, expense, and category breakdowns
- **Transaction Filtering**: Filter by date range, category, type, and amount range
- **Audit Logging**: Append-only audit trail for sensitive actions
- **Data Isolation**: All data strictly scoped to the authenticated user

## Architecture Overview

The system strictly enforces layered separation of concerns and user isolation:

```text
Client (HTTP / JWT Bearer)
   |
   v
FastAPI Routes (app/api/routes/)
   |  (JWT Authentication -> extracts user_id, validates request schema)
   v
Services & Tools (app/services/, app/tools/)
   |  (AuthService, AccountService, CsvImportService, BudgetService, ReportService)
   v
Repositories (app/db/repositories/)
   |  (All SQL queries strictly scoped to authenticated user_id)
   v
PostgreSQL Database
```

## Technology Stack

| Component | Technology |
| :--- | :--- |
| Language | Python 3.12 |
| Web Framework | FastAPI |
| Agent Framework | LangGraph |
| LLM Provider | Groq (provider-neutral interface) |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| PDF Generation | ReportLab |
| Authentication | JWT HS256 (hand-rolled) |
| Password Hashing | PBKDF2-HMAC-SHA256 (600K iterations) |

## Security & Authentication

- **Authentication**: JWT Bearer authentication (RFC 7519 HS256).
- **Password Storage**: OWASP-compliant PBKDF2-HMAC-SHA256 with 600,000 iterations and unique 16-byte random salts. Plaintext passwords and `password_hash` are never exposed in responses or logs.
- **Data Scoping**: User identity is derived strictly from verified JWT tokens. `user_id` is never accepted from request bodies, query parameters, path variables, or CSV headers.
- **Zero Raw Error Leakage**: Global exception handlers sanitize database and internal errors.

## API Endpoints

### Authentication
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Register a new user (`email`, `password`, `full_name`) | No |
| `POST` | `/auth/login` | Authenticate with credentials and receive a JWT Bearer token | No |

### Financial Accounts
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/accounts` | Create a new GBP account (`account_name`, `account_type`, `currency_code`) | Yes (JWT) |
| `GET` | `/accounts` | List all accounts owned by the authenticated user | Yes (JWT) |

### Transactions & Categorization
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/accounts/{account_id}/transactions/import` | Upload UK-bank CSV file to import and deduplicate transactions | Yes (JWT) |
| `POST` | `/accounts/{account_id}/transactions/categorize` | Trigger Transaction Agent (deterministic rules + Groq) | Yes (JWT) |
| `GET` | `/accounts/{account_id}/transactions` | List transactions with filters (`start_date`, `end_date`, `category`, `transaction_type`, `min_amount`, `max_amount`, `limit`, `offset`) | Yes (JWT) |

### Budgets
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/budgets` | Create a spending budget for a category and date range | Yes (JWT) |
| `GET` | `/budgets` | List all budgets with spending analysis | Yes (JWT) |
| `GET` | `/budgets/{budget_id}` | Get a specific budget with spending analysis | Yes (JWT) |
| `PATCH` | `/budgets/{budget_id}` | Update a budget's amount or date range | Yes (JWT) |
| `DELETE` | `/budgets/{budget_id}` | Delete a budget | Yes (JWT) |

### Tax
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/tax/estimate` | Estimate England Income Tax for the authenticated user | Yes (JWT) |
| `GET` | `/tax/calculations` | List all tax calculations for the authenticated user | Yes (JWT) |
| `GET` | `/tax/calculations/{id}` | Get a specific tax calculation by ID | Yes (JWT) |

### Reports
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/reports/generate` | Generate a PDF financial summary report for a given period | Yes (JWT) |
| `GET` | `/reports` | List all generated reports for the authenticated user | Yes (JWT) |
| `GET` | `/reports/{report_id}` | Get a specific report metadata by ID | Yes (JWT) |

### System Health
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Application health check endpoint | No |

## England Income Tax Engine (Tax Year 2026/27)

A 100% deterministic Python calculation engine for England Income Tax estimation.

- **Official Source of Truth**: [GOV.UK Income Tax rates and allowances](https://www.gov.uk/income-tax-rates)
- **Tax Year**: `2026/27` (6 April 2026 - 5 April 2027)
- **Jurisdiction**: United Kingdom: England
- **Rules Version**: `2026_27_england_v1`
- **Arithmetic Precision**: Fixed 2-decimal precision with `Decimal` and `ROUND_HALF_UP` (zero float operations).

### Tax Rates & Allowances Implemented
- **Personal Allowance**: 12,570.00 (tax-free allowance).
- **Personal Allowance Taper**: 1 reduction for every 2 of income above 100,000.00 (reaches 0.00 at 125,140.00).
- **Basic Rate (20%)**: 0.01 to 37,700.00 of taxable income.
- **Higher Rate (40%)**: 37,700.01 to 125,140.00 of taxable income.
- **Additional Rate (45%)**: Taxable income above 125,140.00.

### Assumptions & Limitations
- **Estimation Only**: Calculations are automated mathematical estimates and do **not** constitute an official HMRC tax determination, legal assessment, or binding advice.
- **Scope Limitations**: Excludes National Insurance Contributions (NICs), Scottish/Welsh devolved tax bands, Northern Ireland, VAT, Capital Gains Tax, Dividend Allowance, Personal Savings Allowance, High Income Child Benefit Charge, and direct HMRC tax submission.

## Budget Status Thresholds

| Status | Condition | Description |
| :--- | :--- | :--- |
| `under_budget` | spending < 80% of budget | Spending is well within budget |
| `near_limit` | spending between 80% and 100% of budget | Spending is approaching the budget limit |
| `over_budget` | spending > 100% of budget | Spending has exceeded the budget |

## Transaction Categorization

The Transaction Agent uses a two-stage approach:

1. **Deterministic Rules**: 9 regex-based merchant rules (Tesco, Sainsbury's, Asda, Morrisons -> Food; TfL, Uber -> Transport; Octopus Energy -> Utilities; Netflix -> Subscriptions; Payroll -> Salary)
2. **LLM Fallback**: Groq LLM categorizes transactions that don't match deterministic rules, validated against approved categories with confidence thresholds

### Approved Categories (15)
**Income**: Salary, Freelance Income, Other Income
**Expense**: Housing, Food, Transport, Utilities, Healthcare, Shopping, Entertainment, Subscriptions, Education, Insurance, Personal Care, Other Expense

## Setup & Running Locally

### Option 1: Docker Compose (Recommended)

```bash
# Copy environment file
cp .env.example .env
# Edit .env with your values (GROQ_API_KEY, JWT_SECRET_KEY)

# Start PostgreSQL and the application
docker compose up -d

# Run migrations
docker compose exec app alembic upgrade head

# Seed categories
docker compose exec app python scripts/seed_categories.py

# API docs at http://localhost:8000/docs
```

### Option 2: Manual Setup

#### 1. Environment Configuration
```bash
cp .env.example .env
```
Ensure `DATABASE_URL`, `JWT_SECRET_KEY`, and `GROQ_API_KEY` are populated.

#### 2. Database Migrations & Category Seeding
```powershell
# Run Alembic migrations
alembic upgrade head

# Seed the 15 approved transaction categories
python scripts/seed_categories.py
```

#### 3. Run the FastAPI Dev Server
```powershell
uvicorn app.main:app --reload
```
Interactive API docs are available at `http://127.0.0.1:8000/docs`.

#### 4. Run Automated Tests
```powershell
$env:PYTHONPATH="."; .\.venv\Scripts\python -m pytest -q
```

## Environment Variables

| Variable | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Yes | - | Secret key for JWT signing (min 32 chars) |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | No | `1440` | Token expiry in minutes |
| `GROQ_API_KEY` | Yes | - | Groq API key for LLM categorization |
| `GROQ_MODEL` | No | `openai/gpt-oss-120b` | Groq model identifier |
| `TRANSACTION_AGENT_BATCH_SIZE` | No | `10` | Transactions per LLM batch |
| `TRANSACTION_AGENT_CONFIDENCE_THRESHOLD` | No | `0.85` | Minimum LLM confidence to auto-assign |
| `TRANSACTION_AGENT_MAX_BATCHES_PER_RUN` | No | `10` | Max batches per categorization run |

## Project Structure

```
app/
  main.py                 # FastAPI application entry point
  config.py               # Pydantic Settings from environment
  agents/                 # LangGraph agents and workflows
  api/routes/             # FastAPI routers (auth, accounts, budgets, tax, reports)
  db/models/              # SQLAlchemy ORM models
  db/repositories/        # Database access layer (user-scoped)
  db/migrations/          # Alembic migrations
  schemas/                # Pydantic request/response schemas
  security/               # JWT and password hashing
  services/               # Business logic and orchestration
  tax/                    # Deterministic tax engine (UK/England/2026-27)
  tools/                  # Controlled entry points for agents
tests/
  unit/                   # Unit and integration tests
  api/                    # API endpoint tests
```

## License

This project is for educational and demonstration purposes.
