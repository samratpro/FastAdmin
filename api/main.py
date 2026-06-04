from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from alembic.config import Config
from alembic import command
from pathlib import Path
from core.config import settings
from core.database import engine, Base
from core.registry import MODEL_REGISTRY
import os
import importlib

limiter = Limiter(key_func=get_remote_address)

# Disable built-in docs — we serve protected versions below
app = FastAPI(
    title="FastAdmin API",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files (logos, favicons, SEO images) at /uploads/...
# The directory is created here so the mount never fails on a fresh checkout.
_uploads_dir = Path(__file__).parent / "uploads"
_uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")


async def _require_superuser_cookie(request: Request):
    """Dependency: validate accessToken cookie and require superuser."""
    from core.security import decode_token
    token = request.cookies.get("accessToken")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if not payload.get("isSuperuser"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    return payload


@app.get("/docs", include_in_schema=False, dependencies=[Depends(_require_superuser_cookie)])
async def protected_swagger():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="FastAdmin API — Docs")


@app.get("/redoc", include_in_schema=False, dependencies=[Depends(_require_superuser_cookie)])
async def protected_redoc():
    return get_redoc_html(openapi_url="/openapi.json", title="FastAdmin API — ReDoc")


@app.get("/openapi.json", include_in_schema=False, dependencies=[Depends(_require_superuser_cookie)])
async def protected_openapi():
    return JSONResponse(
        get_openapi(title=app.title, version=app.version, routes=app.routes)
    )


def discover_and_register_routers():
    apps_dir = "apps"
    try:
        apps_list = [d for d in os.listdir(apps_dir) if os.path.isdir(os.path.join(apps_dir, d))]
    except FileNotFoundError:
        return

    for app_name in apps_list:
        module_path = f"apps.{app_name}.routers"
        try:
            module = importlib.import_module(module_path)
            if hasattr(module, "router"):
                app.include_router(module.router)
                print(f"Registered router: {app_name}")
        except ImportError:
            pass
        except Exception as e:
            print(f"Error registering router for {app_name}: {e}")


def discover_and_register_models():
    apps_dir = "apps"
    try:
        apps_list = [d for d in os.listdir(apps_dir) if os.path.isdir(os.path.join(apps_dir, d))]
    except FileNotFoundError:
        return

    for app_name in apps_list:
        try:
            importlib.import_module(f"apps.{app_name}.models")
            print(f"Discovered models: {app_name}")
        except ImportError:
            pass
        except Exception as e:
            print(f"Error loading models for {app_name}: {e}")


def run_migrations():
    """Apply all pending Alembic migrations. Idempotent — safe to call on every startup."""
    cfg = Config(str(Path(__file__).parent / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).parent / "alembic"))
    command.upgrade(cfg, "head")


async def init_db():
    """Create any tables not tracked by Alembic (dev safety net — harmless on prod)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_permissions():
    """Create CRUD permissions for every registered model if they don't exist yet."""
    from core.database import async_session
    from apps.auth.models import Permission

    actions = [
        ("add", "Can add"),
        ("change", "Can change"),
        ("delete", "Can delete"),
        ("view", "Can view"),
    ]

    async with async_session() as db:
        for model_name, meta in MODEL_REGISTRY.items():
            table = meta["model"].__tablename__
            for action, label in actions:
                codename = f"{action}_{table}"
                existing = await Permission.objects(db).filter(codename=codename).first()
                if not existing:
                    perm = Permission(
                        name=f"{label} {model_name.lower()}",
                        codename=codename,
                        model_name=model_name,
                    )
                    await perm.save(db)


@app.on_event("startup")
async def startup_event():
    discover_and_register_models()
    run_migrations()
    await init_db()
    discover_and_register_routers()
    await seed_permissions()


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
