import pytest
from sqlalchemy import select

import app.helpers as helpers
from app.database import SessionLocal, Redirect
from app.database import RedirectRepository


def _repo(session):
    return RedirectRepository(session)


async def test_upsert_creates_and_updates():
    async with SessionLocal() as db:
        repo = _repo(db)
        await repo.upsert("canal", "https://ex.com")
        await db.commit()
        assert (await repo.find_by_name("canal")).target_url == "https://ex.com"
        await repo.upsert("canal", "https://other.com")
        await db.commit()
        assert (await repo.find_by_name("canal")).target_url == "https://other.com"


async def test_upsert_many_returns_count_and_persists():
    async with SessionLocal() as db:
        repo = _repo(db)
        count = await repo.upsert_many([("a", "u1"), ("b", "u2")])
        await db.commit()
    assert count == 2
    async with SessionLocal() as db:
        result = await db.execute(select(Redirect))
        names = {row.name for row in result.scalars().all()}
    assert names == {"a", "b"}


async def test_delete_by_name_returns_flag():
    async with SessionLocal() as db:
        repo = _repo(db)
        await repo.upsert("x", "u")
        await db.commit()
    async with SessionLocal() as db:
        repo = _repo(db)
        assert await repo.delete_by_name("x") is True
        await db.commit()
    async with SessionLocal() as db:
        repo = _repo(db)
        assert await repo.find_by_name("x") is None
        assert await repo.delete_by_name("x") is False


async def test_delete_all_counts_and_clears():
    async with SessionLocal() as db:
        repo = _repo(db)
        await repo.upsert_many([("a", "u1"), ("b", "u2"), ("c", "u3")])
        await db.commit()
        removed = await repo.delete_all()
        await db.commit()
    assert removed == 3
    async with SessionLocal() as db:
        repo = _repo(db)
        assert await repo.all() == []


async def test_filter_excludes_name():
    async with SessionLocal() as db:
        repo = _repo(db)
        await repo.upsert_many([("keep", "u1"), ("f", "u2")])
        await db.commit()
        others = [l for l in await repo.all() if l.name != "f"]
    assert [l.name for l in others] == ["keep"]


async def test_upsert_many_counts_generator():
    async with SessionLocal() as db:
        repo = _repo(db)
        gen = ((f"k{i}", f"u{i}") for i in range(5))
        count = await repo.upsert_many(gen)
        await db.commit()
    assert count == 5
    async with SessionLocal() as db:
        assert await repo.count() == 5


async def test_upsert_redirects_rolls_back_on_failure(monkeypatch):
    async with SessionLocal() as db:
        original = RedirectRepository.upsert
        state = {"n": 0}

        async def flaky_upsert(self, name, target_url):
            state["n"] += 1
            if state["n"] == 2:
                raise RuntimeError("boom")
            return await original(self, name, target_url)

        monkeypatch.setattr(RedirectRepository, "upsert", flaky_upsert)
        with pytest.raises(RuntimeError):
            await helpers._upsert_redirects([("a", "u1"), ("b", "u2")])

    async with SessionLocal() as db:
        repo = _repo(db)
        assert await repo.count() == 0
