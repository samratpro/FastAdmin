from typing import Type, TypeVar, Generic, List, Any, Dict, Optional
from sqlalchemy import select, update, delete, and_, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import Base

T = TypeVar("T")

class QuerySet(Generic[T]):
    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session
        self._query = select(model)
        self._filters = {}
        self._order_by = None
        self._limit = None
        self._offset = None

    def filter(self, **kwargs) -> "QuerySet[T]":
        for key, value in kwargs.items():
            self._filters[key] = value
        # Rebuild query with where clause
        self._query = select(self.model).where(
            and_(*[getattr(self.model, k) == v for k, v in self._filters.items()])
        )
        return self

    def order_by(self, field: str, direction: str = "ASC") -> "QuerySet[T]":
        attr = getattr(self.model, field)
        self._query = self._query.order_by(asc(attr) if direction == "ASC" else desc(attr))
        return self

    def limit(self, count: int) -> "QuerySet[T]":
        self._limit = count
        return self

    def offset(self, count: int) -> "QuerySet[T]":
        self._offset = count
        return self

    async def all(self) -> List[T]:
        stmt = self._query
        if self._limit is not None:
            stmt = stmt.limit(self._limit)
        if self._offset is not None:
            stmt = stmt.offset(self._offset)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def first(self) -> Optional[T]:
        stmt = self._query.limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count(self) -> int:
        from sqlalchemy import func
        stmt = select(func.count()).select_from(self.model).where(
            and_(*[getattr(self.model, k) == v for k, v in self._filters.items()])
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def delete(self) -> int:
        stmt = delete(self.model).where(
            and_(*[getattr(self.model, k) == v for k, v in self._filters.items()])
        )
        result = await self.session.execute(stmt)
        return result.rowcount

class Model(Base):
    """
    Base class for all models.
    Extends SQLAlchemy DeclarativeBase.
    """
    __abstract__ = True

    @classmethod
    def objects(cls, session: AsyncSession) -> QuerySet:
        return QuerySet(cls, session)

    def to_dict(self) -> dict:
        from sqlalchemy import inspect as sa_inspect
        return {
            c.key: getattr(self, c.key)
            for c in sa_inspect(self.__class__).mapper.column_attrs
        }

    async def save(self, session: AsyncSession):
        session.add(self)
        await session.commit()
        await session.refresh(self)

    async def delete(self, session: AsyncSession):
        await session.delete(self)
        await session.commit()
