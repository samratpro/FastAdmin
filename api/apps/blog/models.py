from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base
from common.orm import Model
from core.registry import register_admin

@register_admin(
    app_name="Blog",
    display_name="Categories",
    list_display=["name", "slug"]
)
class Category(Model):
    __tablename__ = "blog_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    posts = relationship("BlogPost", back_populates="category")

@register_admin(
    app_name="Blog",
    display_name="Posts",
    list_display=["title", "slug", "published"]
)
class BlogPost(Model):
    __tablename__ = "blog_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    excerpt = Column(Text, nullable=True)
    content = Column(Text, nullable=False) # Store Editor.js JSON
    featured_image = Column(String(500), nullable=True)
    meta_title = Column(String(60), nullable=True)
    meta_description = Column(String(160), nullable=True)
    schema = Column(Text, nullable=True) # JSON-LD
    category_id = Column(Integer, ForeignKey("blog_categories.id"), nullable=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    published = Column(Boolean, default=False)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("Category", back_populates="posts")
    author = relationship("User")
