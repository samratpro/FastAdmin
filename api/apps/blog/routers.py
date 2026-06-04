from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from apps.blog.models import BlogPost, Category
from typing import List, Optional

router = APIRouter(prefix="/api/public", tags=["Public Blog"])

@router.get("/posts")
async def list_posts(
    category_slug: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List published blog posts."""
    qs = BlogPost.objects(db).filter(published=True)

    if category_slug:
        # Find category first
        cat = await Category.objects(db).filter(slug=category_slug).first()
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
        qs = qs.filter(category_id=cat.id)

    posts = await qs.limit(limit).offset(offset).all()

    return {
        "success": True,
        "data": posts
    }

@router.get("/posts/{slug}")
async def get_post(slug: str, db: AsyncSession = Depends(get_db)):
    """Get a single post by slug."""
    post = await BlogPost.objects(db).filter(slug=slug).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return {
        "success": True,
        "data": post
    }

@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    """List all categories."""
    categories = await Category.objects(db).all()
    return {
        "success": True,
        "data": categories
    }
