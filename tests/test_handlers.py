import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select

from app.config import ALLOWED_ID
from app.database import SessionLocal, Redirect


def _cmd_update(args=(), user_id=ALLOWED_ID):
    update = MagicMock()
    update.effective_user.id = user_id
    update.callback_query = None
    update.effective_message = MagicMock()
    update.effective_message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = list(args)
    context.user_data = {}
    return update, context


def _cb_update(callback_data, user_id=ALLOWED_ID):
    update = MagicMock()
    update.effective_user.id = user_id
    callback_query = MagicMock()
    callback_query.answer = AsyncMock()
    callback_query.data = callback_data
    callback_query.edit_message_text = AsyncMock()
    update.callback_query = callback_query
    update.effective_message = MagicMock()
    update.effective_message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = []
    context.user_data = {}
    return update, context


async def _count():
    async with SessionLocal() as db:
        return (await db.execute(select(Redirect))).scalars().all()


# --- start ---

async def test_start_shows_menu():
    from app.handlers.start import start
    update, context = _cmd_update()
    await start(update, context)
    update.effective_message.reply_text.assert_awaited_once()


async def test_start_blocks_unauthorized():
    from app.handlers.start import start
    update, context = _cmd_update(user_id=999999)
    await start(update, context)
    update.effective_message.reply_text.assert_awaited_with("⛔ No autorizado.")


# --- set ---

async def test_set_creates():
    from app.handlers.set import set_cmd
    update, context = _cmd_update(args=["canal", "https://ex.com"])
    await set_cmd(update, context)
    rows = await _count()
    assert len(rows) == 1
    assert rows[0].target_url == "https://ex.com"


async def test_set_updates_existing():
    async with SessionLocal() as db:
        db.add(Redirect(name="canal", target_url="https://old"))
        await db.commit()
    from app.handlers.set import set_cmd
    update, context = _cmd_update(args=["canal", "https://new.com"])
    await set_cmd(update, context)
    rows = await _count()
    assert len(rows) == 1
    assert rows[0].target_url == "https://new.com"


async def test_set_missing_args_reports_error():
    from app.handlers.set import set_cmd
    update, context = _cmd_update(args=["solo"])
    await set_cmd(update, context)
    assert not await _count()
    update.effective_message.reply_text.assert_awaited()


async def test_set_empty_name_rejected():
    from app.handlers.set import set_cmd
    update, context = _cmd_update(args=["", "https://ex.com"])
    await set_cmd(update, context)
    assert not await _count()
    update.effective_message.reply_text.assert_awaited()


async def test_set_captures_exception():
    from app.handlers import set as set_mod
    with patch.object(set_mod.RedirectRepository, "upsert", new=AsyncMock(side_effect=RuntimeError("boom"))):
        update, context = _cmd_update(args=["canal", "https://x"])
        from app.handlers.set import set_cmd
        await set_cmd(update, context)
    update.effective_message.reply_text.assert_awaited_with("❌ Error. Uso: `/set nombre url`")


# --- setace ---

async def test_setace_ok():
    from app.handlers.set import set_acestream
    update, context = _cmd_update(args=["canal", "abc123"])
    await set_acestream(update, context)
    rows = await _count()
    assert rows[0].target_url == "http://acestream.local:6878/ace/getstream?id=abc123"


async def test_setace_missing_base():
    from app.handlers import set as set_mod
    with patch.object(set_mod, "ACESTREAM_BASE", ""):
        update, context = _cmd_update(args=["canal", "abc123"])
        from app.handlers.set import set_acestream
        await set_acestream(update, context)
    update.effective_message.reply_text.assert_awaited_with("❌ Error: `URL_BASE_ACESTREAM` no está definida.")


async def test_setace_missing_args():
    from app.handlers.set import set_acestream
    update, context = _cmd_update(args=["canal"])
    await set_acestream(update, context)
    update.effective_message.reply_text.assert_awaited()


# --- list ---

async def test_list_empty():
    from app.handlers.list import list_cmd
    update, context = _cmd_update()
    await list_cmd(update, context)
    update.effective_message.reply_text.assert_awaited_with("📭 No hay rutas configuradas.")


async def test_list_populated():
    async with SessionLocal() as db:
        db.add(Redirect(name="a", target_url="https://a"))
        await db.commit()
    from app.handlers.list import list_cmd
    update, context = _cmd_update()
    await list_cmd(update, context)
    assert update.effective_message.reply_text.await_count >= 1


# --- del / clear ---

async def test_del_by_name_found():
    async with SessionLocal() as db:
        db.add(Redirect(name="canal", target_url="https://a"))
        await db.commit()
    from app.handlers.delete import del_cmd
    update, context = _cmd_update(args=["canal"])
    await del_cmd(update, context)
    _, kwargs = update.effective_message.reply_text.await_args
    assert kwargs["reply_markup"] is not None


async def test_del_by_name_not_found():
    from app.handlers.delete import del_cmd
    update, context = _cmd_update(args=["noexiste"])
    await del_cmd(update, context)
    update.effective_message.reply_text.assert_awaited_with("❓ No encontré `noexiste`.")


async def test_del_without_name_shows_page():
    async with SessionLocal() as db:
        db.add(Redirect(name="a", target_url="https://a"))
        await db.commit()
    from app.handlers.delete import del_cmd
    update, context = _cmd_update(args=[])
    await del_cmd(update, context)
    assert update.effective_message.reply_text.await_count >= 1


async def test_clear_empty():
    from app.handlers.delete import clear_cmd
    update, context = _cmd_update()
    await clear_cmd(update, context)
    update.effective_message.reply_text.assert_awaited_with("📭 No hay rutas configuradas para borrar.")


async def test_clear_confirm_deletes_all():
    async with SessionLocal() as db:
        db.add(Redirect(name="a", target_url="https://a"))
        db.add(Redirect(name="b", target_url="https://b"))
        await db.commit()
    from app.handlers.callbacks import button_handler
    update, context = _cb_update("clear_confirm")
    await button_handler(update, context)
    assert await _count() == []


# --- addlist ---

async def test_addlist_missing_base():
    from app.handlers import addlist as addlist_mod
    with patch.object(addlist_mod, "ACESTREAM_BASE", ""):
        update, context = _cmd_update()
        from app.handlers.addlist import addlist_cmd
        await addlist_cmd(update, context)
    update.effective_message.reply_text.assert_awaited_with("❌ Error: `URL_BASE_ACESTREAM` no está definida.")


async def test_addlist_with_channel_url_button():
    from app.handlers import addlist as addlist_mod
    with patch.object(addlist_mod, "CHANNEL_LIST_URL", "https://example.com/list.json"):
        update, context = _cmd_update()
        from app.handlers.addlist import addlist_cmd
        await addlist_cmd(update, context)
        _, kwargs = update.effective_message.reply_text.await_args
        markup = kwargs["reply_markup"]
        callbacks = [b.callback_data for row in markup.inline_keyboard for b in row]
    assert "addlist_url" in callbacks


async def test_addlist_without_channel_url_no_button():
    from app.handlers import addlist as addlist_mod
    with patch.object(addlist_mod, "CHANNEL_LIST_URL", ""):
        update, context = _cmd_update()
        from app.handlers.addlist import addlist_cmd
        await addlist_cmd(update, context)
        _, kwargs = update.effective_message.reply_text.await_args
        markup = kwargs["reply_markup"]
        callbacks = [b.callback_data for row in markup.inline_keyboard for b in row]
    assert "addlist_url" not in callbacks


# --- handle_json_input ---

async def test_handle_json_input_no_mode():
    from app.handlers.addlist import handle_json_input
    update, context = _cmd_update()
    await handle_json_input(update, context)
    update.effective_message.reply_text.assert_not_awaited()


async def test_handle_json_input_simple():
    update, context = _cmd_update()
    context.user_data["awaiting"] = "simple"
    payload = json.dumps([{"name": "canal1", "ace_id": "abc"}])
    update.effective_message.text = payload
    from app.handlers.addlist import handle_json_input
    await handle_json_input(update, context)
    rows = await _count()
    assert rows[0].target_url == "http://acestream.local:6878/ace/getstream?id=abc"


async def test_handle_json_input_url():
    data = {"hashes": [{"title": "Canal", "hash": "xyz"}]}
    from app.handlers import addlist as addlist_mod
    with patch.object(addlist_mod, "_fetch_json", new=AsyncMock(return_value=data)):
        update, context = _cmd_update()
        context.user_data["awaiting"] = "url"
        update.effective_message.text = "https://example.com/list.json"
        from app.handlers.addlist import handle_json_input
        await handle_json_input(update, context)
    rows = await _count()
    assert rows[0].target_url == "http://acestream.local:6878/ace/getstream?id=xyz"


async def test_handle_json_input_warns_when_empty():
    from app.handlers import addlist as addlist_mod
    with patch.object(addlist_mod, "_fetch_json", new=AsyncMock(return_value={"hashes": []})):
        update, context = _cmd_update()
        context.user_data["awaiting"] = "url"
        update.effective_message.text = "https://example.com/list.json"
        from app.handlers.addlist import handle_json_input
        await handle_json_input(update, context)
    update.effective_message.reply_text.assert_awaited_once()
    args, _ = update.effective_message.reply_text.await_args
    assert "⚠️" in args[0]


async def test_handle_json_input_rejects_large_paste(monkeypatch):
    from app.handlers import addlist as addlist_mod
    monkeypatch.setattr(addlist_mod, "MAX_PASTE_JSON_SIZE", 16)
    update, context = _cmd_update()
    context.user_data["awaiting"] = "simple"
    payload = '{"name":"canal","ace_id":"12345678901234"}'
    update.effective_message.text = payload
    from app.handlers.addlist import handle_json_input
    await handle_json_input(update, context)
    assert not await _count()
    update.effective_message.reply_text.assert_awaited()
    args, _ = update.effective_message.reply_text.await_args
    assert "demasiado largo" in args[0]



async def test_fetch_json_rejects_non_json_content_type():
    from app import helpers

    class _FakeResp:
        def __init__(self, headers):
            self.headers = headers
            self.status_code = 200
            self.text = ""

        def raise_for_status(self):
            pass

        def json(self):
            return {"x": 1}

    class _FakeClient:
        def __init__(self, resp):
            self._resp = resp

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, **kwargs):
            return self._resp

    with patch.object(helpers.httpx, "AsyncClient", return_value=_FakeClient(_FakeResp({"content-type": "text/html"}))):
        with pytest.raises(ValueError):
            await helpers._fetch_json("https://example.com")


async def test_fetch_json_accepts_json_content_type():
    from app import helpers

    class _FakeResp:
        def __init__(self, headers):
            self.headers = headers
            self.status_code = 200
            self.text = ""

        def raise_for_status(self):
            pass

        def json(self):
            return [{"name": "a", "ace_id": "b"}]

    class _FakeClient:
        def __init__(self, resp):
            self._resp = resp

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, **kwargs):
            return self._resp

    with patch.object(helpers.httpx, "AsyncClient", return_value=_FakeClient(_FakeResp({"content-type": "application/json; charset=utf-8"}))):
        data = await helpers._fetch_json("https://example.com")
    assert data == [{"name": "a", "ace_id": "b"}]


async def test_fetch_json_uses_configurable_timeout(monkeypatch):
    from app import helpers
    monkeypatch.setattr(helpers, "FETCH_TIMEOUT_SECONDS", 15)

    class _Resp:
        def __init__(self):
            self.headers = {"content-type": "application/json"}
            self.status_code = 200
            self.text = "[]"

        def raise_for_status(self):
            pass

        def json(self):
            return []

    class _Client:
        def __init__(self):
            self.kwargs = None

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, **kwargs):
            self.kwargs = kwargs
            return _Resp()

    client = _Client()
    with patch.object(helpers.httpx, "AsyncClient", return_value=client):
        await helpers._fetch_json("https://example.com")
    assert client.kwargs["timeout"] == 15



# --- reredirect ---

async def test_reredirect_missing_name():
    from app.handlers import reredirect as reredirect_mod
    with patch.object(reredirect_mod, "REDIRECT_NAME", ""):
        update, context = _cmd_update()
        from app.handlers.reredirect import reredirect_cmd
        await reredirect_cmd(update, context)
    args, _ = update.effective_message.reply_text.await_args
    assert "REDIRECT_NAME" in args[0]


async def test_reredirect_populated_stores_links():
    async with SessionLocal() as db:
        db.add(Redirect(name="otro", target_url="https://real"))
        await db.commit()
    from app.handlers.reredirect import reredirect_cmd
    update, context = _cmd_update()
    await reredirect_cmd(update, context)
    assert context.user_data.get("reredirect_links")
    assert update.effective_message.reply_text.await_count >= 1


# --- button_handler ---

async def test_button_handler_list():
    async with SessionLocal() as db:
        db.add(Redirect(name="a", target_url="https://a"))
        await db.commit()
    from app.handlers.callbacks import button_handler
    update, context = _cb_update("list")
    await button_handler(update, context)
    assert update.callback_query.edit_message_text.await_count >= 1


async def test_button_handler_reredirect_upserts():
    async with SessionLocal() as db:
        db.add(Redirect(name="otro", target_url="https://real"))
        await db.commit()
    from app.handlers.callbacks import button_handler
    update, context = _cb_update("reredirect:otro")
    await button_handler(update, context)
    rows = await _count()
    f = [r for r in rows if r.name == "f"]
    assert len(f) == 1
    assert f[0].target_url == "@reredirect:otro"


async def test_button_handler_paste_url_sets_awaiting():
    from app.handlers.callbacks import button_handler
    update, context = _cb_update("addlist_paste_url")
    await button_handler(update, context)
    assert context.user_data["awaiting"] == "url"


async def test_button_handler_paste_json_sets_awaiting():
    from app.handlers.callbacks import button_handler
    update, context = _cb_update("addlist_paste_json")
    await button_handler(update, context)
    assert context.user_data["awaiting"] == "simple"


async def test_button_handler_delete_execute():
    async with SessionLocal() as db:
        db.add(Redirect(name="canal", target_url="https://a"))
        await db.commit()
    from app.handlers.callbacks import button_handler
    update, context = _cb_update("delete_execute:canal")
    await button_handler(update, context)
    assert await _count() == []
    assert update.callback_query.edit_message_text.await_count >= 1
