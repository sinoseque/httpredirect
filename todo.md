# TODO — Análisis de código (httpredirect)

---

## 🔴 Seguridad

- [ ] **SSRF en `dynamic_redirect`** (`app/main.py:582-584`) — El endpoint `/r/{name}` hace `client.get(target)` contra cualquier URL guardada en la BD. Permitiría escanear la red interna si alguien inserta URLs como `http://localhost:8080/admin` o `http://169.254.169.254/latest/meta-data/`.
- [ ] **Open redirect / URLs maliciosas** (`app/main.py:183`) — `/set nombre javascript:alert(1)` se guarda sin validar. Si bien la redirección es server-side, podría redirigir a sitios de phishing.

---

## 🔶 Bugs

- [ ] **`normalize_name` puede devolver string vacío** (`app/main.py:34-39`) — Si un título solo contiene caracteres especiales (`"!!!$$$"`), el nombre resultante es `""`, creando una ruta inválida.
- [ ] **`import_from_json_simple` no normaliza nombres** (`app/main.py:147-158`) — Usa el nombre tal cual, mientras que `import_from_json_hashes` llama a `normalize_name()`. Inconsistencia que genera duplicados con/sin guiones.
- [ ] **Race condition con SQLite** — `SessionLocal()` se crea por request/handler y `check_same_thread=False` permite accesos concurrentes. Bajo carga puede lanzar `database is locked`.

---

## 🟡 Mejoras

- [ ] **HTTP GET redundante** (`app/main.py:580-586`) — Cada `/r/{name}` resuelve la URL final con `client.get(target, follow_redirects=True)`. Añade latencia innecesaria. Bastaría con devolver el `target` directamente como `RedirectResponse`.
- [ ] **Falta endpoint de healthcheck** — Docker/Portainer no tienen una ruta `/health` para monitorear el servicio.
- [ ] **Código monolítico** — Todo en `app/main.py` (~593 líneas). Separar en módulos (`handlers.py`, `services.py`) facilitaría el mantenimiento.
- [ ] **Faltan type hints** — Funciones sin anotaciones de tipos, dificulta autocompletado y detección de errores.
- [ ] **Sin validación de content-type en `_fetch_json`** — Si `CHANNEL_LIST_URL` devuelve HTML/XML, `resp.json()` explota. Validar `content-type` antes de parsear.
