"""Carga del dataset completo y caché en disco."""

from __future__ import annotations

import json
import pickle
from dataclasses import asdict
from pathlib import Path

from app.core.config import CACHE_DIR, SOURCE_XLSX
from app.etl.excel_reader import ExcelReader
from app.models.domain import Dataset

_CACHE_VERSION = 2
_CACHE_FILE = CACHE_DIR / f"dataset_v{_CACHE_VERSION}.pkl"
_DIAG_FILE = CACHE_DIR / "diagnostico_datos.json"


def build_dataset(ruta: Path | str | None = None) -> Dataset:
    reader = ExcelReader(ruta)
    tickets, sesiones, grupos, docentes, gestores = reader.leer()
    return Dataset(
        tickets=tickets,
        sesiones=sesiones,
        grupos=grupos,
        docentes=docentes,
        gestores=gestores,
        diagnostico=reader.diagnostico,
        fuente=str(reader.ruta),
    )


def load_dataset(force: bool = False, ruta: Path | str | None = None) -> Dataset:
    """Devuelve el dataset, usando caché en disco si el Excel no cambió."""
    origen = Path(ruta) if ruta else SOURCE_XLSX
    if (
        not force
        and ruta is None
        and _CACHE_FILE.exists()
        and origen.exists()
        and _CACHE_FILE.stat().st_mtime >= origen.stat().st_mtime
    ):
        with _CACHE_FILE.open("rb") as fh:
            return pickle.load(fh)

    ds = build_dataset(ruta)
    if ruta is None:
        with _CACHE_FILE.open("wb") as fh:
            pickle.dump(ds, fh)
        escribir_diagnostico(ds)
    return ds


def escribir_diagnostico(ds: Dataset) -> Path:
    """Serializa el diagnóstico de calidad para mostrarlo en la UI."""
    payload = {
        "archivo": ds.diagnostico.archivo,
        "hojas_leidas": ds.diagnostico.hojas_leidas,
        "tickets_totales": ds.diagnostico.tickets_totales,
        "tickets_abiertos": ds.diagnostico.tickets_abiertos,
        "sesiones_totales": ds.diagnostico.sesiones_totales,
        "sesiones_fechadas": ds.diagnostico.sesiones_fechadas,
        "grupos": ds.diagnostico.grupos,
        "docentes": ds.diagnostico.docentes,
        "resumen": ds.diagnostico.resumen,
        "incidencias": [
            {
                "tipo": i.tipo,
                "gravedad": i.gravedad,
                "descripcion": i.descripcion,
                "referencia": i.referencia,
                "accion_tomada": i.accion_tomada,
            }
            for i in ds.diagnostico.incidencias
        ],
    }
    _DIAG_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return _DIAG_FILE
