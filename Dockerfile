FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# Valores por defecto para las variables
ENV LOG_LEVEL=WARNING
ENV PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
RUN mkdir -p /app/data && touch /app/app/__init__.py

EXPOSE 8000

# Usamos la variable PORT en el comando de arranque
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}