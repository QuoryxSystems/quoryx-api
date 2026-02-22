# Quoryx

Intercompany reconciliation platform. Connects to Xero and QuickBooks via OAuth 2.0, ingests transactions, and automatically matches corresponding entries across entities.

---

## Prerequisites

- Python 3.11+
- PostgreSQL 14+

---

## Setup

### 1. Clone and create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Description |
|---|---|
| `APP_SECRET_KEY` | Random secret used for token hashing |
| `DATABASE_URL` | PostgreSQL connection string |
| `XERO_CLIENT_ID` | From [Xero Developer Portal](https://developer.xero.com) |
| `XERO_CLIENT_SECRET` | From Xero Developer Portal |
| `QB_CLIENT_ID` | From [Intuit Developer Portal](https://developer.intuit.com) |
| `QB_CLIENT_SECRET` | From Intuit Developer Portal |

### 3. Create the database

```bash
createdb quoryx
```

### 4. Run database migrations

The models use SQLAlchemy. To create tables on first run:

```python
# one-off bootstrap (development only)
python -c "
from app.models.database import engine
from app.models import transaction
transaction.Base.metadata.create_all(bind=engine)
"
```

For production, use Alembic migrations:

```bash
alembic upgrade head
```

### 5. Start the server

```bash
uvicorn app.main:app --reload
```

API docs are available at <http://localhost:8000/docs> in development mode.

---

## API Overview

All routes are prefixed with `/api/v1`.

### Health

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/health/db` | Database connectivity check |

### Auth

| Method | Path | Description |
|---|---|---|
| GET | `/auth/xero` | Start Xero OAuth flow |
| GET | `/auth/xero/callback` | Xero OAuth callback |
| GET | `/auth/quickbooks` | Start QuickBooks OAuth flow |
| GET | `/auth/quickbooks/callback` | QuickBooks OAuth callback |

### Transactions

| Method | Path | Description |
|---|---|---|
| POST | `/transactions/` | Ingest a transaction |
| GET | `/transactions/` | List transactions (filter by `status`, `provider`) |
| GET | `/transactions/{id}` | Get a single transaction |
| POST | `/transactions/{id}/reconcile` | Manually trigger reconciliation |

---

## Project Structure

```
app/
  api/          # Route handlers (health, auth, transactions)
  core/         # Config, security utilities
  models/       # SQLAlchemy models and database session
  services/     # Business logic (OAuth, reconciliation)
  main.py       # FastAPI app and middleware
requirements.txt
.env.example
```

---

## Reconciliation Logic

When a transaction is ingested it is immediately compared against pending transactions from the opposite provider. A match is confirmed when:

- Amounts agree within **$0.01**
- Currency codes are identical
- Transaction dates are within **3 days** of each other

Both transactions are then marked `matched` and linked via `matched_transaction_id`. Unmatched transactions remain `pending` until manually reconciled or a counterpart arrives.
