# Changelog

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
