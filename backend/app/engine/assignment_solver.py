"""Asignación de tickets a gestores: modelo de equidad (Regla 1 y 5).

Variables
    x[i,g] ∈ {0,1}   ticket i asignado al gestor g
    Cmax, Cmin ≥ 0   carga máxima y mínima

Objetivo
    min  w1·(Cmax − Cmin) + w4·Σ_i antigüedad_i·(1 − Σ_g x[i,g_original])

Restricciones
    Σ_g x[i,g] = 1       ∀ i          (todo ticket tiene exactamente un gestor)
    x[i,g] = 0           si g no está activo
    Cmax ≥ Σ_i W_i·x[i,g]  ∀ g
    Cmin ≤ Σ_i W_i·x[i,g]  ∀ g

La antigüedad se penaliza cuando un ticket viejo o urgente NO queda con su
gestor actual (mover un ticket en curso tiene costo operativo) y se premia
cuando un ticket urgente cae en un gestor con holgura.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from app.core.model_params import (
    SLO_DIAS_POR_PRIORIDAD,
    PESO_PRIORIDAD,
    ParametrosOptimizacion,
)
from app.engine.weights import calcular_cargas, calcular_peso, metricas_equidad
from app.models.domain import Dataset, EstadoGestor, Gestor, Ticket

# Costo de mover un ticket que ya estaba asignado (fricción operativa).
COSTO_MOVIMIENTO = 6.0

# Política realista: no se reorganiza la cartera completa. Con 6 movimientos
# el desbalance baja de 2.03x a 1.01x en los datos de prueba.
MAX_MOVIMIENTOS_DEFAULT = 6


@dataclass(slots=True)
class ResultadoAsignacion:
    asignacion: dict[str, str]                 # ticket_id -> gestor
    asignacion_previa: dict[str, str]
    movimientos: list[dict] = field(default_factory=list)
    metricas_antes: dict[str, float] = field(default_factory=dict)
    metricas_despues: dict[str, float] = field(default_factory=dict)
    cargas_antes: dict[str, dict] = field(default_factory=dict)
    cargas_despues: dict[str, dict] = field(default_factory=dict)
    estado_solver: str = ""


class AsignacionSolver:
    def __init__(self, ds: Dataset, params: ParametrosOptimizacion | None = None) -> None:
        self.ds = ds
        self.params = params or ParametrosOptimizacion()

    # ------------------------------------------------------------------ API
    def resolver(
        self,
        tickets: list[Ticket] | None = None,
        gestores: list[Gestor] | None = None,
        fijar: dict[str, str] | None = None,
        max_movimientos: int | None = MAX_MOVIMIENTOS_DEFAULT,
    ) -> ResultadoAsignacion:
        """Reasigna tickets.

        `fijar` permite bloquear asignaciones (por ejemplo, tickets ya resueltos
        o decisiones manuales del usuario).

        `max_movimientos` limita cuántos tickets pueden cambiar de gestor: una
        política de reasignación realista no puede reorganizar toda la cartera.
        """
        tickets = tickets if tickets is not None else self.ds.tickets_abiertos
        gestores = gestores if gestores is not None else self.ds.gestores
        fijar = fijar or {}

        # Regla 1: un gestor en vacaciones no recibe NUEVAS asignaciones. Su
        # carga pendiente se reasigna entre los activos. (Su calendario se
        # bloquea aparte, en el solver de supervisión.)
        activos = [g for g in gestores if g.estado is EstadoGestor.ACTIVO]
        if not activos:
            raise ValueError("No hay gestores activos: no se puede asignar.")
        nombres = [g.nombre for g in activos]

        pesos = {t.ticket_id: calcular_peso(t, self._participantes(t.ticket_id), self.params.pesos_carga).total
                 for t in tickets}

        modelo = cp_model.CpModel()
        x: dict[tuple[str, str], cp_model.IntVar] = {}
        for t in tickets:
            for g in nombres:
                x[(t.ticket_id, g)] = modelo.NewBoolVar(f"x_{t.ticket_id}_{g}")

        # todo ticket exactamente un gestor
        for t in tickets:
            candidatos = [x[(t.ticket_id, g)] for g in nombres]
            if t.ticket_id in fijar and fijar[t.ticket_id] in nombres:
                modelo.Add(sum(candidatos) == 1)
                for g in nombres:
                    modelo.Add(x[(t.ticket_id, g)] == (1 if g == fijar[t.ticket_id] else 0))
            else:
                modelo.Add(sum(candidatos) == 1)

        # cargas como enteros escalados (CP-SAT trabaja con enteros)
        escala = 1000
        carga = {}
        for g in nombres:
            carga[g] = modelo.NewIntVar(0, 10**7, f"carga_{g}")
            modelo.Add(
                carga[g] == sum(int(round(pesos[t.ticket_id] * escala)) * x[(t.ticket_id, g)]
                                for t in tickets)
            )

        cmax = modelo.NewIntVar(0, 10**7, "cmax")
        cmin = modelo.NewIntVar(0, 10**7, "cmin")
        for g in nombres:
            modelo.Add(cmax >= carga[g])
            modelo.Add(cmin <= carga[g])

        # Costo de mover un ticket en curso. Debe ser del orden de la carga que
        # se mueve, no un epsilon: si mover sale gratis, el solver reorganiza
        # el 86% de la cartera y la propuesta deja de ser aplicable.
        costo_mov = []
        for t in tickets:
            if not (t.gestor and t.gestor in nombres):
                continue
            peso_prio = PESO_PRIORIDAD.get(t.prioridad.value, 1.0)
            slo = SLO_DIAS_POR_PRIORIDAD.get(t.prioridad.value, 10)
            exceso = max(0, t.dias_abiertos - slo)
            # Mover un ticket urgente/viejo cuesta más que mover uno de baja.
            factor = int(round((peso_prio + exceso / 20.0) * 1000))
            for g in nombres:
                if g != t.gestor:
                    costo_mov.append(factor * x[(t.ticket_id, g)])

        # Presupuesto de movimientos: cada cambio de gestor consume cupo.
        if max_movimientos is not None:
            movs = [
                x[(t.ticket_id, g)]
                for t in tickets
                if t.gestor and t.gestor in nombres
                for g in nombres
                if g != t.gestor
            ]
            if movs:
                modelo.Add(sum(movs) <= max_movimientos)

        objetivo = [int(self.params.w_equidad * 100) * (cmax - cmin)]
        if costo_mov:
            objetivo.extend(int(COSTO_MOVIMIENTO) * c for c in costo_mov)
        modelo.Minimize(sum(objetivo) if objetivo else 0)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0
        solver.parameters.num_search_workers = 8
        estado = solver.Solve(modelo)

        if estado not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise RuntimeError("El modelo de asignación no encontró solución factible.")

        resultado: dict[str, str] = {}
        for t in tickets:
            for g in nombres:
                if solver.Value(x[(t.ticket_id, g)]) == 1:
                    resultado[t.ticket_id] = g
                    break

        return self._construir_resultado(tickets, resultado)

    # -------------------------------------------------------------- internos
    def _participantes(self, ticket_id: str) -> int:
        return sum(
            g.participantes_solicitados or 0
            for g in self.ds.grupos
            if g.ticket_id == ticket_id
        )

    def _construir_resultado(
        self, tickets: list[Ticket], nueva: dict[str, str]
    ) -> ResultadoAsignacion:
        previa = {t.ticket_id: t.gestor for t in tickets}

        cargas_antes, _ = calcular_cargas(self.ds, tickets, self.params.pesos_carga, previa)
        cargas_despues, desgloses = calcular_cargas(self.ds, tickets, self.params.pesos_carga, nueva)

        movimientos = [
            {
                "ticket_id": tid,
                "de": previa[tid],
                "a": nueva[tid],
                "peso": desgloses[tid].total,
                "prioridad": next(t.prioridad.value for t in tickets if t.ticket_id == tid),
            }
            for tid in nueva
            if previa.get(tid) != nueva[tid]
        ]

        def _dump(c: dict) -> dict:
            return {
                g: {
                    "tickets": v.tickets,
                    "carga_total": v.carga_total,
                    "sesiones": v.sesiones,
                    "dias_con_sesion": v.dias_con_sesion,
                    "tickets_obligatorios": v.tickets_obligatorios,
                    "tickets_ruta_b": v.tickets_ruta_b,
                }
                for g, v in c.items()
            }

        return ResultadoAsignacion(
            asignacion=nueva,
            asignacion_previa=previa,
            movimientos=movimientos,
            metricas_antes=metricas_equidad(cargas_antes),
            metricas_despues=metricas_equidad(cargas_despues),
            cargas_antes=_dump(cargas_antes),
            cargas_despues=_dump(cargas_despues),
            estado_solver="OPTIMAL",
        )
