"""Semáforo de plazos administrativos (Regla 2, cambio dinámico de docente)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.core.calendario import dias_habiles_entre
from app.core.model_params import REQ_DIAS_HABILES
from app.models.domain import Severidad, Ticket, TipoDocente


@dataclass(slots=True)
class EvaluacionPlazo:
    ticket_id: str
    tipo_docente: str
    requiere_dias: int
    disponibles: int | None
    holgura: int | None
    severidad: Severidad
    mensaje: str

    def to_dict(self) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "tipo_docente": self.tipo_docente,
            "requiere_dias": self.requiere_dias,
            "disponibles": self.disponibles,
            "holgura": self.holgura,
            "severidad": self.severidad.value,
            "mensaje": self.mensaje,
        }


def evaluar(
    ticket: Ticket,
    hoy: date,
    tipo_docente: TipoDocente | str | None = None,
    req_dias: int | None = None,
) -> EvaluacionPlazo:
    """Evalúa si los días hábiles restantes alcanzan para el tipo de docente.

    `tipo_docente` permite simular un cambio (Interno -> Externo) sin tocar el
    ticket: es lo que alimenta el simulador de la Prueba 3.
    """
    tipo = tipo_docente or ticket.tipo_docente
    tipo_valor = tipo.value if isinstance(tipo, TipoDocente) else str(tipo)
    requerido = req_dias if req_dias is not None else REQ_DIAS_HABILES.get(tipo_valor, 8)

    if ticket.fecha_inicio is None:
        return EvaluacionPlazo(
            ticket_id=ticket.ticket_id,
            tipo_docente=tipo_valor,
            requiere_dias=requerido,
            disponibles=None,
            holgura=None,
            severidad=Severidad.SIN_FECHA,
            mensaje="El ticket no tiene fecha de inicio; complete la fecha para evaluar el plazo.",
        )

    disponibles = dias_habiles_entre(hoy, ticket.fecha_inicio)
    holgura = disponibles - requerido

    if holgura < 0:
        severidad = Severidad.ROJO
        mensaje = (
            f"Retraso inminente: el plazo de {requerido} días hábiles para "
            f"{tipo_valor} excede en {abs(holgura)} días al margen disponible."
        )
    elif holgura <= max(2, int(requerido * 0.25)):
        severidad = Severidad.AMBAR
        mensaje = (
            f"Margen ajustado: {holgura} días hábiles de holgura sobre los "
            f"{requerido} requeridos para {tipo_valor}."
        )
    else:
        severidad = Severidad.VERDE
        mensaje = (
            f"Plazo holgado: {disponibles} días hábiles disponibles para "
            f"{requerido} requeridos ({holgura} de holgura)."
        )

    return EvaluacionPlazo(
        ticket_id=ticket.ticket_id,
        tipo_docente=tipo_valor,
        requiere_dias=requerido,
        disponibles=disponibles,
        holgura=holgura,
        severidad=severidad,
        mensaje=mensaje,
    )


def simular_cambio_docente(
    ticket: Ticket, nuevo_tipo: TipoDocente, hoy: date
) -> dict:
    """Compara el plazo actual contra el escenario de cambio de docente."""
    antes = evaluar(ticket, hoy, ticket.tipo_docente)
    despues = evaluar(ticket, hoy, nuevo_tipo)

    return {
        "ticket_id": ticket.ticket_id,
        "antes": antes.to_dict(),
        "despues": despues.to_dict(),
        "deterioro": (
            despues.severidad is Severidad.ROJO and antes.severidad is not Severidad.ROJO
        ),
        "mejora": (
            despues.severidad is Severidad.VERDE and antes.severidad is not Severidad.VERDE
        ),
        "delta_dias_requeridos": despues.requiere_dias - antes.requiere_dias,
        "delta_holgura": (
            (despues.holgura or 0) - (antes.holgura or 0)
            if despues.holgura is not None and antes.holgura is not None
            else None
        ),
    }
