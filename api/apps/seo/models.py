from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base
from common.orm import Model
from core.registry import register_admin

@register_admin(
    app_name="SEO",
    display_name="SEO Pages",
    list_display=["page_slug", "title"]
)
class SEOPage(Model):
    __tablename__ = "seo_pages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    page_slug = Column(String(255), unique=True, nullable=False)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    schema = Column(Text, nullable=True)
    og_type = Column(String(50), nullable=True, default="website")
    og_title = Column(String(255), nullable=True)
    og_description = Column(Text, nullable=True)
    og_image = Column(String(500), nullable=True)
    twitter_card_type = Column(String(50), nullable=True, default="summary_large_image")
    twitter_title = Column(String(255), nullable=True)
    twitter_description = Column(Text, nullable=True)
    twitter_image = Column(String(500), nullable=True)
    canonical_url = Column(String(500), nullable=True)
    no_index = Column(Boolean, default=False)
    no_follow = Column(Boolean, default=False)

class SEORobots(Model):
    __tablename__ = "seo_robots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow) # Needs import

class SEORedirect(Model):
    __tablename__ = "seo_redirects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    from_url = Column(String(500), nullable=False)
    to_url = Column(String(500), nullable=True)
    type = Column(String(10), default="301") # 301 or 410
    created_at = Column(DateTime, default=datetime.utcnow)
