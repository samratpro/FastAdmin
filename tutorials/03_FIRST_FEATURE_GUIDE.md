# First Feature Guide

This is the fastest end-to-end path for building something real in FastAdmin.

Goal:

- define a model
- expose public API routes
- manage the model from the admin
- fetch the data from a user-facing frontend

We will use a simple blog-style example.

## Final Result

At the end, you will have:

- a `BlogPost` model in `api/apps/blog/models.py`
- public routes like `GET /api/posts`
- a model visible in the admin
- a public app that can fetch posts from the API

The `blog` app already exists in this repo. This guide walks through what it does and how to apply the same pattern to any new feature.

---

## Step 1: Create the App Folder

Create the directory and required files:

```bash
mkdir api/apps/myfeature
touch api/apps/myfeature/__init__.py
touch api/apps/myfeature/models.py
touch api/apps/myfeature/routers.py
```

---

## Step 2: Define the Model

Edit `api/apps/myfeature/models.py`:

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime
from core.database import Base
from common.orm import Model
from core.registry import register_admin

@register_admin(
    app_name="Content",
    display_name="Blog Posts",
    icon="file-text",
    list_display=["id", "title", "published", "created_at"],
    search_fields=["title", "content"],
    filter_fields=["published"],
)
class BlogPost(Model):
    __tablename__ = "blog_posts"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    title      = Column(String(255), nullable=False)
    slug       = Column(String(255), unique=True, nullable=False)
    content    = Column(Text, nullable=True)
    published  = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## Step 3: Define Public API Routes

Edit `api/apps/myfeature/routers.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from apps.myfeature.models import BlogPost

router = APIRouter(tags=["Blog"])


@router.get("/api/posts")
async def list_posts(db: AsyncSession = Depends(get_db)):
    posts = await BlogPost.objects(db).filter(published=True).order_by("id", "DESC").all()
    return {"data": posts}


@router.get("/api/posts/{post_id}")
async def get_post(post_id: int, db: AsyncSession = Depends(get_db)):
    post = await BlogPost.objects(db).filter(id=post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"data": post}
```

---

## Step 4: Register with Alembic

Open `api/alembic/env.py` and add the import near the other model imports:

```python
import apps.myfeature.models
```

---

## Step 5: Generate and Apply the Migration

```bash
cd api
alembic revision --autogenerate -m "add blog_posts table"
alembic upgrade head
```

---

## Step 6: Start the API

```bash
cd api
uvicorn main:app --reload --port 8000
```

The auto-discovery engine finds `apps/myfeature/routers.py` and registers the router. The model appears in the admin immediately.

You can verify:

```bash
# API health
curl http://localhost:8000/health

# List posts (empty for now)
curl http://localhost:8000/api/posts
```

---

## What Happens After Restart

When the API starts:

1. `discover_and_register_models()` imports all `apps/*/models.py`
2. `@register_admin(...)` adds the model to `MODEL_REGISTRY`
3. `init_db()` creates any missing tables (dev only)
4. `discover_and_register_routers()` imports all `apps/*/routers.py` and calls `app.include_router(...)`
5. `seed_permissions()` creates `add_blog_posts`, `change_blog_posts`, `delete_blog_posts`, `view_blog_posts` permissions automatically

---

## Step 7: Use the Model from Your Public Frontend

Any frontend can now read published posts:

```javascript
// Next.js / React
const res = await fetch("http://localhost:8000/api/posts");
const { data } = await res.json();
```

Or from a Next.js server component:

```typescript
export default async function BlogPage() {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/posts`);
  const { data } = await res.json();

  return (
    <ul>
      {data.map((post: any) => (
        <li key={post.id}>{post.title}</li>
      ))}
    </ul>
  );
}
```

---

## Adding an Admin Write Route

To let staff users create posts from the admin (or a custom frontend):

```python
from core.dependencies import require_staff

@router.post("/api/admin/posts")
async def create_post(
    payload: dict,
    user=Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    post = BlogPost(**payload)
    await post.save(db)
    return {"data": post}
```

`require_staff` checks the `accessToken` cookie and rejects requests from non-staff users with 403.

---

## Summary

| Step | What You Do |
|---|---|
| Create app folder | `mkdir api/apps/<name>` + `__init__.py` |
| Define model | SQLAlchemy columns in `models.py` + `@register_admin(...)` |
| Define routes | FastAPI handlers in `routers.py` |
| Migration | `alembic revision --autogenerate -m "..."` → `alembic upgrade head` |
| Restart | `uvicorn main:app --reload` |
| Admin | model appears automatically |
| Public frontend | `fetch("/api/posts")` |
