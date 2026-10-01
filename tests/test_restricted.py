import asyncio
from unittest.mock import AsyncMock, MagicMock

import app.main as main


def _update(user_id):
    update = MagicMock()
    update.effective_user.id = user_id
    update.callback_query = None
    update.effective_message = MagicMock()
    update.effective_message.reply_text = AsyncMock()
    return update


def test_restricted_allows_authorized_user():
    called = []

    @main.restricted
    async def handler(update, context):
        called.append(True)

    update = _update(main.ALLOWED_ID)
    asyncio.run(handler(update, None))
    assert called == [True]
    update.effective_message.reply_text.assert_not_awaited()


def test_restricted_blocks_unauthorized_user():
    called = []

    @main.restricted
    async def handler(update, context):
        called.append(True)

    update = _update(999999)
    result = asyncio.run(handler(update, None))
    assert result is None
    assert called == []
    update.effective_message.reply_text.assert_awaited_with("⛔ No autorizado.")


def test_restricted_unauthorized_with_callback_query():
    update = _update(999999)
    update.callback_query = MagicMock()
    update.callback_query.answer = AsyncMock()

    @main.restricted
    async def handler(update, context):
        pass

    asyncio.run(handler(update, None))
    update.callback_query.answer.assert_awaited()
    update.effective_message.reply_text.assert_not_awaited()


def test_restricted_blocks_anonymous_user():
    called = []

    @main.restricted
    async def handler(update, context):
        called.append(True)

    update = MagicMock()
    update.effective_user = None
    update.callback_query = None
    update.effective_message = MagicMock()
    update.effective_message.reply_text = AsyncMock()
    result = asyncio.run(handler(update, None))
    assert result is None
    assert called == []
    update.effective_message.reply_text.assert_awaited_with("⛔ No autorizado.")
