import os
import tempfile

# La base de datos y las variables de entorno se fijan antes de importar la app,
# porque app.config y app.database leen el entorno en el momento del import.
_TEST_DIR = tempfile.mkdtemp(prefix="httpredirect_test_")
_DB_PATH = os.path.join(_TEST_DIR, "test.db")

os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ["TELEGRAM_TOKEN"] = "test-token"
os.environ["ALLOWED_USER_ID"] = "12345"
os.environ["URL_BASE_ACESTREAM"] = "http://acestream.local:6878/ace/getstream?id="
os.environ["CHANNEL_LIST_URL"] = ""
os.environ["REDIRECT_NAME"] = "f"

from app.database import Base, engine, Redirect, SessionLocal  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db():
    """Limpia la tabla de redirecciones antes y después de cada test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
