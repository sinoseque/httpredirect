import os
import tempfile

# La base de datos y las variables de entorno se fijan antes de importar la app,
# porque app.config y app.database leen el entorno en el momento del import.
_TEST_DIR = tempfile.mkdtemp(prefix="httpredirect_test_")
_DB_PATH = os.path.join(_TEST_DIR, "test.db")

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_PATH}"
os.environ["TELEGRAM_TOKEN"] = "test-token"
os.environ["ALLOWED_USER_ID"] = "12345"
os.environ["URL_BASE_ACESTREAM"] = "http://acestream.local:6878/ace/getstream?id="
os.environ["CHANNEL_LIST_URL"] = ""
os.environ["REDIRECT_NAME"] = "f"

from app.database import Base, engine, Redirect  # noqa: E402
from sqlalchemy import delete  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
async def _fresh_db():
    """Crea el esquema (idempotente) y limpia la tabla antes de cada test."""
    async with engine.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(delete(Redirect))
        await conn.commit()
    yield
