"""Capa de servicio: une estado, motores y esquemas de la API.

Los routers no calculan nada; solo llaman aquí. Esto mantiene la lógica de
optimización testeable sin levantar el servidor.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from app.core.model_params import ParametrosOptimizacion
from app.engine.assignment_solver import AsignacionSolver
from app.engine.calendar_solver import CalendarioSolver
from app.engine.sla import evaluar as evaluar_plazo
from app.engine.verificador import VerificadorCalendario
from app.engine.weights import calcular_cargas, calcular_peso, metricas_equidad
from app.models.domain import Dataset, EstadoGestor, Gestor, Ticket
from app.services.state import EstadoApp


def _dump_cargas(cargas: dict) -> list[dict[str, Any]]:
    return [
        {
            "gestor": g,
            "tickets": c.tickets,
            "carga_total": c.carga_total,
            "sesiones": c.sesiones,
            "dias_con_sesion": c.dias_con_sesion,
            "tickets_obligatorios": c.tickets_obligatorios,
            "tickets_ruta_b": c.tickets_ruta_b,
        }
        for g, c in sorted(cargas.items())
    ]


def _peso_ticket(ds: Dataset, t: Ticket, params: ParametrosOptimizacion) -> float:
    participantes = sum(
        g.participantes_solicitados or 0 for g in ds.grupos if g.ticket_id == t.ticket_id
    )
    return calcular_peso(t, participantes, params.pesos_carga).total


class Orquestador:
    def __init__(self, estado: EstadoApp) -> None:
        self.e = estado
        self.ds = estado.ds
        self.params = ParametrosOptimizacion()

    # ------------------------------------------------------------ recursos
    def recursos(self) -> dict[str, Any]:
        abiertos = self.e.tickets_para_optimizar()
        cargas, _ = calcular_cargas(self.ds, abiertos, self.params.pesos_carga)

        gestores = []
        for g in self.e.gestores:
            c = cargas.get(g.nombre)
            gestores.append(
                {
                    "nombre": g.nombre,
                    "estado": g.estado.value,
                    "vacaciones_desde": g.vacaciones_desde,
                    "vacaciones_hasta": g.vacaciones_hasta,
                    "tickets": c.tickets if c else 0,
                    "carga": c.carga_total if c else 0.0,
                    "sesiones": c.sesiones if c else 0,
                    "disponible_hoy": g.disponible_en(self.e.hoy),
                }
            )

        return {
            "gestores": gestores,
            "fecha_corte": self.e.hoy,
            "n_gestores_activos": sum(
                1 for g in self.e.gestores if g.estado is EstadoGestor.ACTIVO
            ),
        }

    # ------------------------------------------------------------ tickets
    def tickets(self, estado: str | None = None) -> list[dict[str, Any]]:
        out = []
        for t in self.e.tickets:
            if estado and t.estado.value != estado:
                continue
            ev = evaluar_plazo(t, self.e.hoy)
            out.append(
                {
                    "ticket_id": t.ticket_id,
                    "estado": t.estado.value,
                    "prioridad": t.prioridad.value,
                    "modalidad": t.modalidad.value,
                    "evento": t.evento,
                    "dependencia": t.dependencia,
                    "gestor": t.gestor,
                    "fecha_ingreso": t.fecha_ingreso,
                    "fecha_inicio": t.fecha_inicio,
                    "fecha_fin": t.fecha_fin,
                    "tipo_docente": t.tipo_docente.value,
                    "observacion": t.observacion.value,
                    "grupos": t.grupos_programados,
                    "sesiones_por_grupo": t.sesiones_por_grupo,
                    "total_sesiones": t.total_sesiones,
                    "dias_abiertos": t.dias_abiertos,
                    "dias_habiles_restantes": t.dias_habiles_restantes,
                    "req_dias_habiles": t.req_dias_habiles,
                    "severidad": ev.severidad.value,
                    "es_ruta_b": t.es_ruta_b,
                    "obligatorio": t.requiere_supervision_obligatoria,
                    "peso": round(_peso_ticket(self.ds, t, self.params), 2),
                }
            )
        return out

    def sugerir_gestor(self, datos: dict) -> dict[str, Any]:
        """Mesa de entrada: a quién asignar un ticket nuevo (Regla 1 y 5)."""
        abiertos = self.e.tickets_para_optimizar()
        cargas, _ = calcular_cargas(self.ds, abiertos, self.params.pesos_carga)

        grupos = int(datos.get("grupos_programados", 1))
        spg = int(datos.get("sesiones_por_grupo", 1))
        scratch = Ticket(
            ticket_id="__nuevo__",
            estado=self.e.tickets[0].estado if self.e.tickets else None,  # type: ignore[arg-type]
            prioridad=datos.get("prioridad", "Media"),
            modalidad=datos["modalidad"],
            evento=datos.get("evento", ""),
            dependencia="",
            gestor="",
            fecha_ingreso=self.e.hoy,
            fecha_asignacion=self.e.hoy,
            fecha_inicio=datos.get("fecha_inicio"),
            fecha_fin=None,
            tipo_docente=datos.get("tipo_docente", "Interno"),
            observacion=None,  # type: ignore[arg-type]
            observacion_raw="",
            grupos_programados=grupos,
            sesiones_por_grupo=spg,
            total_sesiones=grupos * spg,
        )
        peso = calcular_peso(scratch, 0, self.params.pesos_carga).total

        candidatos = []
        for g in self.e.gestores:
            if g.estado is not EstadoGestor.ACTIVO:
                continue
            actual = cargas[g.nombre].carga_total if g.nombre in cargas else 0.0
            candidatos.append(
                {
                    "gestor": g.nombre,
                    "carga_actual": round(actual, 2),
                    "carga_resultante": round(actual + peso, 2),
                    "delta": round(peso, 2),
                    "recomendado": False,
                }
            )

        if not candidatos:
            return {"peso_ticket": round(peso, 2), "sugerencias": []}

        mejor = min(candidatos, key=lambda c: c["carga_resultante"])
        mejor["recomendado"] = True
        return {"peso_ticket": round(peso, 2), "sugerencias": candidatos}

    def simular_cambio_docente(self, ticket_id: str, nuevo_tipo: str) -> dict[str, Any]:
        from app.engine.sla import simular_cambio_docente

        t = next((x for x in self.e.tickets if x.ticket_id == ticket_id), None)
        if t is None:
            raise KeyError(ticket_id)

        abiertos = self.e.tickets_para_optimizar()
        cargas_antes, _ = calcular_cargas(self.ds, abiertos, self.params.pesos_carga)
        peso_antes = _peso_ticket(self.ds, t, self.params)

        from copy import deepcopy

        simulado = deepcopy(t)
        from app.models.domain import TipoDocente

        simulado.tipo_docente = TipoDocente(nuevo_tipo)
        peso_despues = _peso_ticket(self.ds, simulado, self.params)

        carga_act = cargas_antes[t.gestor].carga_total if t.gestor in cargas_antes else 0.0
        delta = peso_despues - peso_antes

        sla = simular_cambio_docente(t, TipoDocente(nuevo_tipo), self.e.hoy)

        return {
            "ticket_id": ticket_id,
            "gestor": t.gestor,
            "peso_antes": round(peso_antes, 2),
            "peso_despues": round(peso_despues, 2),
            "delta_peso": round(delta, 2),
            "carga_actual": round(carga_act, 2),
            "carga_simulada": round(carga_act + delta, 2),
            "plazo": sla,
        }

    # ------------------------------------------------------- optimización
    def optimizar(
        self,
        theta_muestreo: float = 0.25,
        semilla: int = 20261008,
        max_movimientos: int = 6,
        reasignar: bool = True,
        generar_calendario: bool = True,
    ) -> dict[str, Any]:
        self.params = ParametrosOptimizacion(theta_muestreo=theta_muestreo, semilla=semilla)
        self.params.validar()

        abiertos = self.e.tickets_para_optimizar()

        # gestores activos; en vacaciones no reciben tickets nuevos
        activos = [g for g in self.e.gestores if g.estado is EstadoGestor.ACTIVO]

        if reasignar:
            resultado = AsignacionSolver(self.ds, self.params).resolver(
                tickets=abiertos, gestores=activos, max_movimientos=max_movimientos
            )
            asignacion = resultado.asignacion
            comparativa = {
                "antes": _dump_cargas(calcular_cargas(self.ds, abiertos, self.params.pesos_carga, resultado.asignacion_previa)[0]),
                "despues": resultado.cargas_despues and _dump_from_dict(resultado.cargas_despues),
                "metricas_antes": resultado.metricas_antes,
                "metricas_despues": resultado.metricas_despues,
            }
            movimientos = resultado.movimientos
            cargas_opt = resultado.cargas_despues
        else:
            asignacion = self.asignacion_vigente()
            cargas, _ = calcular_cargas(self.ds, abiertos, self.params.pesos_carga, asignacion)
            comparativa = {
                "antes": _dump_cargas(cargas),
                "despues": _dump_cargas(cargas),
                "metricas_antes": metricas_equidad(cargas),
                "metricas_despues": metricas_equidad(cargas),
            }
            movimientos = []
            cargas_opt = {g: {
                "tickets": c.tickets, "carga_total": c.carga_total, "sesiones": c.sesiones,
                "dias_con_sesion": c.dias_con_sesion,
                "tickets_obligatorios": c.tickets_obligatorios,
                "tickets_ruta_b": c.tickets_ruta_b,
            } for g, c in cargas.items()}

        # aplicar la asignación al estado para que el calendario la respete
        for tid, gestor in asignacion.items():
            self.e.asignacion_manual[tid] = gestor
            for t in self.e.tickets:
                if t.ticket_id == tid:
                    t.gestor = gestor
                    break

        calendario = None
        if generar_calendario:
            # el calendario necesita que las sesiones reflejen el gestor actual
            self._resincronizar_sesiones(asignacion, cargas_opt)
            rc = CalendarioSolver(self._ds_con_sesiones(), self.params).resolver(
                gestores=self.e.gestores
            )
            calendario = self._serializar_calendario(rc)

        alertas = [self._alerta(t) for t in abiertos]
        alertas = sorted(alertas, key=lambda a: _orden_severidad(a["severidad"]))

        self.e.ultima_optimizacion = {
            "comparativa": comparativa,
            "movimientos": movimientos,
            "calendario": calendario,
        }
        return {
            "comparativa": comparativa,
            "movimientos": movimientos,
            "calendario": calendario,
            "alertas_plazo": alertas,
            "diagnostico_capacidad": CalendarioSolver.diagnostico_capacidad(
                self._ds_con_sesiones(), self.e.gestores
            ),
        }

    # ----------------------------------------------------- helpers internos
    def asignacion_vigente(self) -> dict[str, str]:
        return {t.ticket_id: t.gestor for t in self.e.tickets_para_optimizar()}

    def _resincronizar_sesiones(self, asignacion: dict[str, str], cargas: dict) -> None:
        """Devuelve las sesiones al gestor dueño actual del ticket."""
        gestor_por_ticket = dict(asignacion)
        for s in self.ds.sesiones:
            if s.ticket_id in gestor_por_ticket:
                object.__setattr__(s, "gestor", gestor_por_ticket[s.ticket_id])
        for s in self.ds.sesiones:
            if s.ticket_id in gestor_por_ticket:
                object.__setattr__(s, "gestor", gestor_por_ticket[s.ticket_id])

    def _ds_con_sesiones(self) -> Dataset:
        return self.ds

    def _alerta(self, t: Ticket) -> dict[str, Any]:
        ev = evaluar_plazo(t, self.e.hoy)
        return {
            "ticket_id": t.ticket_id,
            "evento": t.evento,
            "gestor": t.gestor,
            "prioridad": t.prioridad.value,
            "tipo_docente": t.tipo_docente.value,
            "fecha_inicio": t.fecha_inicio,
            "disponibles": ev.disponibles,
            "requeridos": ev.requiere_dias,
            "holgura": ev.holgura,
            "severidad": ev.severidad.value,
            "mensaje": ev.mensaje,
        }

    def _serializar_calendario(self, rc) -> dict[str, Any]:
        sesiones = {s.sesion_id: s for s in self.ds.sesiones}
        tickets = {t.ticket_id: t for t in self.e.tickets}
        por_fecha: dict[str, list[dict]] = {}

        for (gestor, fecha_iso), lista in rc.plan.asignaciones.items():
            for sid in lista:
                s = sesiones[sid]
                t = tickets.get(s.ticket_id)
                por_fecha.setdefault(fecha_iso, []).append(
                    {
                        "sesion_id": sid,
                        "ticket_id": s.ticket_id,
                        "evento": t.evento if t else "",
                        "grupo": s.grupo,
                        "numero_sesion": s.numero_sesion,
                        "fecha": s.fecha,
                        "hora_inicio": s.hora_inicio.strftime("%H:%M") if s.hora_inicio else None,
                        "hora_fin": s.hora_fin.strftime("%H:%M") if s.hora_fin else None,
                        "gestor": gestor,
                        "gestor_dueno": s.gestor,
                        "es_apoyo": sid in rc.plan.apoyos,
                        "obligatoria": s.obligatoria,
                        "modalidad": s.modalidad.value if s.modalidad else "",
                    }
                )

        dias = [
            {
                "fecha": date.fromisoformat(f),
                "sesiones": sorted(v, key=lambda x: (x["gestor"], x["hora_inicio"] or "")),
                "saturado": f in rc.dias_saturados,
            }
            for f, v in sorted(por_fecha.items())
        ]

        rep = rc.verificacion
        return {
            "dias": dias,
            "dias_saturados": [
                {"fecha": f, "sesiones": s} for f, s in rc.dias_saturados.items()
            ],
            "cobertura_pct": rep.cobertura_pct,
            "obligatorias_cubiertas": rep.obligatorias_cubiertas,
            "obligatorias_totales": rep.sesiones_obligatorias,
            "regulares_cubiertas": rep.regulares_cubiertas,
            "regulares_totales": rep.regulares_totales,
            "colisiones": rep.dias_con_colision,
            "violaciones": [str(v) for v in rep.violaciones],
        }

    # ----------------------------------------------------------- dashboard
    def dashboard(self) -> dict[str, Any]:
        abiertos = self.e.tickets_para_optimizar()
        cargas, _ = calcular_cargas(self.ds, abiertos, self.params.pesos_carga)
        alertas = [self._alerta(t) for t in abiertos]

        ruta_b = [t for t in abiertos if t.es_ruta_b]
        en_alerta = [a for a in alertas if a["severidad"] in ("ROJO", "AMBAR")]

        v = VerificadorCalendario(self.ds)
        universo = v._universo_esperado()
        sesiones = {s.sesion_id: s for s in self.ds.sesiones}
        obligatorias = sum(1 for s in universo if sesiones[s].obligatoria)

        return {
            "kpis": {
                "tickets_abiertos": len(abiertos),
                "tickets_totales": len(self.e.tickets),
                "eventos_ruta_b": len(ruta_b),
                "alertas_contratacion": sum(
                    1 for a in alertas
                    if a["tipo_docente"] == "Externo" and a["severidad"] == "ROJO"
                ),
                "tickets_en_alerta": len(en_alerta),
                "sesiones_por_supervisar": len(universo),
                "sesiones_obligatorias": obligatorias,
                "gestores_activos": sum(
                    1 for g in self.e.gestores if g.estado is EstadoGestor.ACTIVO
                ),
                "ratio_desbalance": metricas_equidad(cargas)["ratio"],
            },
            "cargas": _dump_cargas(cargas),
            "tickets_por_prioridad": dict(Counter(t.prioridad.value for t in abiertos)),
            "tickets_por_modalidad": dict(Counter(t.modalidad.value for t in abiertos)),
            "tickets_por_tipo_docente": dict(Counter(t.tipo_docente.value for t in abiertos)),
            "tickets_por_estado": dict(Counter(t.estado.value for t in self.e.tickets)),
            "alertas_plazo": sorted(alertas, key=lambda a: _orden_severidad(a["severidad"])),
            "ruta_b": {
                "tickets": len(ruta_b),
                "carga_liberada": round(
                    sum(_peso_ticket(self.ds, t, self.params) for t in ruta_b), 2
                ),
                "ids": [t.ticket_id for t in ruta_b],
            },
        }


def _dump_from_dict(cargas: dict) -> list[dict[str, Any]]:
    return [
        {"gestor": g, **v} for g, v in sorted(cargas.items())
    ]


def _orden_severidad(s: str) -> int:
    return {"ROJO": 0, "AMBAR": 1, "SIN_FECHA": 2, "VERDE": 3}.get(s, 4)
