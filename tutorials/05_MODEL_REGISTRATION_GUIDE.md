# Model Registration Guide

This guide explains the full path from "I want a model" to "I can manage it in the admin and use it in my app".

In FastAdmin, those are separate concerns:

1. define the SQLAlchemy model in `api/apps/<name>/models.py`
2. register it for admin with `@register_admin(...)`
3. define FastAPI routes in `api/apps/<name>/routers.py`
4. add the model import to `alembic/env.py`
5. generate and apply a migration
6. restart the API (everything is auto-discovered)

---

## Creating a New App

Create the app folder and files manually:

```
api/apps/catalog/
├── __init__.py
├── models.py
└── routers.py
```

The API's startup loop auto-discovers any `routers.py` inside `api/apps/*/`.

---

## End-to-End Example

Goal: a `Product` model that appears in the admin and is available from a public API route.

### Step 1: Define the Model

Create `api/apps/catalog/models.py`:

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime
from core.database import Base
from common.orm import Model
from core.registry import register_admin

@register_admin(
    app_name="Catalog",
    display_name="Products",
    icon="package",
    list_display=["id", "name", "price", "is_active"],
    search_fields=["name", "description"],
    filter_fields=["is_active"],
)
class Product(Model):
    __tablename__ = "products"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(255), nullable=False)
    slug        = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    price       = Column(Integer, default=0)       # store in cents
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Step 2: Add Public API Routes

Create `api/apps/catalog/routers.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.dependencies import require_staff
from apps.catalog.models import Product

router = APIRouter(tags=["Catalog"])


@router.get("/api/products")
async def list_products(db: AsyncSession = Depends(get_db)):
    products = await Product.objects(db).filter(is_active=True).all()
    return {"data": products}


@router.get("/api/products/{product_id}")
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    product = await Product.objects(db).filter(id=product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"data": product}


@router.post("/api/admin/products")
async def create_product(
    payload: dict,
    user=Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    product = Product(**payload)
    await product.save(db)
    return {"data": product}
```

### Step 3: Register the Model with Alembic

Open `api/alembic/env.py` and add an import near the other model imports:

```python
import apps.catalog.models   # ← add this line
```

This ensures Alembic can see the `products` table in `Base.metadata`.

### Step 4: Generate and Apply the Migration

```bash
cd api
alembic revision --autogenerate -m "add products table"
alembic upgrade head
```

### Step 5: Restart the API

```bash
uvicorn main:app --reload --port 8000
```

The startup loop auto-discovers `apps/catalog/routers.py` and registers the router. The model appears in the admin immediately.

---

## What Happens on Startup

When the API starts:

1. `discover_and_register_models()` imports all `apps/*/models.py` files
2. `@register_admin(...)` adds each model to `MODEL_REGISTRY`
3. `init_db()` calls `create_all` — creates any missing tables (dev only; prod uses Alembic)
4. `discover_and_register_routers()` imports all `apps/*/routers.py` and calls `app.include_router(...)`
5. `seed_permissions()` creates default CRUD permissions for every registered model

---

## What `@register_admin(...)` Does

`@register_admin(...)` does three practical things:

1. makes the model visible to the admin UI
2. provides metadata for list columns, search, filters, and icons
3. ensures CRUD permissions are auto-created on startup

It does not create public API routes for you. Those remain explicit in `routers.py`.

---

## Available `@register_admin` Options

```python
@register_admin(
    app_name="Catalog",          # sidebar section heading
    display_name="Products",     # label shown in the admin
    icon="package",              # Lucide icon name
    list_display=["id", "name", "price", "is_active"],  # columns in list view
    search_fields=["name", "description"],              # fields searched by the search bar
    filter_fields=["is_active"],                        # sidebar filter options
    exclude_fields=["internal_notes"],                  # fields hidden from all admin forms
)
```

---

## Field Types

| SQLAlchemy Column | Use For |
|---|---|
| `String(n)` | short text, VARCHAR |
| `Text` | long text |
| `Integer` | integers, IDs, foreign keys |
| `Float` | decimal numbers |
| `Boolean` | true/false |
| `DateTime` | timestamps |
| `Date` | date only |
| `ForeignKey("table.id")` | relational references |

---

## Relationships

Use `ForeignKey` + `relationship` when one model references another:

```python
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base
from common.orm import Model
from core.registry import register_admin


@register_admin(app_name="Catalog", display_name="Categories", list_display=["id", "name"])
class Category(Model):
    __tablename__ = "catalog_categories"

    id   = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)

    products = relationship("Product", back_populates="category")


@register_admin(
    app_name="Catalog",
    display_name="Products",
    list_display=["id", "name", "category_id"],
)
class Product(Model):
    __tablename__ = "products"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(255), nullable=False)
    category_id = Column(Integer, ForeignKey("catalog_categories.id"), nullable=True)

    category = relationship("Category", back_populates="products")
```

---

## Query API

The `Model.objects(db)` method returns a chainable async query object:

```python
# All records
products = await Product.objects(db).all()

# Filter
active = await Product.objects(db).filter(is_active=True).all()

# Single record
product = await Product.objects(db).filter(id=42).first()

# Order
recent = await Product.objects(db).order_by("created_at", "DESC").all()
```

---

## Admin-Only vs Public-Only Models

If a model should be manageable in the admin, use `@register_admin(...)`.

If a model is internal or API-only with no admin:

- omit `@register_admin(...)`
- it will not appear in the admin sidebar
- add the model import to `alembic/env.py` manually so Alembic still tracks it
- `create_all` in dev will still create the table automatically

---

## Troubleshooting

### Model does not appear in admin

1. Model has `@register_admin(...)`
2. Model file is named `models.py` inside `api/apps/<app>/`
3. API server was restarted after adding the model

### Table does not exist

1. For dev: restart the API — `create_all` creates missing tables
2. For prod: run `alembic revision --autogenerate` + `alembic upgrade head`
3. Check that the model file is in the correct location

### Public route returns 404

1. `routers.py` exists in the app folder
2. The file contains a `router = APIRouter(...)` variable at module level
3. API server was restarted

---

## Recommended Mental Model

In FastAdmin, a model has three separate concerns:

- **data definition** — `models.py`, SQLAlchemy columns
- **admin registration** — `@register_admin(...)` decorator options
- **public API exposure** — `routers.py`, FastAPI route handlers

Keeping those concerns explicit is one of the framework's core ideas.
