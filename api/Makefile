# FastAdmin — migration helpers (Django-style)
# Usage:
#   make migrations msg="add view_count to blog_posts"
#   make migrate
#   make rollback
#   make history
#   make current

msg ?= auto

migrations:
	alembic revision --autogenerate -m "$(msg)"

migrate:
	alembic upgrade head

rollback:
	alembic downgrade -1

history:
	alembic history

current:
	alembic current

.PHONY: migrations migrate rollback history current
