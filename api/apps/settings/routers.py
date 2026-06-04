import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.dependencies import require_superuser
from apps.settings.models import SiteSetting, REQUIRED_SETTINGS
from typing import Dict, Any

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("")
async def get_public_settings(db: AsyncSession = Depends(get_db)):
    settings_list = await SiteSetting.objects(db).all()
    return {"success": True, "data": {s.key: s.value for s in settings_list}}


@router.get("/admin")
async def get_admin_settings(user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    settings_list = await SiteSetting.objects(db).all()
    return {"success": True, "data": {s.key: s.value for s in settings_list}}


@router.put("/admin")
async def update_settings(payload: Dict[str, Any], user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    for key, value in payload.items():
        setting = await SiteSetting.objects(db).filter(key=key).first()
        if setting:
            setting.value = str(value)
            await setting.save(db)
        elif key in REQUIRED_SETTINGS:
            await SiteSetting(key=key, value=str(value)).save(db)
    return {"success": True, "message": "Settings updated successfully"}


@router.post("/admin/upload")
async def upload_setting_file(
    type: str,
    file: UploadFile = File(...),
    user=Depends(require_superuser),
    db: AsyncSession = Depends(get_db),
):
    if type not in ["logo", "favicon"]:
        raise HTTPException(status_code=400, detail="type must be 'logo' or 'favicon'")

    upload_dir = Path(__file__).resolve().parent.parent.parent / "uploads" / "settings"
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1] or ".png"
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
