import pytest
from unittest.mock import patch

import app.main as main
from app.database import SessionLocal, Redirect


def _names_to_urls():
    with SessionLocal() as db:
        return {l.name: l.target_url for l in db.query(Redirect).all()}


def test_import_from_json_hashes():
    data = {"hashes": [{"title": "Canal Uno", "hash": "abc123"}, {"title": "", "hash": "x"}]}
    with SessionLocal() as db:
        count = main.import_from_json_hashes(data)
        links = {l.name: l.target_url for l in db.query(Redirect).all()}
    assert count == 1
    assert "canal-uno" in links
    assert links["canal-uno"] == main.ACESTREAM_BASE + "abc123"


def test_import_from_json_hashes_requires_base():
    with patch.object(main, "ACESTREAM_BASE", ""):
        with pytest.raises(ValueError):
            main.import_from_json_hashes({"hashes": [{"title": "x", "hash": "y"}]})


def test_import_from_json_simple():
    data = [{"name": "canal1", "ace_id": "abc"}, {"name": "bad"}]
    with SessionLocal() as db:
        count = main.import_from_json_simple(data)
        links = {l.name: l.target_url for l in db.query(Redirect).all()}
    assert count == 1
    assert links["canal1"] == main.ACESTREAM_BASE + "abc"


def test_import_from_json_simple_requires_base():
    with patch.object(main, "ACESTREAM_BASE", ""):
        with pytest.raises(ValueError):
            main.import_from_json_simple([{"name": "x", "ace_id": "y"}])


def test_import_upserts_existing():
    with SessionLocal() as db:
        db.add(Redirect(name="c", target_url="http://old"))
        db.commit()
    count = main.import_from_json_simple([{"name": "c", "ace_id": "new1"}])
    assert count == 1
    assert _names_to_urls()["c"] == main.ACESTREAM_BASE + "new1"


def test_import_simple_resolves_duplicates():
    main.import_from_json_simple([
        {"name": "dup", "ace_id": "1"},
        {"name": "dup", "ace_id": "2"},
    ])
    with SessionLocal() as db:
        names = [l.name for l in db.query(Redirect).all()]
    assert names == ["dup", "dup-1"]
