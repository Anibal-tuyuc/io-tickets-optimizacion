from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.schemas import OptimizarIn, ResultadoOptimizacion
from app.engine.calendar_solver import CalendarioSolver
from app.services.orquestador import Orquestador
from app.services.state import gestor_estado

router = APIRouter(prefix="/optimizar", tags=["optimización"])


@router.post("", response_model=ResultadoOptimizacion)
def optimizar(datos: OptimizarIn) -> dict:
    """Ejecuta asignación + calendario y devuelve el antes/después completo."""
    try:
        return Orquestador(gestor_estado.get()).optimizar(
            theta_muestreo=datos.theta_muestreo,
            semilla=datos.semilla,
            max_movimientos=datos.max_movimientos,
            reasignar=datos.reasignar_tickets,
            generar_calendario=datos.generar_calendario,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/capacidad")
def capacidad() -> list[dict]:
    """Días con más sesiones que gestores: advertencia previa a optimizar."""
    estado = gestor_estado.get()
    return CalendarioSolver.diagnostico_capacidad(estado.ds, estado.gestores)
