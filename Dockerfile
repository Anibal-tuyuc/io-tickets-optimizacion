# ---------- Etapa 1: compilar el frontend ----------
FROM node:20-alpine AS frontend

WORKDIR /build

# Solo manifiestos primero: si el código no cambia, esta capa se reutiliza.
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund 2>/dev/null || npm install --no-audit --no-fund

COPY frontend/ ./
RUN VITE_API_BASE="" npm run build


# ---------- Etapa 2: runtime de Python ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias del backend (la única que necesita compilador es ortools,
# que publica wheel para manylinux: no hace falta build-essential).
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Código y datos
COPY backend/ ./backend/
COPY data/source/ ./data/source/

# Frontend compilado
COPY --from=frontend /build/dist ./frontend/dist

# Directorios de trabajo escribibles
RUN mkdir -p /app/data/cache /app/data/results

# Usuario sin privilegios
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

ENV IO_SOURCE_XLSX=/app/data/source/Control_Prueba_IO.xlsx

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=4).status==200 else 1)"

WORKDIR /app/backend

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
