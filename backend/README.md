# Agro Future – Backend

FastAPI backend for the Farmer Carbon Credit Marketplace (Epic 1: Farmer Account Onboarding).

## Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2 (async) |
| Database | PostgreSQL (via asyncpg) |
| Migrations | Alembic |
| Auth | python-jose (JWT) + passlib (bcrypt) |
| Validation | Pydantic v2 |
| Tests | pytest + httpx + aiosqlite |

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt   # test dependencies
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

### 3. Create the database

```bash
createdb agro_future          # or use psql / pgAdmin
```

### 4. Run Alembic migrations

```bash
alembic upgrade head
```

This creates the following tables in PostgreSQL:

| Table | Description |
|---|---|
| `users` | Central identity record (id, email, role, status, …) |
| `supplier_profiles` | Farm metadata + payout details (FK → users.id) |

PostgreSQL ENUM types created: `role_enum`, `user_status_enum`, `ownership_status_enum`.

### 5. Start the API server

```bash
uvicorn app.main:app --reload --port 8000
```

Interactive docs: http://localhost:8000/api/docs

## API Endpoints (v1)

All endpoints are prefixed with `/api/v1`.

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | Public | Register a new supplier account |
| `POST` | `/auth/verify-email` | Public | Verify email with token |
| `POST` | `/auth/login` | Public | Log in, receive bearer token |

### Supplier

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/supplier/profile` | ****** | Fetch own profile |
| `POST` | `/supplier/profile` | ****** | Create / update profile |

## Running tests

Tests use an in-memory SQLite database (no PostgreSQL needed):

```bash
cd backend
pytest -v
```

## Database migration reference

```bash
# Apply all pending migrations
alembic upgrade head

# Roll back the last migration
alembic downgrade -1

# Auto-generate a new migration from model changes
alembic revision --autogenerate -m "describe change"

# Show current migration state
alembic current
```
