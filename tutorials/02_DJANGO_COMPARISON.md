# Django Comparison

FastAdmin is inspired by Django, but it does not try to reproduce Django exactly.

This document is the easiest way to understand the overlap and the differences.

## Where It Feels Familiar

If you know Django, these ideas should feel natural:

- app-oriented backend structure (`apps/auth/`, `apps/blog/`, etc.)
- model classes for persistence (SQLAlchemy, similar shape to Django ORM)
- a built-in admin concept
- Alembic migrations (`makemigrations` / `migrate` equivalent)
- a preference for convention over chaos

## Where It Differs

FastAdmin is more explicitly decoupled.

Instead of one framework owning templates, admin rendering, routing, and database behavior in one place, FastAdmin splits those concerns:

- FastAPI handles the backend runtime
- Next.js handles the admin UI
- your public frontend is free to evolve separately

## Quick Mapping

| Django | FastAdmin |
|---|---|
| `manage.py startapp` | create `api/apps/<name>/` manually |
| `settings.py` | `api/core/config.py` (pydantic-settings) |
| `models.py` | `models.py` in each app (SQLAlchemy) |
| `views.py` + `urls.py` | `routers.py` in each app (FastAPI) |
| Django admin | standalone Next.js admin app |
| `manage.py createsuperuser` | see [06_USER_AND_AUTH_GUIDE.md](./06_USER_AND_AUTH_GUIDE.md) |
| `manage.py makemigrations` | `alembic revision --autogenerate -m "..."` |
| `manage.py migrate` | `alembic upgrade head` |
| `manage.py shell` | `python` REPL with `asyncio.run(...)` for async calls |

## Models

Django:

```python
class Article(models.Model):
    title     = models.CharField(max_length=255)
    content   = models.TextField()
    published = models.BooleanField(default=False)
```

FastAdmin:

```python
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from datetime import datetime
from core.database import Base
from common.orm import Model
from core.registry import register_admin

@register_admin(
    app_name="Content",
    display_name="Articles",
    list_display=["title", "published", "created_at"],
)
class Article(Model):
    __tablename__ = "articles"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    title     = Column(String(255), nullable=False)
    content   = Column(Text, nullable=True)
    published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## Query Style

Django:

```python
Article.objects.filter(published=True)
```

FastAdmin (async):

```python
articles = await Article.objects(db).filter(published=True).all()
```

The session `db` is an `AsyncSession` injected by FastAPI's dependency system:

```python
from core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

@router.get("/api/articles")
async def list_articles(db: AsyncSession = Depends(get_db)):
    articles = await Article.objects(db).filter(published=True).all()
    return articles
```

## Admin Registration

Django:

```python
# admin.py
from django.contrib import admin
from .models import Article

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ["title", "published"]
```

FastAdmin — registration is a decorator on the model itself:

```python
@register_admin(
    app_name="Content",
    display_name="Articles",
    list_display=["title", "published"],
    search_fields=["title", "content"],
    exclude_fields=["internal_notes"],
    icon="file-text",
)
class Article(Model):
    ...
```

No separate admin file needed.

## Migrations

Django:

```bash
python manage.py makemigrations
python manage.py migrate
```

FastAdmin:

```bash
cd api
alembic revision --autogenerate -m "add articles table"
alembic upgrade head
```

The workflow is nearly identical. Migration files live in `api/alembic/versions/` and are committed to git exactly like Django migration files.

See [07_DATABASE_MIGRATIONS.md](./07_DATABASE_MIGRATIONS.md) for the full guide.

## Admin Philosophy

Django admin is tightly integrated with the backend framework. FastAdmin admin is a separate Next.js application that consumes the API. That gives you more UI flexibility, but also means the admin is not a backend-side switch — it is a real frontend application.

## Authentication

Django defaults to session-oriented patterns. FastAdmin ships with JWT-based auth: `accessToken` stored as an httpOnly cookie. This fits modern frontend and API workflows naturally.

## What Django Still Does Better Today

Django is still stronger in several areas:

- ORM maturity (complex joins, annotations, aggregations)
- ecosystem depth (third-party packages)
- built-in form validation

FastAdmin is not pretending otherwise.

## What FastAdmin Does Differently

FastAdmin aims to be stronger in a different direction:

- cleaner separation between admin and backend
- async-first (every DB call is `await`)
- easier integration with modern frontend workflows
- less framework entanglement
- a more explicit architecture for teams that value loose coupling

## Best Mental Model

Think of FastAdmin as:

> "Django's app-oriented productivity ideas, rebuilt for a Python/FastAPI and async-first workflow, with a modern Next.js admin UI instead of server-rendered templates."
