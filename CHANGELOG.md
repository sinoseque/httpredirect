# Changelog

## [1.3.4] - 2026-06-23

### Added
- `/list` — comando para listar todas las rutas configuradas
- `/del` (sin argumentos) — lista interactiva paginada para seleccionar y borrar rutas

### Changed
- `/del <nombre>` ahora pide confirmación antes de borrar
- README actualizado con la nueva documentación de comandos

### Fixed
- Reemplazado `update.message` por `update.effective_message` para evitar errores `NoneType`
- Mensaje largo de listado dividido en fragmentos de 4000 caracteres
- Añadido handler HEAD para `/r/{name}` (compatibilidad VLC en Linux)
- Seguimiento de cadena HTTP redirect ahora se resuelve server-side para mejor compatibilidad con clientes

## [1.3.3] - 2026-06-22

### Added
- Validación de `TELEGRAM_TOKEN` y `ALLOWED_USER_ID` al arranque
- Mensaje "⛔ No autorizado" para usuarios no permitidos en el bot
- `DATABASE_URL` configurable mediante variable de entorno

### Changed
- Autorización extraída a decorator `@restricted`, eliminando 8 checks duplicados
- Lógica HTTP de fetching JSON unificada en `_fetch_json()`
- Patrón de sesión de BD unificado (eliminado `get_db()`)
- `requirements.txt`: versiones mínimas fijadas para todas las dependencias
- Dockerfile actualizado a Python 3.12
- Workflow CI: actions actualizadas (checkout@v4, setup-qemu@v3, etc.)

### Fixed
- Resolución `@reredirect` ahora soporta cadenas de más de 2 niveles con detección de ciclos
- Validación de `ACESTREAM_BASE` en funciones de importación

### Internal
- Añadida skill `publish-gh` para automatizar el flujo de publicación

## [1.3.0] - 2026-06-17

### Changed
- Refactor: `main.py` dividido en 3 módulos (`config.py`, `database.py`, `main.py`) para mejor mantenimiento
- Extraída función `_upsert_redirects()` para eliminar código duplicado en las importaciones

### Added
- `app/__init__.py` para que `app/` funcione como paquete Python

### Internal
- Sin cambios de comportamiento ni nuevas funcionalidades

## [1.2.0] - 2026-06-17

### Added
- `/clear` — comando para borrar todos los redireccionamientos con confirmación inline
- `/addlist` — importar lista de canales desde JSON (URL configurada, URL personalizada o pegado manual)
- `/reredirect` — apuntar una ruta fija (`REDIRECT_NAME`) a otro canal existente, con resolución en cadena
- `@reredirect:` — lógica en el endpoint `/r/{name}` para resolver cadenas de redirecciones
- Variables de entorno: `CHANNEL_LIST_URL`, `REDIRECT_NAME`
- Modo debug vía `LOG_LEVEL=DEBUG`
- Logging detallado en todos los handlers (HTTP status, respuesta, traceback)

### Fixed
- Normalización de nombres: caracteres especiales (`*`, `&`, `@`, `#`) se reemplazan por letras en lugar de eliminarse
- Nombres duplicados en importación: se añade sufijo numérico (`-1`, `-2`, ...)
- Seguimiento de redirectos HTTP (`follow_redirects=True`) para gateways IPFS
- User-Agent en peticiones HTTP para compatibilidad con gateways
- Anidamiento correcto de `InlineKeyboardMarkup` en `/reredirect`

### Changed
- Workflow Docker: push a `main` publica como `:edge`; releases publican como `:vX.Y.Z` + `:latest`
- `normalize_name` ahora reemplaza caracteres en lugar de eliminarlos
- `import_from_json_hashes` y `import_from_json_simple` usan lógica de dedup previa al insert
