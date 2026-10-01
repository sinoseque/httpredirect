import json
import re

import httpx

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .config import ACESTREAM_BASE, REDIRECT_NAME, logger, FETCH_TIMEOUT_SECONDS, MAX_PASTE_JSON_SIZE
from .database import RedirectRepository, SessionLocal

PAGE_SIZE = 10


def normalize_name(title):
    name = title.lower()
    name = name.replace('*', 'o').replace('&', 'y').replace('@', 'a').replace('#', 'h')
    name = re.sub(r'[^a-z0-9\- ]', '', name)
    name = name.strip().replace(' ', '-')
    name = re.sub(r'-+', '-', name)
    return name


def _resolve_duplicates(items):
    seen = {}
    resolved = []
    for name, target_url in items:
        if name in seen:
            seen[name] += 1
            resolved.append((f"{name}-{seen[name]}", target_url))
        else:
            seen[name] = 0
            resolved.append((name, target_url))
    return resolved


def _build_paged_page(links, page, item_prefix, nav_prefix, title):
    total_pages = (len(links) + PAGE_SIZE - 1) // PAGE_SIZE
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_links = links[start:end]

    buttons = [InlineKeyboardButton(name, callback_data=f"{item_prefix}:{name}") for name, _ in page_links]
    keyboard = [buttons[i:i+2] for i in range(0, len(buttons), 2)]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Anterior", callback_data=f"{nav_prefix}:{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Siguiente ▶️", callback_data=f"{nav_prefix}:{page+1}"))
    if nav:
        keyboard.append(nav)

    text = (
        f"{title}\n"
        f"Página {page+1}/{total_pages}"
    )
    return text, InlineKeyboardMarkup(keyboard)


def _build_reredirect_page(links, page):
    return _build_paged_page(links, page, "reredirect", "reredirect_page", "🎯 **Selecciona la ruta a la que quieres que apunte `{REDIRECT_NAME}`:**")


def _build_delete_page(links, page):
    return _build_paged_page(links, page, "delete_select", "delete_page", "🗑 **Selecciona la ruta que quieres borrar:**")


def _build_redirect_list_parts(links):
    lines = [f"🔹 `{l.name}` ➔ {l.target_url}" for l in links]
    header = "🛰 **Rutas actuales:**\n\n"
    max_len = 4000

    parts = []
    current = header
    for line in lines:
        candidate = current + line + "\n"
        if len(candidate) > max_len:
            parts.append(current)
            current = header + line + "\n"
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


async def _send_list_parts(parts, send_first, send_rest):
    await send_first(parts[0])
    for part in parts[1:]:
        await send_rest(part)


async def _fetch_json(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url, timeout=FETCH_TIMEOUT_SECONDS,
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True
        )
        logger.debug("GET %s -> status %d", url, resp.status_code)
        logger.debug("Respuesta: %s", resp.text[:500])
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if content_type and "json" not in content_type.lower():
            raise ValueError(f"Content-type no esperado: {content_type}")
        return resp.json()


async def _upsert_redirects(items):
    async with SessionLocal() as db:
        repo = RedirectRepository(db)
        try:
            await repo.upsert_many(items)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
    return len(items)


async def import_from_json_hashes(data):
    if not ACESTREAM_BASE:
        raise ValueError("URL_BASE_ACESTREAM no está definida.")
    items = []
    for item in data.get("hashes", []):
        title = item.get("title", "")
        hash_id = item.get("hash", "")
        if not title or not hash_id:
            continue
        name = normalize_name(title)
        if not name:
            continue
        items.append((name, f"{ACESTREAM_BASE}{hash_id}"))
    items = _resolve_duplicates(items)
    return await _upsert_redirects(items)


async def import_from_json_simple(data):
    if not ACESTREAM_BASE:
        raise ValueError("URL_BASE_ACESTREAM no está definida.")
    items = []
    for item in data:
        name = normalize_name(item.get("name", ""))
        ace_id = item.get("ace_id", "")
        if not name or not ace_id:
            continue
        items.append((name, f"{ACESTREAM_BASE}{ace_id}"))
    items = _resolve_duplicates(items)
    return await _upsert_redirects(items)
