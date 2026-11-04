"""Cálculo de carga ponderada W_i y agregados por gestor.

W_i = α · PesoDocente(TD_i)
    + β · FactorModalidad(M_i) · Sesiones_i
    + γ · ln(1 + Participantes_i)

El objetivo del proyecto es demostrar que "1 ticket = 1 unidad de trabajo" es
falso: tickets con el mismo conteo nominal producen cargas muy distintas.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.core.model_params import (
    FACTOR_MODALIDAD,
    PESO_DOCENTE,
    PESO_PRIORIDAD,
    PesosCarga,
)
from app.models.domain import Dataset, Ticket


@dataclass(slots=True)
class DesgloseCarga:
    """Componentes de W_i, para mostrarlos en el tooltip del dashboard."""

    ticket_id: str
    peso_docente: float
    peso_sesiones: float
    peso_participantes: float
    total: float


@dataclass(slots=True)
class CargaGestor:
    gestor: str
    tickets: int
    carga_total: float
    sesiones: int
    dias_con_sesion: int
    tickets_obligatorios: int
    tickets_ruta_b: int
    desglose: list[DesgloseCarga] = field(default_factory=list)


def _participantes(ds: Dataset, ticket_id: str) -> int:
    """Participantes solicitados sumados sobre los grupos del ticket."""
    total = 0
    for g in ds.grupos:
        if g.ticket_id == ticket_id and g.participantes_solicitados:
            total += g.participantes_solicitados
    return total


def calcular_peso(
    ticket: Ticket, participantes: int = 0, pesos: PesosCarga | None = None
) -> DesgloseCarga:
    pesos = pesos or PesosCarga()
    peso_doc = PESO_DOCENTE.get(ticket.tipo_docente.value, 1.0)
    factor_mod = FACTOR_MODALIDAD.get(ticket.modalidad.value, 1.0)

    comp_doc = pesos.alpha_docente * peso_doc
    comp_ses = pesos.beta_sesiones * factor_mod * max(0, ticket.total_sesiones)
    comp_par = pesos.gamma_participantes * math.log1p(max(0, participantes))

    return DesgloseCarga(
        ticket_id=ticket.ticket_id,
        peso_docente=round(comp_doc, 4),
        peso_sesiones=round(comp_ses, 4),
        peso_participantes=round(comp_par, 4),
        total=round(comp_doc + comp_ses + comp_par, 4),
    )


def calcular_cargas(
    ds: Dataset,
    tickets: list[Ticket] | None = None,
    pesos: PesosCarga | None = None,
    asignacion: dict[str, str] | None = None,
) -> tuple[dict[str, CargaGestor], dict[str, DesgloseCarga]]:
    """Carga por gestor.

    `asignacion` permite simular un escenario distinto del que trae el Excel
    (ticket_id -> gestor), sin tocar el dataset original.
    """
    pesos = pesos or PesosCarga()
    tickets = tickets if tickets is not None else ds.tickets_abiertos

    sesiones_por_ticket = ds.sesiones_por_ticket
    dias_por_ticket: dict[str, set] = {}
    for tid, ses in sesiones_por_ticket.items():
        dias_por_ticket[tid] = {s.fecha for s in ses}

    cargas: dict[str, CargaGestor] = {}
    desgloses: dict[str, DesgloseCarga] = {}

    for t in tickets:
        gestor = (asignacion or {}).get(t.ticket_id, t.gestor)
        if not gestor:
            continue

        d = calcular_peso(t, _participantes(ds, t.ticket_id), pesos)
        desgloses[t.ticket_id] = d

        cg = cargas.get(gestor)
        if cg is None:
            cg = CargaGestor(
                gestor=gestor,
                tickets=0,
                carga_total=0.0,
                sesiones=0,
                dias_con_sesion=0,
                tickets_obligatorios=0,
                tickets_ruta_b=0,
            )
            cargas[gestor] = cg

        cg.tickets += 1
        cg.carga_total = round(cg.carga_total + d.total, 4)
        cg.sesiones += t.total_sesiones
        cg.dias_con_sesion += len(dias_por_ticket.get(t.ticket_id, set()))
        cg.tickets_obligatorios += int(t.requiere_supervision_obligatoria)
        cg.tickets_ruta_b += int(t.es_ruta_b)
        cg.desglose.append(d)

    return cargas, desgloses


def metricas_equidad(cargas: dict[str, CargaGestor]) -> dict[str, float]:
    """Indicadores de desbalance que alimentan la función objetivo."""

    valores = [c.carga_total for c in cargas.values()]
    if not valores:
        return {
            "c_max": 0.0, "c_min": 0.0, "c_media": 0.0, "rango": 0.0,
            "ratio": 0.0, "desviacion_estandar": 0.0, "desbalance_pct": 0.0,
        }

    maximo, minimo = max(valores), min(valores)
    media = sum(valores) / len(valores)
    varianza = sum((v - media) ** 2 for v in valores) / len(valores)

    return {
        "c_max": round(maximo, 4),
        "c_min": round(minimo, 4),
        "c_media": round(media, 4),
        "rango": round(maximo - minimo, 4),
        "ratio": round(maximo / minimo, 3) if minimo > 0 else 0.0,
        "desviacion_estandar": round(math.sqrt(varianza), 4),
        "desbalance_pct": round((maximo - minimo) / media * 100, 2) if media else 0.0,
    }


def prioridad_numerica(ticket: Ticket) -> float:
    return PESO_PRIORIDAD.get(ticket.prioridad.value, 1.0)
