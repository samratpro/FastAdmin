from sqlalchemy import Column, Integer, String, Text
from core.database import Base
from common.orm import Model


class SiteSetting(Model):
    __tablename__ = "site_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)

# Predefined settings keys
REQUIRED_SETTINGS = [
    "siteTitle", "tagline", "logoUrl", "faviconUrl",
    "footerText", "contactEmail", "phone", "siteUrl", "primaryColor"
]
