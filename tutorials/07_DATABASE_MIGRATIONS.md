# Database Migrations

FastAdmin uses **Alembic** for schema migrations — the same approach Django uses with `makemigrations` / `migrate`, but for the Python/SQLAlchemy stack.

---

## How It Works

| Dev | Production (Docker) |
|---|---|
| `uvicorn` starts → `run_migrations()` runs `alembic upgrade head` automatically | Docker CMD runs `alembic upgrade head` first, then starts uvicorn |
| Just restart the server after generating a migration | Same automatic flow |

Migrations run automatically on every startup — dev and production. You only need to generate the migration file; applying it is handled for you.

---

## File Layout

```
api/
├── alembic.ini              ← Alembic config (DB URL injected at runtime)
├── alembic/
│   ├── env.py               ← Async-aware migration environment
│   ├── script.py.mako       ← Template for new migration files
│   └── versions/
│       └── 0001_initial.py  ← Initial migration (all 12 tables)
```

---

## Daily Developer Workflow

### The short version (3 commands)

```bash
cd api

# 1. Generate migration from model changes
make migrations msg="add view_count to blog_posts"

# 2. Apply to the database
make migrate

# 3. (optional) Roll back one step
make rollback
```

These are just aliases. Under the hood they run Alembic.

---

### Longer version (raw Alembic)

### 1. Change a model

Open `api/apps/<app>/models.py` and edit the SQLAlchemy model:

```python
# api/apps/blog/models.py
class BlogPost(Model):
    __tablename__ = "blog_posts"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    title       = Column(String(255), nullable=False)
    slug        = Column(String(255), unique=True, nullable=False)
    content     = Column(Text, nullable=False)
    published   = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    # New field added:
    view_count  = Column(Integer, default=0, nullable=False)
```

### 2. Generate the migration

```bash
cd api
alembic revision --autogenerate -m "add view_count to blog_posts"
```

Alembic compares your current model definitions against the database schema and writes a migration file like:

```
api/alembic/versions/0002_add_view_count_to_blog_posts.py
```

**Always open and review the generated file before applying it.** Autogenerate is smart but not perfect — check that the `upgrade()` and `downgrade()` functions look right.

### 3. Apply the migration

Just restart the API:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

`run_migrations()` runs `alembic upgrade head` automatically on every startup. No separate apply step needed.

Or apply manually without restarting:

```bash
make migrate
```

---

## Common Commands

| What | Make shortcut | Raw Alembic |
|---|---|---|
| Create migration | `make migrations msg="..."` | `alembic revision --autogenerate -m "..."` |
| Apply all pending | `make migrate` | `alembic upgrade head` |
| Roll back one step | `make rollback` | `alembic downgrade -1` |
| Show history | `make history` | `alembic history` |
| Show current state | `make current` | `alembic current` |
| Empty manual migration | — | `alembic revision -m "..."` |

---

## Writing a Migration Manually

When autogenerate cannot detect a change (e.g. renaming a column), write the migration by hand:

```python
# api/alembic/versions/0003_rename_body_to_content.py
"""rename body to content in blog_posts

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-05
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("blog_posts") as batch_op:
        batch_op.alter_column("body", new_column_name="content")


def downgrade():
    with op.batch_alter_table("blog_posts") as batch_op:
        batch_op.alter_column("content", new_column_name="body")
```

`op.batch_alter_table` is required for SQLite (SQLite does not support ALTER COLUMN natively). It is harmless on PostgreSQL.

---

## Adding a New App with a New Table

1. Create `api/apps/myapp/models.py` with your SQLAlchemy model:

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from core.database import Base
from common.orm import Model
from core.registry import register_admin

@register_admin(
    app_name="MyApp",
    display_name="Products",
    list_display=["name", "price", "is_active"],
)
class Product(Model):
    __tablename__ = "products"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String(255), nullable=False)
    price      = Column(Integer, default=0)
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

2. Import the model in `api/alembic/env.py` so Alembic can see it:

```python
# Near the top of alembic/env.py — add your new app
import apps.myapp.models
```

3. Generate the migration:

```bash
alembic revision --autogenerate -m "add products table"
```

4. Apply it:

```bash
alembic upgrade head
```

---

## Production Docker Flow

Migrations run **automatically** — no manual step needed.

The `api/Dockerfile` CMD is:

```dockerfile
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1"]
```

So the sequence on every `docker-compose up` is:

1. Postgres starts (healthcheck waits until ready)
2. API container starts → runs `alembic upgrade head` → applies any pending migrations
3. Uvicorn starts

**Deploy workflow (production):**

```bash
# Pull new code (with model changes)
git pull

# Rebuild and restart — migrations apply automatically on startup
docker-compose build api
docker-compose up -d --no-deps api
```

That's it. You do not run `alembic` manually on the server.

---

## Creating the First Admin User

After a fresh deploy, create your superuser:

```bash
docker-compose exec api python -c "
import asyncio
from core.database import async_session
from apps.auth.models import User
from core.security import hash_password

async def create():
    async with async_session() as db:
        u = User(
            username='admin',
            email='admin@yourdomain.com',
            password=hash_password('changeme'),
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
        await u.save(db)
        print('Superuser created.')

asyncio.run(create())
"
```

---

## SQLite vs PostgreSQL

| Topic | SQLite (dev) | PostgreSQL (prod) |
|---|---|---|
| URL format | `sqlite+aiosqlite:///./db.sqlite3` | `postgresql+asyncpg://user:pass@host/db` |
| ALTER TABLE | requires `render_as_batch=True` | native support |
| Schema changes in dev | `create_all` covers new tables; Alembic for columns | always use Alembic |
| Concurrent writes | single-writer | multi-writer |

The `alembic/env.py` normalises bare `postgresql://` to `postgresql+asyncpg://` automatically — you never need to set the async driver prefix by hand.

---

## Summary

| Task | Shortcut | Raw |
|---|---|---|
| Add a field to a model | `make migrations msg="..."` → `make migrate` | `alembic revision --autogenerate -m "..."` → `alembic upgrade head` |
| Add a new model | create model, add import to `env.py`, then same as above | same |
| Rename a column | write manual migration with `batch_alter_table`, then `make migrate` | `alembic upgrade head` |
| Roll back last migration | `make rollback` | `alembic downgrade -1` |
| See what's pending | `make history` | `alembic history` |
| Production deploy | `git pull` → `docker-compose build api` → `docker-compose up -d` | migrations run automatically |
