"""Configuración central del proyecto.

Todas las constantes del modelo viven aquí y en `model_params.py`, de forma que
el informe del proyecto y el código digan exactamente lo mismo.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------- rutas
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # .../io-tickets-optimizacion
BACKEND_DIR = PROJECT_ROOT / "backend"
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
RESULTS_DIR = DATA_DIR / "results"

# Orden de resolución del archivo base:
#   1. variable de entorno IO_SOURCE_XLSX
#   2. copia incluida en el repo (data/source/) — la que usa Docker
#   3. ruta original de la máquina de desarrollo
_ENTORNO = os.getenv("IO_SOURCE_XLSX", "").strip()

_CANDIDATOS_XLSX = [
    Path(_ENTORNO) if _ENTORNO else None,
    PROJECT_ROOT / "data" / "source" / "Control_Prueba_IO.xlsx",
    Path(r"C:\Users\Admin\Investigacion-Docentes-Optimización\Control_Prueba_IO (1).xlsx"),
]

# Path("") es Path(".") y siempre "existe": los nulos se filtran explícitamente.
SOURCE_XLSX = next(
    (p for p in _CANDIDATOS_XLSX if p is not None and p.is_file()),
    PROJECT_ROOT / "data" / "source" / "Control_Prueba_IO.xlsx",
)

DB_PATH = Path(os.getenv("IO_DB_PATH", PROJECT_ROOT / "data" / "app.db"))

for _d in (CACHE_DIR, RESULTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------- metadatos del curso
APP_NAME = "Optimizador de Tickets y Acompañamiento Docente"
APP_VERSION = "0.1.0"
INSTITUTION = "Universidad Mariano Gálvez de Guatemala"
COURSE = "Investigación de Operaciones — Sexto Semestre"

# Corte de simulación: fecha desde la cual se calculan plazos y antigüedad.
# Los datos de prueba llegan hasta el 2026-10-08, por lo que ese es el "hoy".
SIMULATION_DATE = "2026-10-08"
