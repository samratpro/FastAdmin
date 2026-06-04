"""Initial schema — all tables

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── auth ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password", sa.String(), nullable=False),
        sa.Column("first_name", sa.String(length=150), nullable=True),
        sa.Column("last_name", sa.String(length=150), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_staff", sa.Boolean(), nullable=True),
        sa.Column("is_superuser", sa.Boolean(), nullable=True),
        sa.Column("date_joined", sa.DateTime(), nullable=True),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )

    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("codename", sa.String(length=100), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codename"),
    )

    op.create_table(
        "user_permissions",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "permission_id"),
    )

    op.create_table(
        "user_groups",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "group_id"),
    )

    op.create_table(
        "group_permissions",
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
        sa.PrimaryKeyConstraint("group_id", "permission_id"),
    )

    # ── settings ──────────────────────────────────────────────────────────────
    op.create_table(
        "site_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    # ── seo ───────────────────────────────────────────────────────────────────
    op.create_table(
        "seo_pages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("page_slug", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("schema", sa.Text(), nullable=True),
        sa.Column("og_type", sa.String(length=50), nullable=True),
        sa.Column("og_title", sa.String(length=255), nullable=True),
        sa.Column("og_description", sa.Text(), nullable=True),
        sa.Column("og_image", sa.String(length=500), nullable=True),
        sa.Column("twitter_card_type", sa.String(length=50), nullable=True),
        sa.Column("twitter_title", sa.String(length=255), nullable=True),
        sa.Column("twitter_description", sa.Text(), nullable=True),
        sa.Column("twitter_image", sa.String(length=500), nullable=True),
        sa.Column("canonical_url", sa.String(length=500), nullable=True),
        sa.Column("no_index", sa.Boolean(), nullable=True),
        sa.Column("no_follow", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("page_slug"),
    )

    op.create_table(
        "seo_robots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "seo_redirects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("from_url", sa.String(length=500), nullable=False),
        sa.Column("to_url", sa.String(length=500), nullable=True),
        sa.Column("type", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── blog ──────────────────────────────────────────────────────────────────
    op.create_table(
        "blog_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "blog_posts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("featured_image", sa.String(length=500), nullable=True),
        sa.Column("meta_title", sa.String(length=60), nullable=True),
        sa.Column("meta_description", sa.String(length=160), nullable=True),
        sa.Column("schema", sa.Text(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("published", sa.Boolean(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["blog_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )


def downgrade() -> None:
    op.drop_table("blog_posts")
    op.drop_table("blog_categories")
    op.drop_table("seo_redirects")
    op.drop_table("seo_robots")
    op.drop_table("seo_pages")
    op.drop_table("site_settings")
    op.drop_table("group_permissions")
    op.drop_table("user_groups")
    op.drop_table("user_permissions")
    op.drop_table("permissions")
    op.drop_table("groups")
    op.drop_table("users")
