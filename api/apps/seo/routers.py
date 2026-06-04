import os
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import PlainTextResponse
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.dependencies import require_staff
from apps.seo.models import SEOPage, SEORobots, SEORedirect

router = APIRouter(tags=["SEO"])


def _page_to_dict(page) -> dict:
    return {
        "pageSlug": page.page_slug,
        "metaTitle": page.title or "",
        "metaDescription": page.description or "",
        "canonicalUrl": page.canonical_url or "",
        "ogType": page.og_type or "website",
        "ogTitle": page.og_title or "",
        "ogDescription": page.og_description or "",
        "ogImage": page.og_image or "",
        "twitterCardType": page.twitter_card_type or "summary_large_image",
        "twitterTitle": page.twitter_title or "",
        "twitterDescription": page.twitter_description or "",
        "twitterImage": page.twitter_image or "",
        "noIndex": bool(page.no_index),
        "noFollow": bool(page.no_follow),
        "schema": page.schema or "",
    }


def _redirect_to_dict(r) -> dict:
    return {
        "id": str(r.id),
        "from": r.from_url or "",
        "to": r.to_url or "",
        "type": int(r.type) if r.type and str(r.type).isdigit() else 301,
        "createdAt": r.created_at.isoformat() if r.created_at else "",
    }


# ── Public endpoints ─────────────────────────────────────────────────────────

@router.get("/api/seo/head")
async def get_seo_head(slug: str, db: AsyncSession = Depends(get_db)):
    page = await SEOPage.objects(db).filter(page_slug=slug).first()
    if not page:
        return {"success": True, "data": {}}
    return {"success": True, "data": _page_to_dict(page)}


@router.get("/api/seo/robots-text", response_class=PlainTextResponse)
async def get_robots_text(db: AsyncSession = Depends(get_db)):
    robots = await SEORobots.objects(db).first()
    return robots.content if robots else "User-agent: *\nAllow: /"


# ── Admin endpoints ───────────────────────────────────────────────────────────

@router.get("/api/admin/seo/robots")
async def get_admin_robots(user=Depends(require_staff), db: AsyncSession = Depends(get_db)):
    robots = await SEORobots.objects(db).first()
    return {"content": robots.content if robots else ""}


@router.post("/api/admin/seo/robots")
async def update_admin_robots(payload: dict, user=Depends(require_staff), db: AsyncSession = Depends(get_db)):
    robots = await SEORobots.objects(db).first()
    if not robots:
        robots = SEORobots(content=payload.get("content", ""))
    else:
        robots.content = payload.get("content", "")
    await robots.save(db)
    return {"success": True}


@router.get("/api/admin/seo/pages")
async def list_seo_pages(user=Depends(require_staff), db: AsyncSession = Depends(get_db)):
    pages = await SEOPage.objects(db).order_by("id", "ASC").all()
    return [_page_to_dict(p) for p in pages]


@router.post("/api/admin/seo/pages")
async def upsert_seo_page(payload: dict, user=Depends(require_staff), db: AsyncSession = Depends(get_db)):
    slug = (payload.get("pageSlug") or payload.get("page_slug") or "").strip()
    if not slug:
        raise HTTPException(status_code=400, detail="pageSlug is required")

    page = await SEOPage.objects(db).filter(page_slug=slug).first()
    if not page:
        page = SEOPage(page_slug=slug)

    page.title = payload.get("metaTitle") or payload.get("title") or ""
    page.description = payload.get("metaDescription") or payload.get("description")
    page.canonical_url = payload.get("canonicalUrl") or payload.get("canonical_url")
    page.og_type = payload.get("ogType") or payload.get("og_type") or "website"
    page.og_title = payload.get("ogTitle") or payload.get("og_title")
    page.og_description = payload.get("ogDescription") or payload.get("og_description")
    page.og_image = payload.get("ogImage") or payload.get("og_image")
    page.twitter_card_type = payload.get("twitterCardType") or payload.get("twitter_card_type") or "summary_large_image"
    page.twitter_title = payload.get("twitterTitle") or payload.get("twitter_title")
    page.twitter_description = payload.get("twitterDescription") or payload.get("twitter_description")
    page.twitter_image = payload.get("twitterImage") or payload.get("twitter_image")
    page.no_index = bool(payload.get("noIndex") or payload.get("no_index"))
    page.no_follow = bool(payload.get("noFollow") or payload.get("no_follow"))
    page.schema = payload.get("schema")

    await page.save(db)
    return _page_to_dict(page)


@router.delete("/api/admin/seo/pages")
async def delete_seo_page(slug: str = Query(...), user=Depends(require_staff), db: AsyncSession = Depends(get_db)):
    page = await SEOPage.objects(db).filter(page_slug=slug).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    await page.delete(db)
    return {"success": True}


@router.get("/api/admin/seo/redirects")
async def list_admin_redirects(user=Depends(require_staff), db: AsyncSession = Depends(get_db)):
    redirects = await SEORedirect.objects(db).order_by("id", "ASC").all()
    return [_redirect_to_dict(r) for r in redirects]


@router.post("/api/admin/seo/redirects")
async def add_redirect(payload: dict, user=Depends(require_staff), db: AsyncSession = Depends(get_db)):
    r = SEORedirect(
        from_url=payload.get("from") or "",
        to_url=payload.get("to") or "",
        type=str(payload.get("type", "301")),
    )
    await r.save(db)
    return _redirect_to_dict(r)


@router.delete("/api/admin/seo/redirects/{redirect_id}")
async def delete_redirect(redirect_id: int, user=Depends(require_staff), db: AsyncSession = Depends(get_db)):
    r = await SEORedirect.objects(db).filter(id=redirect_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Redirect not found")
    await r.delete(db)
    return {"success": True}


@router.get("/api/admin/seo/scripts")
async def get_seo_scripts(user=Depends(require_staff), db: AsyncSession = Depends(get_db)):
    from apps.settings.models import SiteSetting
    import json
    setting = await SiteSetting.objects(db).filter(key="seo_scripts").first()
    try:
        data = json.loads(setting.value) if setting and setting.value else {}
    except Exception:
        data = {}
    return {"headerScripts": data.get("headerScripts", ""), "footerScripts": data.get("footerScripts", "")}


@router.post("/api/admin/seo/scripts")
async def update_seo_scripts(payload: dict, user=Depends(require_staff), db: AsyncSession = Depends(get_db)):
    from apps.settings.models import SiteSetting
    import json
    setting = await SiteSetting.objects(db).filter(key="seo_scripts").first()
    if setting:
        setting.value = json.dumps(payload)
        await setting.save(db)
    else:
        await SiteSetting(key="seo_scripts", value=json.dumps(payload)).save(db)
    return {"success": True}


@router.get("/api/admin/seo/sitemap")
async def get_sitemap_config(user=Depends(require_staff), db: AsyncSession = Depends(get_db)):
    from apps.settings.models import SiteSetting
    import json
    setting = await SiteSetting.objects(db).filter(key="seo_sitemap").first()
    default = {
        "enabled": True, "frequency": "daily", "priority": 0.8,
        "excludeSlugs": [], "staticPaths": [], "maxUrlsPerSitemap": 50000, "modelSlugs": []
    }
    try:
        data = json.loads(setting.value) if setting and setting.value else default
    except Exception:
        data = default
    return data


@router.post("/api/admin/seo/sitemap")
async def update_sitemap_config(payload: dict, user=Depends(require_staff), db: AsyncSession = Depends(get_db)):
    from apps.settings.models import SiteSetting
    import json
    setting = await SiteSetting.objects(db).filter(key="seo_sitemap").first()
    if setting:
        setting.value = json.dumps(payload)
        await setting.save(db)
    else:
        await SiteSetting(key="seo_sitemap", value=json.dumps(payload)).save(db)
    return {"success": True}


@router.post("/api/admin/seo/upload")
async def upload_seo_image(
    slug: str = Query(...),
    type: str = Query(...),
    file: UploadFile = File(...),
    user=Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    if type not in ["og", "twitter"]:
        raise HTTPException(status_code=400, detail="type must be 'og' or 'twitter'")
    upload_dir = Path(__file__).resolve().parent.parent.parent / "uploads" / "seo"
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    safe_slug = slug.strip("/").replace("/", "_")
    filename = f"{safe_slug}_{type}{ext}"
    dest = upload_dir / filename
    content = await file.read()
    dest.write_bytes(content)
    url = f"/uploads/seo/{filename}"

    page = await SEOPage.objects(db).filter(page_slug=slug).first()
    if not page:
        page = SEOPage(page_slug=slug)
    if type == "og":
        page.og_image = url
    else:
        page.twitter_image = url
    await page.save(db)
    return {"success": True, "url": url}


@router.post("/api/admin/seo/backup")
async def backup_seo(
    drive: bool = Query(False),
    user=Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    pages = await SEOPage.objects(db).all()
    redirects = await SEORedirect.objects(db).all()
    robots = await SEORobots.objects(db).first()
    data = {
        "pages": [_page_to_dict(p) for p in pages],
        "redirects": [_redirect_to_dict(r) for r in redirects],
        "robots": robots.content if robots else "",
    }
    if drive:
        # Google Drive upload is not yet implemented — silently skip
        pass
    return data


@router.post("/api/admin/seo/restore")
async def restore_seo(
    file: UploadFile = File(...),
    user=Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    import json
    content = await file.read()
    try:
        data = json.loads(content)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON backup file")

    for page_data in (data.get("pages") or []):
        slug = page_data.get("pageSlug", "")
        if not slug:
            continue
        page = await SEOPage.objects(db).filter(page_slug=slug).first()
        if not page:
            page = SEOPage(page_slug=slug)
        page.title = page_data.get("metaTitle", "")
        page.description = page_data.get("metaDescription")
        page.canonical_url = page_data.get("canonicalUrl")
        page.og_type = page_data.get("ogType", "website")
        page.og_title = page_data.get("ogTitle")
        page.og_description = page_data.get("ogDescription")
        page.og_image = page_data.get("ogImage")
        page.twitter_card_type = page_data.get("twitterCardType", "summary_large_image")
        page.twitter_title = page_data.get("twitterTitle")
        page.twitter_description = page_data.get("twitterDescription")
        page.twitter_image = page_data.get("twitterImage")
        page.no_index = bool(page_data.get("noIndex"))
        page.no_follow = bool(page_data.get("noFollow"))
        page.schema = page_data.get("schema")
        await page.save(db)

    for r_data in (data.get("redirects") or []):
        r = SEORedirect(
            from_url=r_data.get("from", ""),
            to_url=r_data.get("to", ""),
            type=str(r_data.get("type", "301")),
        )
        await r.save(db)

    robots_content = data.get("robots", "")
    if robots_content:
        robots = await SEORobots.objects(db).first()
        if not robots:
            robots = SEORobots(content=robots_content)
        else:
            robots.content = robots_content
        await robots.save(db)

    return {"success": True, "message": "SEO data restored successfully"}
