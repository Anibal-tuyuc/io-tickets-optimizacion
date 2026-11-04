"""Programación del calendario de acompañamiento docente (Regla 4).

Modelo en dos etapas:

  Etapa 1 — sesiones OBLIGATORIAS (CP-SAT)
      Σ_g y[s,g] + u[s] = 1        ∀ s ∈ S_ob      (cobertura 100% con holgura)
      Σ_{s∈día d} y[s,g] ≤ 1       ∀ g, d          (máximo 1 evento por día)
      y[s,g] = 0                   si g no está disponible ese día
      min  Σ_s (PESO_HOLGURA · u[s] + PESO_APOYO · apoyo[s])

  Etapa 2 — sesiones REGULARES (muestreo controlado)
      Se rellena la capacidad sobrante de cada gestor-día con una muestra
      aleatoria reproducible (semilla) del ⌈θ·n⌉ mínimo exigido por gestor.

Por qué holgura y no infactibilidad: hay días con 8 sesiones y 5 gestores.
Forzar factibilidad es imposible; se reporta "día saturado" para que la
dirección asigne apoyo externo. Esconderlo sería falsificar la demo.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from ortools.sat.python import cp_model

from app.core.model_params import ParametrosOptimizacion
from app.engine.verificador import PlanSupervision, ReporteVerificacion
from app.models.domain import Dataset, EstadoGestor, Gestor, Sesion

PESO_HOLGURA = 1000   # no cubrir una obligatoria es carísimo
PESO_APOYO = 5        # preferir al gestor dueño del ticket
PESO_DESBALANCEO = 1  # repartir supervisiones entre gestores


@dataclass(slots=True)
class ResultadoCalendario:
    plan: PlanSupervision
    verificacion: ReporteVerificacion
    sesiones_obligatorias: int
    obligatorias_cubiertas: int
    regulares_muestreadas: int
    regulares_totales: int
    dias_saturados: dict[str, list[str]] = field(default_factory=dict)
    apoyos: dict[str, str] = field(default_factory=dict)
    estadisticas_solver: dict[str, object] = field(default_factory=dict)


class CalendarioSolver:
    def __init__(self, ds: Dataset, params: ParametrosOptimizacion | None = None) -> None:
        self.ds = ds
        self.params = params or ParametrosOptimizacion()
        self.sesiones: dict[str, Sesion] = {s.sesion_id: s for s in ds.sesiones}
        self.gestores: list[Gestor] = ds.gestores

    # ------------------------------------------------------------------ API
    def resolver(self, gestores: list[Gestor] | None = None) -> ResultadoCalendario:
        gestores = gestores if gestores is not None else self.gestores
        universo = self._universo()

        obligatorias = [sid for sid in universo if self.sesiones[sid].obligatoria]
        regulares = [sid for sid in universo if not self.sesiones[sid].obligatoria]

        plan = PlanSupervision()
        cubiertas_ob = self._etapa_obligatorias(obligatorias, gestores, plan)
        self._etapa_regulares(regulares, gestores, plan)

        # ---- cerrar el plan: días saturados y sin cobertura
        por_dia: dict[str, list[str]] = defaultdict(list)
        for sid in universo:
            por_dia[self.sesiones[sid].fecha.isoformat()].append(sid)

        cubiertas = {sid for lista in plan.asignaciones.values() for sid in lista}
        for fecha_iso, sids in por_dia.items():
            faltan = [s for s in sids if s not in cubiertas]
            obligatorias_faltantes = [s for s in faltan if self.sesiones[s].obligatoria]
            if obligatorias_faltantes:
                plan.dias_saturados[fecha_iso] = obligatorias_faltantes
                for s in obligatorias_faltantes:
                    plan.sin_cobertura[s] = "día saturado: más sesiones obligatorias que gestores disponibles"

        from app.engine.verificador import VerificadorCalendario

        verificador = VerificadorCalendario(self.ds, theta_minimo=self.params.theta_muestreo)
        reporte = verificador.verificar(plan, set(universo))

        return ResultadoCalendario(
            plan=plan,
            verificacion=reporte,
            sesiones_obligatorias=len(obligatorias),
            obligatorias_cubiertas=len(cubiertas_ob),
            regulares_muestreadas=sum(
                1 for sid in regulares if sid in cubiertas
            ),
            regulares_totales=len(regulares),
            dias_saturados=dict(plan.dias_saturados),
            apoyos=dict(plan.apoyos),
            estadisticas_solver={"estado": "OPTIMAL" if not plan.dias_saturados else "CON_HOLGURA"},
        )

    # -------------------------------------------------------------- internos
    def _universo(self) -> list[str]:
        abiertos = {t.ticket_id for t in self.ds.tickets_abiertos}
        return [
            s.sesion_id
            for s in self.ds.sesiones
            if s.ticket_id in abiertos
            and s.modalidad is not None
            and s.modalidad.value != "Virtual Asincrónico"
        ]

    def _disponible(self, gestores: list[Gestor], nombre: str, dia: date) -> bool:
        g = next((x for x in gestores if x.nombre == nombre), None)
        return bool(g and g.disponible_en(dia))

    def _etapa_obligatorias(
        self, sids: list[str], gestores: list[Gestor], plan: PlanSupervision
    ) -> set[str]:
        """Asigna supervisor a cada sesión obligatoria."""
        modelo = cp_model.CpModel()
        nombres = [g.nombre for g in gestores if g.estado is not EstadoGestor.INACTIVO]

        y: dict[tuple[str, str], cp_model.IntVar] = {}
        u: dict[str, cp_model.IntVar] = {}

        for sid in sids:
            sesion = self.sesiones[sid]
            dia = sesion.fecha
            candidatos = [g for g in nombres if self._disponible(gestores, g, dia)]
            u[sid] = modelo.NewBoolVar(f"u_{sid}")
            for g in candidatos:
                y[(sid, g)] = modelo.NewBoolVar(f"y_{sid}_{g}")
            if candidatos:
                modelo.Add(sum(y[(sid, g)] for g in candidatos) + u[sid] == 1)
            else:
                modelo.Add(u[sid] == 1)

        # máximo 1 sesión por gestor por día
        por_gestor_dia: dict[tuple[str, str], list] = defaultdict(list)
        for (sid, g), var in y.items():
            por_gestor_dia[(g, self.sesiones[sid].fecha.isoformat())].append(var)
        for vars_ in por_gestor_dia.values():
            modelo.Add(sum(vars_) <= 1)

        # objetivo
        costo = []
        for sid in sids:
            costo.append(PESO_HOLGURA * u[sid])
            for (s_id, g), var in y.items():
                if s_id == sid and g != self.sesiones[sid].gestor:
                    costo.append(PESO_APOYO * var)
        # repartir carga de supervisión
        for g in nombres:
            total = sum(var for (s, gg), var in y.items() if gg == g)
            costo.append(PESO_DESBALANCEO * total)
        modelo.Minimize(sum(costo) if costo else 0)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0
        solver.parameters.num_search_workers = 8
        estado = solver.Solve(modelo)
        if estado not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return set()

        cubiertas: set[str] = set()
        for (sid, g), var in y.items():
            if solver.Value(var) == 1:
                dia = self.sesiones[sid].fecha.isoformat()
                plan.asignaciones.setdefault((g, dia), []).append(sid)
                cubiertas.add(sid)
                if g != self.sesiones[sid].gestor:
                    plan.apoyos[sid] = g
        return cubiertas

    def _etapa_regulares(
        self, sids: list[str], gestores: list[Gestor], plan: PlanSupervision
    ) -> None:
        """Muestreo aleatorio reproducible, respetando capacidad por día.

        Para cada gestor se eligen ⌈θ·n⌉ sesiones regulares. El cupo del gestor
        dueño es 1 sesión por día; si su calendario ya está lleno en la fecha de
        la sesión, se busca un gestor de apoyo libre ese día. Si nadie puede
        cubrirla, la sesión queda sin muestrear y el verificador lo reporta en
        lugar de maquillarlo.
        """
        rng = random.Random(self.params.semilla)

        ocupado: dict[tuple[str, str], int] = {}
        for (g, dia), lista in plan.asignaciones.items():
            ocupado[(g, dia)] = len(lista)

        por_gestor: dict[str, list[str]] = defaultdict(list)
        for sid in sids:
            por_gestor[self.sesiones[sid].gestor].append(sid)

        activos = [g for g in gestores if g.estado is not EstadoGestor.INACTIVO]

        for gestor, lista in sorted(por_gestor.items()):
            lista = sorted(lista, key=lambda s: (self.sesiones[s].fecha, s))
            minimo = int(self.params.theta_muestreo * len(lista) + 0.999999)
            if minimo <= 0:
                continue

            # orden: primero los días menos cargados globalmente, con desempate
            # aleatorio reproducible dentro de cada día
            carga_dia: dict[str, int] = defaultdict(int)
            for (_, dia), n in ocupado.items():
                carga_dia[dia] += n
            rng.shuffle(lista)
            lista.sort(key=lambda s: carga_dia[self.sesiones[s].fecha.isoformat()])

            cubiertas = 0
            for sid in lista:
                if cubiertas >= minimo:
                    break
                sesion = self.sesiones[sid]
                dia = sesion.fecha.isoformat()

                # 1) el propio gestor dueño, si tiene el día libre
                if (
                    ocupado.get((gestor, dia), 0) == 0
                    and self._disponible(gestores, gestor, sesion.fecha)
                ):
                    plan.asignaciones.setdefault((gestor, dia), []).append(sid)
                    ocupado[(gestor, dia)] = 1
                    cubiertas += 1
                    continue

                # 2) gestor de apoyo libre ese día
                for g2 in activos:
                    if g2.nombre == gestor:
                        continue
                    if not g2.disponible_en(sesion.fecha):
                        continue
                    if ocupado.get((g2.nombre, dia), 0) > 0:
                        continue
                    plan.asignaciones.setdefault((g2.nombre, dia), []).append(sid)
                    plan.apoyos[sid] = g2.nombre
                    ocupado[(g2.nombre, dia)] = 1
                    cubiertas += 1
                    break

    # -------------------------------------------------------- diagnóstico
    @staticmethod
    def diagnostico_capacidad(
        ds: Dataset, gestores: list[Gestor] | None = None
    ) -> list[dict]:
        """Días donde hay más sesiones que gestores disponibles.

        Se calcula antes de resolver para poder mostrarlo en la UI como
        advertencia previa (y usarlo en el informe). Debe reflejar bajas y
        vacaciones: es lo que demuestra la Prueba 2.
        """
        from app.engine.verificador import VerificadorCalendario

        gestores = gestores if gestores is not None else ds.gestores
        v = VerificadorCalendario(ds)
        universo = v._universo_esperado()

        indice = {s.sesion_id: s for s in ds.sesiones}
        por_dia: dict[str, list[str]] = defaultdict(list)
        for sid in universo:
            por_dia[indice[sid].fecha.isoformat()].append(sid)

        activos = [g for g in gestores if g.estado is not EstadoGestor.INACTIVO]
        out = []
        for fecha_iso, sids in sorted(por_dia.items()):
            dia = date.fromisoformat(fecha_iso)
            disponibles = [g for g in activos if g.disponible_en(dia)]
            obligatorias = [s for s in sids if indice[s].obligatoria]
            if len(sids) > len(disponibles):
                out.append(
                    {
                        "fecha": fecha_iso,
                        "total_sesiones": len(sids),
                        "obligatorias": len(obligatorias),
                        "gestores_disponibles": len(disponibles),
                        "gestores_ausentes": [g.nombre for g in activos if not g.disponible_en(dia)],
                        "faltan_gestores": len(sids) - len(disponibles),
                        "factible": False,
                        "sesiones": sorted(sids),
                        "sesiones_obligatorias": sorted(obligatorias),
                    }
                )
        return out


def ds_sesion(ds: Dataset, sid: str) -> Sesion:
    for s in ds.sesiones:
        if s.sesion_id == sid:
            return s
    raise KeyError(sid)
