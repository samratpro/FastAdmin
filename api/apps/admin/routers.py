from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Integer, SmallInteger, BigInteger, String, Text, Boolean, DateTime, Date, Float, Numeric, select
from typing import Any, Dict, Optional
from core.database import get_db
from core.dependencies import require_staff, require_superuser
from core.registry import MODEL_REGISTRY, get_model_by_name

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def _introspect_fields(model_cls) -> dict:
    from sqlalchemy import inspect as sa_inspect
    mapper = sa_inspect(model_cls).mapper
    fields = {}

    for col_attr in mapper.column_attrs:
        col = col_attr.columns[0]
        name = col_attr.key
        col_type = type(col.type)

        has_fk = bool(col.foreign_keys)
        related_model = None

        if has_fk:
            field_type = "ForeignKey"
            fk = list(col.foreign_keys)[0]
            related_table = fk.column.table.name
            for reg_name, reg_meta in MODEL_REGISTRY.items():
                if reg_meta["model"].__tablename__ == related_table:
                    related_model = reg_name
                    break
        elif issubclass(col_type, Boolean):
            field_type = "BooleanField"
        elif issubclass(col_type, (Integer, SmallInteger, BigInteger)):
            field_type = "IntegerField"
        elif issubclass(col_type, (Float, Numeric)):
            field_type = "FloatField"
        elif issubclass(col_type, DateTime):
            field_type = "DateTimeField"
        elif issubclass(col_type, Date):
            field_type = "DateField"
        elif issubclass(col_type, Text):
            field_type = "TextField"
        elif issubclass(col_type, String):
            if "email" in name.lower():
                field_type = "EmailField"
            elif "url" in name.lower() or "link" in name.lower():
                field_type = "URLField"
            else:
                field_type = "CharField"
        else:
            field_type = "CharField"

        max_length = getattr(col.type, "length", None)
        is_nullable = bool(col.nullable)
        is_required = not is_nullable and col.default is None and not col.primary_key

        default_val = None
        if col.default is not None and hasattr(col.default, "arg") and not callable(col.default.arg):
            default_val = col.default.arg

        field_info: dict = {
            "name": name,
            "type": field_type,
            "required": is_required,
            "nullable": is_nullable,
            "unique": bool(col.unique),
        }
        if max_length:
            field_info["maxLength"] = max_length
        if default_val is not None:
            field_info["default"] = default_val
        if related_model:
            field_info["relatedModel"] = related_model

        fields[name] = field_info

    return fields


# ── Model registry ──────────────────────────────────────────────────────────

@router.get("/models")
async def list_models(user=Depends(require_staff)):
    return {
        "models": [
            {
                "name": name,
                "displayName": meta["display_name"],
                "appName": meta["app_name"],
                "tableName": meta["model"].__tablename__,
                "icon": meta.get("icon", ""),
                "permissions": [],
                "listDisplay": meta["list_display"],
            }
            for name, meta in MODEL_REGISTRY.items()
        ]
    }


@router.get("/models/{model_name}")
async def get_model_metadata(model_name: str, user=Depends(require_staff)):
    meta = MODEL_REGISTRY.get(model_name)
    if not meta:
        raise HTTPException(status_code=404, detail="Model not found")

    model_cls = meta["model"]
    fields = _introspect_fields(model_cls)

    filter_fields = meta.get("filter_fields") or [k for k, v in fields.items() if v["type"] == "BooleanField"]
    related_fields = {k: v["relatedModel"] for k, v in fields.items() if v["type"] == "ForeignKey" and v.get("relatedModel")}
    exclude_fields = meta.get("exclude_fields") or []

    return {
        "metadata": {
            "displayName": meta["display_name"],
            "tableName": model_cls.__tablename__,
            "icon": meta.get("icon", ""),
            "permissions": [],
            "fields": fields,
            "adminOptions": {
                "listDisplay": meta["list_display"],
                "searchFields": meta.get("search_fields") or [],
                "filterFields": filter_fields,
                "excludeFields": exclude_fields,
                "relatedFields": related_fields,
            },
        }
    }


@router.get("/models/{model_name}/data")
async def list_model_data(
    model_name: str,
    page: int = 1,
    limit: int = 20,
    orderBy: str = Query(default="id"),
    orderDirection: str = Query(default="DESC"),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_staff),
):
    model_cls = get_model_by_name(model_name)
    if not model_cls:
        raise HTTPException(status_code=404, detail="Model not found")

    valid_fields = {c.key for c in model_cls.__table__.columns}
    safe_order_by = orderBy if orderBy in valid_fields else "id"
    safe_order_dir = "DESC" if orderDirection.upper() == "DESC" else "ASC"

    qs = model_cls.objects(db).order_by(safe_order_by, safe_order_dir).limit(limit).offset((page - 1) * limit)
    data = await qs.all()
    total = await model_cls.objects(db).count()

    return {
        "success": True,
        "data": [item.to_dict() for item in data],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "totalPages": max(1, (total + limit - 1) // limit),
        },
    }


@router.post("/models/{model_name}/data")
async def create_model_data(
    model_name: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    user=Depends(require_staff),
):
    model_cls = get_model_by_name(model_name)
    if not model_cls:
        raise HTTPException(status_code=404, detail="Model not found")

    # Hash password fields if present
    for key in list(payload.keys()):
        if "password" in key.lower() and payload[key]:
            from core.security import hash_password
            payload[key] = hash_password(payload[key])

    instance = model_cls(**payload)
    await instance.save(db)
    return {"success": True, "data": instance.to_dict()}


@router.put("/models/{model_name}/data/{item_id}")
async def update_model_data(
    model_name: str,
    item_id: int,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    user=Depends(require_staff),
):
    model_cls = get_model_by_name(model_name)
    if not model_cls:
        raise HTTPException(status_code=404, detail="Model not found")

    instance = await model_cls.objects(db).filter(id=item_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Item not found")

    for key, value in payload.items():
        if "password" in key.lower():
            if value:
                from core.security import hash_password
                setattr(instance, key, hash_password(value))
        else:
            setattr(instance, key, value)

    await instance.save(db)
    return {"success": True, "data": instance.to_dict()}


@router.delete("/models/{model_name}/data/{item_id}")
async def delete_model_data(
    model_name: str,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_staff),
):
    model_cls = get_model_by_name(model_name)
    if not model_cls:
        raise HTTPException(status_code=404, detail="Model not found")

    instance = await model_cls.objects(db).filter(id=item_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Item not found")

    await instance.delete(db)
    return {"success": True, "message": "Deleted successfully"}


# ── Users / Groups / Permissions management ─────────────────────────────────

@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db), user=Depends(require_staff)):
    from apps.auth.models import User
    users = await User.objects(db).order_by("id", "ASC").all()
    safe = [{k: v for k, v in u.to_dict().items() if k != "password"} for u in users]
    return {"users": safe}


@router.get("/groups")
async def list_groups(db: AsyncSession = Depends(get_db), user=Depends(require_staff)):
    from apps.auth.models import Group
    groups = await Group.objects(db).order_by("id", "ASC").all()
    return {"groups": [g.to_dict() for g in groups]}


@router.get("/permissions")
async def list_permissions(db: AsyncSession = Depends(get_db), user=Depends(require_staff)):
    from apps.auth.models import Permission
    perms = await Permission.objects(db).order_by("id", "ASC").all()
    return {"permissions": [p.to_dict() for p in perms]}


@router.get("/users/{user_id}/groups")
async def get_user_groups(user_id: int, db: AsyncSession = Depends(get_db), user=Depends(require_staff)):
    from apps.auth.models import User, UserGroup
    result = await db.execute(select(UserGroup.group_id).where(UserGroup.user_id == user_id))
    return {"groupIds": [row[0] for row in result.fetchall()]}


@router.put("/users/{user_id}/groups")
async def set_user_groups(user_id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), user=Depends(require_staff)):
    from apps.auth.models import UserGroup
    from sqlalchemy import delete
    await db.execute(delete(UserGroup).where(UserGroup.user_id == user_id))
    for gid in (payload.get("groupIds") or []):
        db.add(UserGroup(user_id=user_id, group_id=gid))
    await db.commit()
    return {"success": True}


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(user_id: int, db: AsyncSession = Depends(get_db), user=Depends(require_staff)):
    from apps.auth.models import UserPermission
    result = await db.execute(select(UserPermission.permission_id).where(UserPermission.user_id == user_id))
    return {"permissionIds": [row[0] for row in result.fetchall()]}


@router.put("/users/{user_id}/permissions")
async def set_user_permissions(user_id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), user=Depends(require_staff)):
    from apps.auth.models import UserPermission
    from sqlalchemy import delete
    await db.execute(delete(UserPermission).where(UserPermission.user_id == user_id))
    for pid in (payload.get("permissionIds") or []):
        db.add(UserPermission(user_id=user_id, permission_id=pid))
    await db.commit()
    return {"success": True}


@router.get("/groups/{group_id}/permissions")
async def get_group_permissions(group_id: int, db: AsyncSession = Depends(get_db), user=Depends(require_staff)):
    from apps.auth.models import GroupPermission
    result = await db.execute(select(GroupPermission.permission_id).where(GroupPermission.group_id == group_id))
    return {"permissionIds": [row[0] for row in result.fetchall()]}


@router.put("/groups/{group_id}/permissions")
async def set_group_permissions(group_id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), user=Depends(require_staff)):
    from apps.auth.models import GroupPermission
    from sqlalchemy import delete
    await db.execute(delete(GroupPermission).where(GroupPermission.group_id == group_id))
    for pid in (payload.get("permissionIds") or []):
        db.add(GroupPermission(group_id=group_id, permission_id=pid))
    await db.commit()
    return {"success": True}


# ── Settings (alias at /api/admin/settings) ──────────────────────────────────

@router.get("/settings")
async def get_admin_settings(user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    from apps.settings.models import SiteSetting
    settings_list = await SiteSetting.objects(db).all()
    return {"success": True, "data": {s.key: s.value for s in settings_list}}


@router.put("/settings")
async def update_admin_settings(payload: Dict[str, Any], user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    from apps.settings.models import SiteSetting, REQUIRED_SETTINGS
    for key, value in payload.items():
        setting = await SiteSetting.objects(db).filter(key=key).first()
        if setting:
            setting.value = str(value)
            await setting.save(db)
        elif key in REQUIRED_SETTINGS:
            await SiteSetting(key=key, value=str(value)).save(db)
    return {"success": True, "message": "Settings updated successfully"}


@router.post("/settings/upload")
async def upload_settings_file(
    type: str,
    file: UploadFile = File(...),
    user=Depends(require_superuser),
    db: AsyncSession = Depends(get_db),
):
    from apps.settings.models import SiteSetting
    import os
    ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico"}
    if type not in ["logo", "favicon"]:
        raise HTTPException(status_code=400, detail="type must be 'logo' or 'favicon'")
    upload_dir = Path(__file__).resolve().parent.parent.parent / "uploads" / "settings"
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1].lower() or ".png"
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f'File type "{ext}" not allowed')
    dest = upload_dir / f"{type}{ext}"
    content = await file.read()
    dest.write_bytes(content)
    file_url = f"/uploads/settings/{type}{ext}"
    key = "logoUrl" if type == "logo" else "faviconUrl"
    setting = await SiteSetting.objects(db).filter(key=key).first()
    if setting:
        setting.value = file_url
        await setting.save(db)
    else:
        await SiteSetting(key=key, value=file_url).save(db)
    return {"success": True, "data": {"url": file_url}}
