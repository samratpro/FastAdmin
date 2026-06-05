import os
import shutil
import json
import glob as glob_module
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.dependencies import require_superuser
from core.config import settings

router = APIRouter(prefix="/api/admin/backup", tags=["Backup"])

# ── Directory helpers ─────────────────────────────────────────────────────────

def _api_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent  # api/

def _data_root() -> Path:
    """Persistent data directory.
    In Docker: /app/appdata (host-mounted volume via DATA_DIR env var).
    In dev:    same as _api_root()."""
    if settings.DATA_DIR:
        p = Path(settings.DATA_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p
    return _api_root()

def _backups_dir() -> Path:
    # Backups always live next to the code root (mounted as a separate volume in Docker)
    d = _api_root() / "backups"
    d.mkdir(exist_ok=True)
    return d

def _schedule_file() -> Path:
    return _data_root() / "backup_schedule.json"

def _log_file() -> Path:
    return _data_root() / "backup_log.json"

def _creds_file() -> Path:
    return _data_root() / "drive_credentials.json"

def _token_file() -> Path:
    return _data_root() / "drive_token.json"

# ── Core helpers ──────────────────────────────────────────────────────────────

def _find_databases() -> list[dict]:
    root = _api_root()
    results = []
    for pattern in ("*.db", "*.sqlite3"):
        for path in root.glob(pattern):
            if "env" in path.parts or "backups" in path.parts:
                continue
            stat = path.stat()
            results.append({
                "name": path.name,
                "path": str(path),
                "sizeBytes": stat.st_size,
                "engine": "sqlite",
            })
    return results

def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def _file_info(p: Path) -> dict:
    stat = p.stat()
    return {
        "filename": p.name,
        "sizeBytes": stat.st_size,
        "createdAt": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
        "modifiedAt": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }

def _load_schedule() -> dict:
    f = _schedule_file()
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {
        "enabled": False, "frequency": "daily", "hour": 3, "minute": 0,
        "keepCount": 2, "uploadToDrive": False, "bandwidthLimitMbps": 50,
    }

def _save_schedule(cfg: dict):
    _schedule_file().write_text(json.dumps(cfg, indent=2))

def _load_log() -> list:
    f = _log_file()
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return []

def _append_log(entry: dict):
    log = _load_log()
    log.insert(0, entry)
    log = log[:50]
    _log_file().write_text(json.dumps(log, indent=2))

def _drive_status() -> dict:
    creds = _creds_file()
    token = _token_file()
    if not creds.exists():
        return {"configured": False, "authMethod": None, "canConnect": False, "credentialsSource": None, "folderName": "FastAdmin Backups"}
    try:
        data = json.loads(creds.read_text())
        if "type" in data and data["type"] == "service_account":
            return {"configured": True, "authMethod": "service_account", "canConnect": True, "credentialsSource": "file", "folderName": "FastAdmin Backups"}
        can = token.exists()
        return {"configured": can, "authMethod": "oauth2" if can else None, "canConnect": True, "credentialsSource": "file", "folderName": "FastAdmin Backups"}
    except Exception:
        return {"configured": False, "authMethod": None, "canConnect": False, "credentialsSource": "file", "folderName": "FastAdmin Backups"}

def _do_backup(db_path: str, trigger: str = "manual") -> dict:
    src = Path(db_path)
    if not src.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    stem = src.stem.replace(".", "_")
    filename = f"backup_{stem}_{_ts()}.sqlite3"
    dest = _backups_dir() / filename
    shutil.copy2(src, dest)
    stat = dest.stat()
    return {
        "filename": filename,
        "sizeBytes": stat.st_size,
        "createdAt": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
        "modifiedAt": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }

def _make_safety_backup(db_path: str) -> str:
    src = Path(db_path)
    if not src.exists():
        return ""
    stem = src.stem.replace(".", "_")
    filename = f"safety_{stem}_{_ts()}.sqlite3"
    dest = _backups_dir() / filename
    shutil.copy2(src, dest)
    return filename

# ── Database endpoints ────────────────────────────────────────────────────────

@router.get("/databases")
async def get_databases(user=Depends(require_superuser)):
    return {"databases": _find_databases()}


@router.get("/download-db")
async def download_db_file(dbPath: str = Query(...), user=Depends(require_superuser)):
    p = Path(dbPath).resolve()
    api_root = _api_root().resolve()
    if not str(p).startswith(str(api_root)):
        raise HTTPException(status_code=403, detail="Access denied")
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Database file not found")
    return FileResponse(
        path=str(p),
        filename=p.name,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{p.name}"'},
    )

# ── Backup file endpoints ─────────────────────────────────────────────────────

@router.post("/create")
async def create_backup(payload: dict, user=Depends(require_superuser)):
    db_path = payload.get("dbPath")
    if not db_path:
        raise HTTPException(status_code=400, detail="dbPath is required")
    start = datetime.now()
    try:
        backup = _do_backup(db_path)
        duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        _append_log({
            "at": datetime.now(tz=timezone.utc).isoformat(),
            "trigger": "manual",
            "status": "success",
            "file": backup["filename"],
            "sizeBytes": backup["sizeBytes"],
            "durationMs": duration_ms,
            "uploadedDrive": False,
            "deletedLocal": 0,
            "deletedDrive": 0,
        })
        return {"backup": backup}
    except Exception as e:
        _append_log({
            "at": datetime.now(tz=timezone.utc).isoformat(),
            "trigger": "manual",
            "status": "error",
            "durationMs": int((datetime.now() - start).total_seconds() * 1000),
            "uploadedDrive": False,
            "deletedLocal": 0,
            "deletedDrive": 0,
            "error": str(e),
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_backups(user=Depends(require_superuser)):
    backups_dir = _backups_dir()
    files = sorted(backups_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
    return {"backups": [_file_info(f) for f in files if f.is_file()]}


@router.get("/files/{filename}/download")
async def download_backup(filename: str, user=Depends(require_superuser)):
    p = _backups_dir() / filename
    if not p.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")
    return FileResponse(
        path=str(p),
        filename=filename,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/files/{filename}")
async def delete_backup(filename: str, user=Depends(require_superuser)):
    p = _backups_dir() / filename
    if not p.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")
    p.unlink()
    return {"success": True}


@router.post("/files/{filename}/restore")
async def restore_from_stored(filename: str, payload: dict = {}, user=Depends(require_superuser)):
    backup_path = _backups_dir() / filename
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")

    db_path = payload.get("dbPath") if payload else None
    if not db_path:
        dbs = _find_databases()
        if not dbs:
            raise HTTPException(status_code=400, detail="No database found to restore into")
        db_path = dbs[0]["path"]

    safety = _make_safety_backup(db_path)
    shutil.copy2(backup_path, db_path)
    return {"restoredTo": db_path, "safetyBackup": safety}


@router.post("/restore")
async def restore_from_upload(
    file: UploadFile = File(...),
    dbPath: str = Query(None),
    user=Depends(require_superuser),
):
    if not dbPath:
        dbs = _find_databases()
        if not dbs:
            raise HTTPException(status_code=400, detail="No database found to restore into")
        dbPath = dbs[0]["path"]

    safety = _make_safety_backup(dbPath)

    tmp = _backups_dir() / f"upload_{_ts()}_{file.filename}"
    try:
        content = await file.read()
        tmp.write_bytes(content)
        shutil.copy2(tmp, dbPath)
    finally:
        if tmp.exists():
            tmp.unlink()

    return {"restoredTo": dbPath, "safetyBackup": safety}

# ── Google Drive endpoints ────────────────────────────────────────────────────

@router.get("/drive/status")
async def drive_status(user=Depends(require_superuser)):
    return _drive_status()


@router.get("/drive/auth-url")
async def drive_auth_url(user=Depends(require_superuser)):
    if not _creds_file().exists():
        raise HTTPException(status_code=400, detail="Upload credentials.json first")
    raise HTTPException(status_code=501, detail="OAuth2 flow not configured. Use a Service Account credentials.json instead.")


@router.post("/drive/credentials")
async def upload_drive_credentials(file: UploadFile = File(...), user=Depends(require_superuser)):
    content = await file.read()
    try:
        data = json.loads(content)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON credentials file")
    _creds_file().write_bytes(content)
    client_id = data.get("client_id") or data.get("client_email") or "unknown"
    return {"success": True, "clientId": client_id}


@router.delete("/drive/credentials")
async def remove_drive_credentials(user=Depends(require_superuser)):
    for f in [_creds_file(), _token_file()]:
        if f.exists():
            f.unlink()
    return {"success": True}


@router.delete("/drive/disconnect")
async def disconnect_drive(user=Depends(require_superuser)):
    if _token_file().exists():
        _token_file().unlink()
    return {"success": True}


@router.post("/files/{filename}/send-to-drive")
async def send_to_drive(filename: str, user=Depends(require_superuser)):
    status = _drive_status()
    if not status["configured"]:
        raise HTTPException(status_code=400, detail="Google Drive is not connected")
    raise HTTPException(status_code=501, detail="Drive upload not implemented. Configure a Service Account to enable this.")

# ── Schedule endpoints ────────────────────────────────────────────────────────

@router.get("/schedule")
async def get_schedule(user=Depends(require_superuser)):
    return _load_schedule()


@router.post("/schedule")
async def save_schedule(payload: dict, user=Depends(require_superuser)):
    cfg = {
        "enabled": bool(payload.get("enabled", False)),
        "frequency": payload.get("frequency", "daily"),
        "hour": int(payload.get("hour", 3)),
        "minute": int(payload.get("minute", 0)),
        "keepCount": int(payload.get("keepCount", 2)),
        "uploadToDrive": bool(payload.get("uploadToDrive", False)),
        "bandwidthLimitMbps": int(payload.get("bandwidthLimitMbps", 50)),
    }
    _save_schedule(cfg)
    return {"success": True, "config": cfg}


@router.post("/schedule/run-now")
async def run_backup_now(user=Depends(require_superuser)):
    dbs = _find_databases()
    if not dbs:
        raise HTTPException(status_code=400, detail="No database files found")
    import asyncio
    asyncio.create_task(_run_backup_task(dbs))
    return {"success": True, "message": f"Backup started for {len(dbs)} database(s)"}

# ── Log endpoints ─────────────────────────────────────────────────────────────

_backup_running = False


@router.get("/log")
async def get_backup_log(user=Depends(require_superuser)):
    global _backup_running
    return {"running": _backup_running, "log": _load_log()}


async def _run_backup_task(dbs: list[dict]):
    global _backup_running
    _backup_running = True
    start = datetime.now()
    try:
        for db in dbs:
            _do_backup(db["path"], trigger="manual")
        duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        _append_log({
            "at": datetime.now(tz=timezone.utc).isoformat(),
            "trigger": "manual",
            "status": "success",
            "durationMs": duration_ms,
            "uploadedDrive": False,
            "deletedLocal": 0,
            "deletedDrive": 0,
        })
    except Exception as e:
        _append_log({
            "at": datetime.now(tz=timezone.utc).isoformat(),
            "trigger": "manual",
            "status": "error",
            "durationMs": int((datetime.now() - start).total_seconds() * 1000),
            "uploadedDrive": False,
            "deletedLocal": 0,
            "deletedDrive": 0,
            "error": str(e),
        })
    finally:
        _backup_running = False
