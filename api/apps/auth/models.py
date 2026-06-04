from sqlalchemy import Column, Integer, String, Boolean, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base
from common.orm import Model
from core.registry import register_admin

class UserPermission(Base):
    __tablename__ = "user_permissions"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), primary_key=True)

class GroupPermission(Base):
    __tablename__ = "group_permissions"
    group_id = Column(Integer, ForeignKey("groups.id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), primary_key=True)

class UserGroup(Base):
    __tablename__ = "user_groups"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), primary_key=True)

@register_admin(
    app_name="auth", display_name="Users",
    list_display=["id", "username", "email", "is_staff", "is_superuser", "is_active"],
    search_fields=["username", "email"],
    exclude_fields=["password"],
    icon="users",
)
class User(Model):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(150), unique=True, nullable=False)
    email = Column(String(254), unique=True, nullable=False)
    password = Column(String, nullable=False)
    first_name = Column(String(150), nullable=True)
    last_name = Column(String(150), nullable=True)
    is_active = Column(Boolean, default=False)
    is_staff = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    date_joined = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    permissions = relationship("Permission", secondary="user_permissions")
    groups = relationship("Group", secondary="user_groups")

@register_admin(app_name="auth", display_name="Groups", list_display=["id", "name", "description"], icon="shield")
class Group(Model):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), unique=True, nullable=False)
    description = Column(String, nullable=True)

    permissions = relationship("Permission", secondary="group_permissions")

@register_admin(app_name="auth", display_name="Permissions", list_display=["id", "name", "codename", "model_name"])
class Permission(Model):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    codename = Column(String(100), unique=True, nullable=False)
    model_name = Column(String(100), nullable=True)
