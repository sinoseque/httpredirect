# 🚀 HTTP Redirect Bot

Este proyecto es un microservicio ligero diseñado para gestionar redirecciones HTTP dinámicas mediante comandos de Telegram. Es ideal para centralizar enlaces largos o complejos en URLs cortas y fáciles de usar en cualquier dispositivo (Smart TV, reproductores multimedia, navegadores, etc.).

Especialmente útil en dispositivos de recursos limitados como cajas Android (S905X3), Raspberry Pi o servidores NAS.

## 🛠 Características

*   **Gestión Centralizada**: Añade, lista o borra rutas de redirección desde un chat privado de Telegram.
*   **Comandos Inteligentes**: El bot registra automáticamente sus comandos en la interfaz de Telegram para facilitar su uso.
*   **Soporte AceStream**: Generación automática de URLs de streaming a partir de un ID, utilizando una base de servidor configurable.
*   **Aislamiento y Ligereza**: Basado en FastAPI, SQLite y Docker.
*   **Multi-arquitectura**: Soporta sistemas `amd64` (PC) y `arm64` (S905X, Raspberry Pi).

---

## 🏗 Despliegue con Docker Compose

Pega el siguiente código en tu archivo `docker-compose.yml` o en el apartado **Stacks** de Portainer:

```yaml
version: '3.8'

services:
  httpredirect:
    image: tu-usuario/httpredirect:latest
    container_name: httpredirect
    restart: always
    ports:
      - "8000:8000"
    environment:
      - TELEGRAM_TOKEN=tu_token_aqui
      - ALLOWED_USER_ID=tu_id_numerico_aqui
      - URL_BASE_ACESTREAM=http://tu-motor-ace:6878/ace/getstream?id=
      - LOG_LEVEL=INFO
      - PORT=8000
    volumes:
      - /path/to/data:/app/data
```

### Variables de Entorno

| Variable | Descripción |
| :--- | :--- |
| `TELEGRAM_TOKEN` | Token obtenido a través de [@BotFather](https://t.me/botfather). |
| `ALLOWED_USER_ID` | Tu ID de usuario de Telegram para restringir el acceso. |
| `URL_BASE_ACESTREAM` | URL base de tu motor AceStream (debe terminar en `id=`). |
| `PORT` | Puerto interno en el que escucha la aplicación (default 8000). |

---

## 🤖 Uso del Bot

Al iniciar el bot en Telegram, dispondrás de los siguientes comandos:

*   `/start`: Muestra el panel de control y ayuda.
*   `/set <nombre> <url>`: Crea una redirección estándar hacia cualquier URL.
    *   *Ejemplo:* `/set miweb [https://miwebpersonal.com](https://miwebpersonal.com)`
*   `/setace <nombre> <id>`: Crea una redirección concatenando el ID al servidor AceStream configurado.
    *   *Ejemplo:* `/setace canal1 1a2b3c4d5e6f7g8h9i0j`
*   `/del <nombre>`: Elimina una ruta de la base de datos.

---

## 🔗 Acceso a las Redirecciones

Una vez configurada una ruta en el bot, podrás acceder a ella mediante la siguiente estructura de URL:

`http://<IP_DE_TU_SERVIDOR>:8000/r/<nombre>`

### Ejemplo de flujo:
1.  **En Telegram**: Envías `/setace prueba 0abc123...`
2.  **En tu reproductor**: Introduces la URL `[http://192.168.1.100:8000/r/prueba](http://192.168.1.100:8000/r/prueba)`
3.  **Resultado**: El servicio responde con una redirección HTTP 302 hacia la URL completa de AceStream.

---

## 🛠 Desarrollo

Si deseas realizar modificaciones y compilar tu propia imagen:

```bash
# Clonar y compilar
docker build -t httpredirect .

# Compilación multi-arquitectura (recomendado para cajas ARM)
docker buildx build --platform linux/amd64,linux/arm64 -t tu-usuario/httpredirect:latest --push .
```

---

## 📝 Notas
*   La base de datos SQLite se almacena en `/app/data`, asegúrate de persistir este volumen para no perder tus rutas al reiniciar el contenedor.
*   El acceso a las rutas de redirección (`/r/`) es público para permitir la compatibilidad con reproductores de vídeo externos.</IP_DE_TU_SERVIDOR>