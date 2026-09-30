import app.main as main
from app.main import _build_paged_page, _build_redirect_list_parts
from app.database import Redirect


def test_normalize_name_basic():
    assert main.normalize_name("Mi Web") == "mi-web"


def test_normalize_name_special_chars():
    assert main.normalize_name("Café & Co@2024") == "caf-y-coa2024"


def test_normalize_name_multiple_dashes():
    assert main.normalize_name("hola   ---  mundo") == "hola-mundo"


def test_resolve_duplicates():
    items = [("canal1", "u1"), ("canal1", "u2"), ("canal2", "u3")]
    assert main._resolve_duplicates(items) == [
        ("canal1", "u1"),
        ("canal1-1", "u2"),
        ("canal2", "u3"),
    ]


def test_build_paged_page_single_page():
    links = [("a", "u"), ("b", "u")]
    text, markup = _build_paged_page(links, 0, "item", "nav", "titulo")
    assert "titulo" in text
    assert "Página 1/1" in text
    callbacks = [b.callback_data for row in markup.inline_keyboard for b in row]
    assert "item:a" in callbacks
    assert "item:b" in callbacks


def test_build_paged_page_navigation():
    links = [(f"n{i}", "u") for i in range(12)]
    text, markup = _build_paged_page(links, 0, "item", "nav", "titulo")
    assert "Página 1/2" in text
    callbacks = [b.callback_data for row in markup.inline_keyboard for b in row]
    assert "item:n0" in callbacks
    assert "nav:1" in callbacks


def test_build_redirect_list_parts():
    links = [
        Redirect(name="a", target_url="http://x"),
        Redirect(name="b", target_url="http://y"),
    ]
    parts = _build_redirect_list_parts(links)
    assert len(parts) >= 1
    assert parts[0].startswith("🛰")
