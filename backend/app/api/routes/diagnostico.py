from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import DashboardOut, DiagnosticoOut
from app.etl.loader import escribir_diagnostico
from app.services.orquestador import Orquestador
from app.services.state import gestor_estado

router = APIRouter(tags=["diagnóstico"])


@router.get("/diagnostico", response_model=DiagnosticoOut)
def diagnostico() -> dict:
    """Auditoría de calidad de la base de datos de origen."""
    ds = gestor_estado.get().ds
    escribir_diagnostico(ds)
    d = ds.diagnostico
    return {
        "archivo": d.archivo,
        "hojas_leidas": d.hojas_leidas,
        "tickets_totales": d.tickets_totales,
        "tickets_abiertos": d.tickets_abiertos,
        "sesiones_totales": d.sesiones_totales,
        "sesiones_fechadas": d.sesiones_fechadas,
        "grupos": d.grupos,
        "docentes": d.docentes,
        "resumen": d.resumen,
        "incidencias": [
            {
                "tipo": i.tipo,
                "gravedad": i.gravedad,
                "descripcion": i.descripcion,
                "referencia": i.referencia,
                "accion_tomada": i.accion_tomada,
            }
            for i in d.incidencias
        ],
    }


@router.get("/dashboard", response_model=DashboardOut)
def dashboard() -> dict:
    return Orquestador(gestor_estado.get()).dashboard()


@router.post("/demo/reset")
def reset_demo() -> dict:
    """Reinicia el estado al del archivo original antes de grabar el video."""
    gestor_estado.reset()
    return {"ok": True, "mensaje": "Estado restaurado desde el Excel original."}
