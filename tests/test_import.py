import pytest
from unittest.mock import patch
from sqlalchemy import select

import app.main as main
import app.helpers as helpers
from app.database import SessionLocal, Redirect


async def _names_to_urls():
    async with SessionLocal() as db:
        result = await db.execute(select(Redirect))
        return {l.name: l.target_url for l in result.scalars().all()}


async def test_import_from_json_hashes():
    data = {"hashes": [{"title": "Canal Uno", "hash": "abc123"}, {"title": "", "hash": "x"}]}
    count = await main.import_from_json_hashes(data)
    links = await _names_to_urls()
    assert count == 1
    assert "canal-uno" in links
    assert links["canal-uno"] == main.ACESTREAM_BASE + "abc123"


async def test_import_from_json_hashes_requires_base():
    with patch.object(helpers, "ACESTREAM_BASE", ""):
        with pytest.raises(ValueError):
            await main.import_from_json_hashes({"hashes": [{"title": "x", "hash": "y"}]})


async def test_import_from_json_simple():
    data = [{"name": "canal1", "ace_id": "abc"}, {"name": "bad"}]
    count = await main.import_from_json_simple(data)
    links = await _names_to_urls()
    assert count == 1
    assert links["canal1"] == main.ACESTREAM_BASE + "abc"


async def test_import_from_json_simple_requires_base():
    with patch.object(helpers, "ACESTREAM_BASE", ""):
        with pytest.raises(ValueError):
            await main.import_from_json_simple([{"name": "x", "ace_id": "y"}])


async def test_import_upserts_existing():
    async with SessionLocal() as db:
        db.add(Redirect(name="c", target_url="http://old"))
        await db.commit()
    count = await main.import_from_json_simple([{"name": "c", "ace_id": "new1"}])
    assert count == 1
    assert (await _names_to_urls())["c"] == main.ACESTREAM_BASE + "new1"


async def test_import_simple_resolves_duplicates():
    await main.import_from_json_simple([
        {"name": "dup", "ace_id": "1"},
        {"name": "dup", "ace_id": "2"},
    ])
    async with SessionLocal() as db:
        result = await db.execute(select(Redirect))
        names = [l.name for l in result.scalars().all()]
    assert names == ["dup", "dup-1"]


async def test_import_hashes_skips_empty_name():
    data = {"hashes": [{"title": "!!!$$$", "hash": "abc123"}]}
    count = await main.import_from_json_hashes(data)
    links = await _names_to_urls()
    assert count == 0
    assert links == {}


async def test_import_simple_normalizes_name():
    await main.import_from_json_simple([{"name": "Canal Dos", "ace_id": "abc"}])
    async with SessionLocal() as db:
        result = await db.execute(select(Redirect))
        names = [l.name for l in result.scalars().all()]
    assert names == ["canal-dos"]
