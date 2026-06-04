from typing import Any, Dict, List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from common.orm import Model

class QuerySet:
    def __init__(self, model: Type[Model], session: AsyncSession):
        self.model = model
        self.session = session
        self._filters = {}
        self._order_by = None
        self._order_direction = "ASC"
        self._limit = None
        self._offset = None

    def filter(self, **kwargs) -> "QuerySet":
        self._filters.update(kwargs)
        return self

    def order_by(self, field: str, direction: str = "ASC") -> "QuerySet":
        self._order_by = field
        self._order_direction = direction
        return self

    def limit(self, count: int) -> "QuerySet":
        self._limit = count
        return self

    def offset(self, count: int) -> "QuerySet":
        self._offset = count
        return self

    async def all(self) -> List[Any]:
        stmt = select(self.model)

        if self._filters:
            conditions = [getattr(self.model, k) == v for k, v in self._filters.items()]
            stmt = stmt.where(and_(*conditions))

        if self._order_by:
            attr = getattr(self.model, self._order_by)
            stmt = stmt.order_by(asc(attr) if self._order_direction == "ASC" else desc(attr))

        if self._limit is not None:
            stmt = stmt.limit(self._limit)

        if self._offset is not None:
            stmt = stmt.offset(self._offset)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        stmt = select(func.count()).select_from(self.model)
        if self._filters:
            conditions = [getattr(self.model, k) == v for k, v in self._filters.items()]
            stmt = stmt.where(and_(*conditions))
        result = await self.session.execute(stmt)
        return result.scalar_one()
