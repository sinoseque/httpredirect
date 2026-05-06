# httpredirect 🛰️

Servicio ligero para crear redirecciones HTTP dinámicas gestionables por API y Telegram.

## ⚙️ Configuración

### Variables de Entorno
- `TELEGRAM_TOKEN`: Token de BotFather.
- `ALLOWED_USER_ID`: Tu ID numérico de Telegram.
- `LOG_LEVEL`:	Nivel de detalle de los logs.	DEBUG, INFO, WARNING, ERROR	WARNING

### Volúmenes
- `/app/data`: Directorio para la base de datos persistente.

## 🚀 Despliegue
```bash
docker run -d \
  --name httpredirect \
  -p 8000:8000 \
  -e TELEGRAM_TOKEN="tu_token" \
  -e ALLOWED_USER_ID="tu_id" \
  -v $(pwd)/data:/app/data \
  tu-usuario/httpredirect:latest