from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

import app.main as main
from app.database import SessionLocal, Redirect


def _add(name, url):
    with SessionLocal() as db:
        db.add(Redirect(name=name, target_url=url))
        db.commit()


def _mock_httpx(target):
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value.url = target
    return patch.object(main.httpx, "Client", return_value=mock_client)


def test_dynamic_redirect_simple():
    _add("web", "https://example.com")
    with _mock_httpx("https://example.com"):
        resp = main.dynamic_redirect("web")
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://example.com"


def test_dynamic_redirect_404():
    with pytest.raises(HTTPException) as exc:
        main.dynamic_redirect("no-exists")
    assert exc.value.status_code == 404


def test_dynamic_redirect_reredirect_chain():
    _add("real", "https://example.com")
    _add("f", "@reredirect:real")
    with _mock_httpx("https://example.com"):
        resp = main.dynamic_redirect("f")
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://example.com"


def test_dynamic_redirect_cycle():
    with SessionLocal() as db:
        db.add(Redirect(name="a", target_url="@reredirect:b"))
        db.add(Redirect(name="b", target_url="@reredirect:a"))
        db.commit()
    resp = main.dynamic_redirect("a")
    assert resp.status_code == 404
    assert "Ciclo" in resp.body.decode()


def test_dynamic_redirect_broken_target():
    _add("f", "@reredirect:missing")
    resp = main.dynamic_redirect("f")
    assert resp.status_code == 404
    assert "ya no existe" in resp.body.decode()


def test_dynamic_redirect_head():
    _add("web", "https://example.com")
    with _mock_httpx("https://example.com"):
        resp = main.dynamic_redirect_head("web")
    assert resp.status_code == 302
