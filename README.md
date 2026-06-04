# FastAdmin

FastAdmin is a Django-inspired full-stack framework for Python that keeps the productive parts of Django while using a more decoupled architecture.

Instead of tightly coupling templates, admin, routing, and backend logic into one runtime, FastAdmin separates concerns clearly:

- `api/` contains the FastAPI backend, ORM, auth, and CLI tools.
- `admin/` is a dedicated Next.js admin application.
- your public frontend can live separately and talk to the API on its own terms.

The goal is not to clone Django line-for-line. The goal is to offer a familiar app-oriented workflow with looser coupling, clearer boundaries, and practical engineering defaults.

## Why FastAdmin

- Django-style apps for organizing backend features
- a custom lightweight ORM for fast iteration with SQLite
- a standalone admin app instead of a backend-rendered admin
- JWT-based authentication out of the box with httpOnly cookies
- Swagger/OpenAPI docs for backend endpoints (superuser-protected)
- Python on the backend, TypeScript on the frontend

## Architecture at a Glance

| Directory | Responsibility |
| --- | --- |
| `api/` | FastAPI backend, auth, ORM, CLI commands, database access |
| `admin/` | Next.js admin interface for managing registered models |
| `tutorials/` | Guides, architecture notes, and implementation walkthroughs |

Default local ports:

- API: `http://localhost:8000`
- Admin: `http://localhost:7000`
- Public app: `http://localhost:3000` if you build one alongside this repo

## How the Admin Fits With Your App

FastAdmin is intentionally split into separate layers:

- `api/` is the shared backend
- `admin/` is the internal management UI
- your public app is a separate frontend for end users

This means the admin is not meant to be embedded into the user-facing app.

Instead, the intended shape is:

```text
Public App  ----\
                 >---- API ---- Database
Admin Panel ----/
```

In practice:

- admins and staff use `admin/`
- end users use your own frontend
- both frontends talk to the same backend API

## Day-One Workflow

If you want the fastest path to something working, use this order:

1. activate the Python virtual environment in `api/`
2. create a backend app by adding `api/apps/myapp/` directory
3. define your model in `api/apps/myapp/models.py`
4. add routes in `api/apps/myapp/routers.py`
5. restart the API — apps are auto-discovered on startup
6. log into the admin and manage the model there
7. fetch the same data from your public frontend

The generated app includes:

- `models.py` — SQLAlchemy model with `@register_admin` decorator
- `routers.py` — FastAPI router with endpoints
- `__init__.py` — package marker

## Quick Start

### Prerequisites

- Python `3.10+`
- Node.js `20.x` LTS (for the admin frontend)

### Backend Setup

```bash
cd api
python -m venv env
.\env\Scripts\activate   # Windows
source env/bin/activate  # macOS/Linux

pip install -r requirements.txt
```

Create `api/.env`:

```env
SECRET_KEY=your_random_secret_key
JWT_SECRET=your_random_jwt_secret
ENVIRONMENT=development
DEBUG=True
DB_ENGINE=sqlite
DB_PATH=./db.sqlite3
```

Start the API:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### Create a Superuser

```bash
cd api
.\env\Scripts\activate
$env:PYTHONPATH = "."; python cli/create_user.py --username admin --email admin@example.com --password admin123 --superuser --staff
```

### Frontend Setup

```bash
cd admin
npm install
npm run dev
```

Admin panel is available at `http://localhost:7000`.

## Core Workflow

### Register a Model

Create your model in `api/apps/<appName>/models.py` and decorate it with `@register_admin`. Because FastAdmin uses an Auto-Discovery Engine, placing it in the correct folder is enough.

Example:

```python
from sqlalchemy import Column, String, Boolean
from common.orm import Model
from core.registry import register_admin

@register_admin(
    app_name="Blog",
    display_name="Posts",
    list_display=["id", "title", "is_published"]
)
class Post(Model):
    __tablename__ = "posts"

    title = Column(String(200))
    is_published = Column(Boolean, default=False)
```

Create routes in `api/apps/<appName>/routers.py`:

```python
from fastapi import APIRouter
router = APIRouter(prefix="/api/blog", tags=["Blog"])

@router.get("/posts")
async def list_posts():
    ...
```

Restart the API — everything is auto-discovered!

### Database Changes

SQLAlchemy `create_all` creates new tables but does not add columns to existing tables.

For new models: just restart the API.

For columns added to existing tables: run explicit `ALTER TABLE` SQL against `api/db.sqlite3`.

Full details in [Database and Migrations](./tutorials/07_DATABASE_MIGRATIONS.md).

## Auth Endpoints

The backend ships with these auth endpoints:

- `POST /auth/register`
- `POST /auth/verify-email`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`
- `POST /auth/change-password`
- `GET /auth/me`
- `POST /auth/logout`

Cookie-based JWT: `accessToken` (1 day) and `refreshToken` (7 days), both httpOnly.

## Philosophy

FastAdmin is built around a few engineering principles:

- loose coupling over framework magic
- explicit boundaries between backend, admin, and public frontend
- app-level modularity for feature development
- simple defaults for solo builders and small teams
- enough convention to move quickly, without forcing every layer into one architecture

If you come from Django, the structure will feel familiar. If you come from Node.js, the Python boundaries should feel easy to control.

## Production Database Reality

FastAdmin is currently SQLite-first.

What is supported today:

- SQLite in development
- SQLite in production
- changing the SQLite file location with `DB_PATH`

PostgreSQL support requires changing the SQLAlchemy connection string and engine configuration — it is an engineering task, not an env-var-only switch.

## Documentation

The main guides live in [`tutorials/README.md`](./tutorials/README.md).

- [Architecture](./tutorials/01_ARCHITECTURE.md)
- [First Feature Guide](./tutorials/03_FIRST_FEATURE_GUIDE.md)
- [Model Registration Guide](./tutorials/05_MODEL_REGISTRATION_GUIDE.md)
- [User and Authentication Guide](./tutorials/06_USER_AND_AUTH_GUIDE.md)
- [Database and Migrations](./tutorials/07_DATABASE_MIGRATIONS.md)
- [Email Configuration](./tutorials/08_EMAIL_CONFIGURATION.md)
- [Port Configuration](./tutorials/09_PORT_CONFIGURATION.md)
- [Production Deployment](./tutorials/16_PRODUCTION_DEPLOYMENT.md)

## Default Service URLs

- Admin UI: `http://localhost:7000`
- Swagger docs: `http://localhost:8000/docs` (superuser login required)
- API base URL: `http://localhost:8000`
