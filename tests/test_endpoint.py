from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import select

import app.main as main
from app.database import SessionLocal, Redirect


async def _add(name, url):
    async with SessionLocal() as db:
        db.add(Redirect(name=name, target_url=url))
        await db.commit()


def _mock_httpx(target):
    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, **kwargs):
            resp = MagicMock()
            resp.url = target
            resp.status_code = 200
            return resp

    return patch.object(main.httpx, "AsyncClient", return_value=_Client())


async def test_dynamic_redirect_simple():
    await _add("web", "https://example.com")
    with _mock_httpx("https://example.com"):
        resp = await main.dynamic_redirect("web")
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://example.com"


async def test_dynamic_redirect_404():
    with pytest.raises(HTTPException) as exc:
        await main.dynamic_redirect("no-exists")
    assert exc.value.status_code == 404


async def test_dynamic_redirect_reredirect_chain():
    await _add("real", "https://example.com")
    await _add("f", "@reredirect:real")
    with _mock_httpx("https://example.com"):
        resp = await main.dynamic_redirect("f")
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://example.com"


async def test_dynamic_redirect_cycle():
    async with SessionLocal() as db:
        db.add(Redirect(name="a", target_url="@reredirect:b"))
        db.add(Redirect(name="b", target_url="@reredirect:a"))
        await db.commit()
    resp = await main.dynamic_redirect("a")
    assert resp.status_code == 404
    assert "Ciclo" in resp.body.decode()


async def test_dynamic_redirect_broken_target():
    await _add("f", "@reredirect:missing")
    resp = await main.dynamic_redirect("f")
    assert resp.status_code == 404
    assert "ya no existe" in resp.body.decode()


async def test_dynamic_redirect_head():
    await _add("web", "https://example.com")
    with _mock_httpx("https://example.com"):
        resp = await main.dynamic_redirect_head("web")
    assert resp.status_code == 302


async def test_health_reports_route_count():
    await _add("web", "https://example.com")
    await _add("other", "https://example.org")
    assert await main.health() == {"status": "ok", "routes": 2}


async def test_health_empty():
    assert (await main.health())["routes"] == 0
