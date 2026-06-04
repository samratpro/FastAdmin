# Architecture

FastAdmin is a Django-inspired framework with a deliberately more decoupled structure.

The backend, admin UI, and public frontend are not collapsed into one layer. That separation is intentional.

## High-Level Shape

```text
FastAdmin/
├── api/         FastAPI backend, SQLAlchemy ORM, auth, Alembic migrations
├── admin/       Next.js admin application
└── tutorials/   Documentation
```

There is no built-in public `app/` directory in this repo. You are expected to build your user-facing frontend separately — either in another folder or another repo — and point it at the API.

## The Easiest Way to Think About FastAdmin

FastAdmin is not one giant full-stack runtime.

It is three explicit pieces:

- a Python/FastAPI backend in `api/`
- a Next.js admin UI in `admin/`
- your own public frontend (outside this repo)

Both frontends use the same backend.

## Why This Structure

This project is built around a few boundary decisions:

- backend logic belongs in `api/`
- admin UX belongs in `admin/`
- public product UX should not share admin assumptions
- apps should organize domain features, not just files

This makes the project feel familiar to Django users while staying explicit and composable.

## Backend: `api/`

The `api/` package is the core runtime. It contains:

- FastAPI server bootstrapping (`main.py`)
- SQLAlchemy async ORM with custom `Model` base class (`common/orm.py`)
- built-in authentication and authorization (`apps/auth/`)
- model registration and admin metadata (`core/registry.py`)
- Alembic migration system (`alembic/`, `alembic.ini`)

Important locations:

```
api/
├── main.py              ← API entry point, startup, router auto-discovery
├── apps/                ← domain feature apps
│   ├── auth/            ← users, groups, permissions
│   ├── blog/            ← blog categories and posts
│   ├── seo/             ← SEO pages, robots, redirects, sitemap
│   ├── settings/        ← site settings (logo, favicon, title)
│   └── backup/          ← database backup and Google Drive
├── core/
│   ├── config.py        ← runtime configuration (pydantic-settings)
│   ├── database.py      ← async SQLAlchemy engine and session
│   ├── dependencies.py  ← FastAPI auth dependencies
│   ├── registry.py      ← MODEL_REGISTRY and @register_admin decorator
│   └── security.py      ← JWT encode/decode, password hashing
├── common/
│   └── orm.py           ← Model base class with .objects() query API
├── alembic/             ← Alembic migration environment
│   ├── env.py
│   └── versions/        ← versioned migration files
└── alembic.ini          ← Alembic config
```

## Admin: `admin/`

The admin is a separate Next.js application, not a backend-rendered admin template system.

That choice gives you:

- a clean UI boundary
- frontend flexibility without touching the API runtime
- the ability to evolve admin UX independently

The admin talks to the backend over HTTP using `NEXT_PUBLIC_API_URL`, which defaults to `http://localhost:8000`.

Your public app should do the same.

## App-Oriented Backend Design

Backend features are grouped as apps under `api/apps/`.

An app typically owns:

- `models.py` — SQLAlchemy model definitions
- `routers.py` — FastAPI route handlers
- optional helpers or schemas

This is conceptually similar to Django apps, but the coupling is lighter. Routes, models, and admin metadata remain explicit.

## What Is Automatic vs Explicit

Some things in FastAdmin are automatic after you wire them in, and some things are always explicit.

Automatic:

- models inside `api/apps/*/models.py` are auto-imported on startup
- routers inside `api/apps/*/routers.py` are auto-registered to the FastAPI instance
- models decorated with `@register_admin(...)` appear in the admin UI
- default CRUD permissions are created for every registered model on startup

Still explicit:

- writing migration files when you change a model
- deciding which routes are public, staff-only, or authenticated
- building your public frontend

## Model Registration

Models are discovered automatically when placed in the correct location. They become active when:

1. the model file is at `api/apps/<app-name>/models.py`
2. the model extends `Model` from `common.orm`
3. the model uses `@register_admin(...)` to appear in the admin UI

You never have to edit `main.py` to register models or routers.

## Request Flow

Typical flow for an admin interaction:

1. user opens the Next.js admin at port `7000`
2. admin calls the API at port `8000`
3. FastAPI routes handle the request
4. SQLAlchemy async ORM reads/writes the database
5. response goes back to the admin

Typical flow for a public app interaction:

1. user opens your frontend at port `3000` or your production domain
2. frontend calls the API
3. FastAPI routes handle the request
4. database is read/written
5. response goes back to your frontend

## Local Ports

Default local development ports:

- API: `8000`
- Admin: `7000`
- Public app: `3000` (if you create one)

Keeping the admin off port `3000` leaves the default frontend port free for the user-facing app.

## Typical Day-One Workflow

When building a new feature:

1. create `api/apps/<name>/models.py` — define your SQLAlchemy model
2. create `api/apps/<name>/routers.py` — define your FastAPI routes
3. add the model import to `alembic/env.py`
4. run `alembic revision --autogenerate -m "..."` and `alembic upgrade head`
5. restart the API (auto-discovered)
6. manage the model in the admin
7. consume the routes from your public app

## Database Strategy

The backend supports SQLite (development) and PostgreSQL (production) through the same SQLAlchemy async engine. Configuration is a single env var:

```env
# SQLite (default dev)
# DB_PATH=./db.sqlite3

# PostgreSQL (production)
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
```

The `_normalise_url()` function in `core/database.py` converts bare `postgresql://` to `postgresql+asyncpg://` automatically.

## What FastAdmin Is Optimized For

FastAdmin is strongest when you want:

- a batteries-included Python/FastAPI backend
- a separate, modern admin panel
- a clear domain-app structure
- Alembic migrations for safe production schema changes
- less framework magic than Django, but more structure than a blank FastAPI repo

## What It Is Not Trying to Be

FastAdmin is not:

- a full Django feature clone
- a monolithic full-stack runtime
- a heavily automated frontend scaffolding tool

That is a design choice, not a missing identity.
