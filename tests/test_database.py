from sqlalchemy import text

from app.database import engine, Base


async def test_table_created_on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        exists = await conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='redirects'"
            )
        )
    assert exists.first() is not None


async def test_schema_create_all_is_idempotent():
    from app.database import Redirect
    from sqlalchemy import delete

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("DELETE FROM redirects"))
        await conn.commit()


async def test_sqlite_wal_pragma_applied():
    def _check(c):
        return c.exec_driver_sql("PRAGMA journal_mode").fetchone()[0]

    async with engine.connect() as conn:
        mode = await conn.run_sync(_check)
    assert mode == "wal"
