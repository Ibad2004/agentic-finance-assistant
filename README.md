# AI-Powered Agentic Finance and Tax Assistant

An AI-powered agentic finance and tax assistant for England Income Tax estimation (Tax Year 2026/27) built with FastAPI, LangGraph, PostgreSQL, and Groq.

## Architecture Overview

The system strictly enforces layered separation of concerns and user isolation:

```text
Client (HTTP / JWT Bearer)
   │
   ▼
FastAPI Routes (app/api/routes/)
   │  (JWT Authentication -> extracts user_id, validates request schema)
   ▼
Services & Tools (app/services/, app/tools/)
   │  (AuthService, AccountService, CsvImportService, TransactionAgent)
   ▼
Repositories (app/db/repositories/)
   │  (All SQL queries strictly scoped to authenticated user_id)
   ▼
PostgreSQL Database
```

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
| `GET` | `/accounts/{account_id}/transactions` | List transactions with safe fields (`limit`, `offset`) | Yes (JWT) |

### System Health
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Application health check endpoint | No |

## Setup & Running Locally

### 1. Environment Configuration
Copy the example environment file and configure variables:
```bash
cp .env.example .env
```
Ensure `DATABASE_URL`, `JWT_SECRET_KEY`, and `GROQ_API_KEY` are populated.

### 2. Database Migrations & Category Seeding
```powershell
# Run Alembic migrations
alembic upgrade head

# Seed the 15 approved transaction categories
python scripts/seed_categories.py
```

### 3. Run the FastAPI Dev Server
```powershell
uvicorn app.main:app --reload
```
Interactive API docs are available at `http://127.0.0.1:8000/docs`.

### 4. Run Automated Tests
```powershell
$env:PYTHONPATH="."; .\.venv\Scripts\python -m pytest -q
```
