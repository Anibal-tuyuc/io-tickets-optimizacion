"""Punto de entrada de la API.

Uso:
    uvicorn app.main:app --reload --port 8000
Documentación interactiva: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import diagnostico, optimizacion, recursos, tickets
from app.core.config import APP_NAME, APP_VERSION, COURSE, INSTITUTION
from app.etl.loader import load_dataset

# Build del frontend, presente solo en la imagen Docker.
# En desarrollo se sirve con Vite en el puerto 5173 y esta carpeta no existe.
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Precarga el dataset para que la primera petición no pague el ETL.
    load_dataset()
    yield


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        f"{INSTITUTION} — {COURSE}\n\n"
        "Optimización de asignación de tickets y programación de acompañamiento docente."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(diagnostico.router)
app.include_router(tickets.router)
app.include_router(recursos.router)
app.include_router(optimizacion.router)


@app.get("/health", tags=["sistema"])
def health() -> dict:
    ds = load_dataset()
    return {
        "ok": True,
        "version": APP_VERSION,
        "tickets": len(ds.tickets),
        "sesiones": len(ds.sesiones),
        "gestores": len(ds.gestores),
    }


# ------------------------------------------------------- frontend estático
# Se monta al final para no tapar /docs, /health ni los routers de la API.
if FRONTEND_DIST.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="assets",
    )

    @app.get("/{ruta_completa:path}", include_in_schema=False)
    def spa(ruta_completa: str) -> FileResponse:
        """Sirve la SPA; cualquier ruta desconocida vuelve a index.html."""
        archivo = FRONTEND_DIST / ruta_completa
        if ruta_completa and archivo.is_file():
            return FileResponse(archivo)
        return FileResponse(FRONTEND_DIST / "index.html")
