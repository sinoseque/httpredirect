from typing import Optional, Tuple

from sqlalchemy import Column, String, select, func, delete, event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

from .config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


class Redirect(Base):
    __tablename__ = "redirects"
    name = Column(String, primary_key=True, index=True)
    target_url = Column(String)


class RedirectRepository:
    """Acceso a la tabla `redirects` desde una sesión asíncrona.

    Cada operación vive dentro de `async with SessionLocal() as db:` así que la
    sesión nunca se comparte entre hilos ni entre peticiones.
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def find_by_name(self, name: str) -> Optional[Redirect]:
        return await self._db.get(Redirect, name)

    async def all(self) -> list[Redirect]:
        result = await self._db.execute(select(Redirect))
        return result.scalars().all()

    async def upsert(self, name: str, target_url: str) -> None:
        link = await self.find_by_name(name)
        if link:
            link.target_url = target_url
        else:
            self._db.add(Redirect(name=name, target_url=target_url))

    async def upsert_many(self, items) -> int:
        count = 0
        for name, target_url in items:
            await self.upsert(name, target_url)
            count += 1
        return count

    async def delete_by_name(self, name: str) -> bool:
        link = await self.find_by_name(name)
        if link:
            await self._db.delete(link)
            return True
        return False

    async def count(self) -> int:
        result = await self._db.execute(select(func.count()).select_from(Redirect))
        return result.scalar_one()

    async def delete_all(self) -> int:
        result = await self._db.execute(delete(Redirect))
        return result.rowcount
