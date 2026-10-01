import httpx
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, PlainTextResponse

from telegram import BotCommand
from telegram.ext import ApplicationBuilder

from .config import ACESTREAM_BASE, ALLOWED_ID, logger, TOKEN
from .database import SessionLocal, RedirectRepository, engine, Base
from .decorators import UsageError, _require_args, restricted
from .handlers import ALL_HANDLERS
from .helpers import (
    _build_paged_page,
    _build_redirect_list_parts,
    _resolve_duplicates,
    import_from_json_hashes,
    import_from_json_simple,
    normalize_name,
)

__all__ = [
    "ALL_HANDLERS",
    "SessionLocal",
    "RedirectRepository",
    "engine",
    "Base",
    "UsageError",
    "_require_args",
    "_build_redirect_list_parts",
    "_resolve_duplicates",
    "dynamic_redirect",
    "dynamic_redirect_head",
    "health",
    "import_from_json_hashes",
    "import_from_json_simple",
    "normalize_name",
    "restricted",
    "app",
]


# --- CICLO DE VIDA ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = []
    if not TOKEN:
        missing.append("TELEGRAM_TOKEN")
    if ALLOWED_ID == 0:
        missing.append("ALLOWED_USER_ID")
    if missing:
        raise RuntimeError(f"Variables de entorno no configuradas: {', '.join(missing)}")

    application = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    for handler in ALL_HANDLERS:
        application.add_handler(handler)

    # Registro automático de comandos
    await application.initialize()
    await application.bot.set_my_commands([
        BotCommand("start", "Menú principal"),
        BotCommand("set", "Redirección normal: /set nombre url"),
        BotCommand("setace", "AceStream: /setace nombre id"),
        BotCommand("del", "Borrar ruta: /del nombre o lista interactiva"),
        BotCommand("clear", "Borrar todas las rutas"),
        BotCommand("addlist", "Importar lista de canales"),
        BotCommand("reredirect", "Apuntar ruta fija a otro canal"),
        BotCommand("list", "Listar todas las rutas")
    ])

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await application.start()
    await application.updater.start_polling()
    logger.info("Bot y comandos registrados correctamente.")

    yield

    await application.updater.stop()
    await application.stop()
    await application.shutdown()


# --- FASTAPI ---

app = FastAPI(title="httpredirect", lifespan=lifespan)


@app.get("/r/{name}")
async def dynamic_redirect(name: str):
    async with SessionLocal() as db:
        repo = RedirectRepository(db)
        link = await repo.find_by_name(name)
        if not link:
            raise HTTPException(status_code=404)

        target = link.target_url
        visited = {name}
        while target.startswith("@reredirect:"):
            inner_name = target[len("@reredirect:"):]
            if inner_name in visited:
                return PlainTextResponse(
                    "⚠️ Ciclo detectado en la cadena de redirecciones.",
                    status_code=404
                )
            visited.add(inner_name)
            inner = await repo.find_by_name(inner_name)
            if not inner:
                return PlainTextResponse(
                    f"⚠️ La ruta '{name}' apunta a '{inner_name}', pero esa ruta ya no existe.",
                    status_code=404
                )
            target = inner.target_url

        if target.startswith("http"):
            try:
                async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                    resp = await client.get(target)
                    target = str(resp.url)
            except httpx.HTTPError:
                logger.debug("Error al resolver cadena de redirects para %s", target)

        return RedirectResponse(url=target, status_code=302)


@app.head("/r/{name}")
async def dynamic_redirect_head(name: str):
    return await dynamic_redirect(name)


@app.get("/health")
async def health():
    """Punto de parida para balanceadores de carga y checks de estado."""
    try:
        async with SessionLocal() as db:
            routes = await RedirectRepository(db).count()
        return {"status": "ok", "routes": routes}
    except Exception:
        logger.exception("Fallo en /health")
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
