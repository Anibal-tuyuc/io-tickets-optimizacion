from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.api.schemas import (
    CambioDocenteIn,
    SugerenciaGestor,
    TicketNuevoIn,
    TicketOut,
)
from app.services.orquestador import Orquestador
from app.services.state import gestor_estado

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _orch() -> Orquestador:
    return Orquestador(gestor_estado.get())


@router.get("", response_model=list[TicketOut])
def listar_tickets(estado: str | None = Query(default=None)) -> list[dict]:
    return _orch().tickets(estado)


@router.post("/nuevo", response_model=SugerenciaGestor)
def sugerir_asignacion(datos: TicketNuevoIn) -> dict:
    """Solo sugiere a qué gestor asignar un ticket hipotético (Mesa de Entrada).

    No crea nada: permite previsualizar el impacto en la carga antes de decidir.
    """
    try:
        return _orch().sugerir_gestor(datos.model_dump())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("", response_model=dict, status_code=201)
def crear_y_asignar(datos: TicketNuevoIn, gestor: str | None = None) -> dict:
    """Crea el ticket y, opcionalmente, lo asigna en el mismo paso."""
    try:
        ticket = gestor_estado.crear_ticket(datos.model_dump())
        if gestor:
            gestor_estado.asignar_ticket(ticket.ticket_id, gestor)
        return {
            "ticket_id": ticket.ticket_id,
            "gestor": gestor or "",
            "evento": ticket.evento,
            "total_sesiones": ticket.total_sesiones,
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{ticket_id}/asignar")
def asignar(ticket_id: str, gestor: str) -> dict:
    try:
        gestor_estado.asignar_ticket(ticket_id, gestor)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "ticket_id": ticket_id, "gestor": gestor}


@router.post("/{ticket_id}/cambio-docente")
def cambio_docente(ticket_id: str, datos: CambioDocenteIn) -> dict:
    """Simulador de la Regla 2: impacto de cambiar el tipo de docente."""
    try:
        orq = _orch()
        if datos.aplicar:
            gestor_estado.cambiar_tipo_docente(ticket_id, datos.nuevo_tipo)
        return orq.simular_cambio_docente(ticket_id, datos.nuevo_tipo)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
