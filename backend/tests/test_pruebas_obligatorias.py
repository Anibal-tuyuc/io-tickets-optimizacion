"""Las tres pruebas de estrés exigidas por el enunciado (§10).

Prueba 1 — Optimización inicial y detección de choques.
Prueba 2 — Baja por vacaciones y redistribución.
Prueba 3 — Cambio dinámico de docente a contratación externa.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest

from app.core.model_params import ParametrosOptimizacion
from app.engine.assignment_solver import AsignacionSolver
from app.engine.calendar_solver import CalendarioSolver
from app.engine.sla import simular_cambio_docente
from app.engine.verificador import VerificadorCalendario
from app.engine.weights import calcular_cargas, metricas_equidad
from app.models.domain import EstadoGestor, Gestor, Severidad, TipoDocente

HOY = date(2026, 10, 8)


# ---------------------------------------------------------------- Prueba 1
class TestPrueba1Optimizacion:
    def test_desbalance_inicial_comprobado(self, ds):
        cargas, _ = calcular_cargas(ds)
        m = metricas_equidad(cargas)
        assert m["ratio"] > 1.8, "El desbalance inicial debería ser severo"
        # El argumento central: mismo número de tickets, cargas muy distintas.
        iguales = [c for c in cargas.values() if c.tickets == 10]
        assert len(iguales) >= 3
        cargas_de_diez = sorted(c.carga_total for c in iguales)
        assert cargas_de_diez[-1] - cargas_de_diez[0] > 5.0

    def test_optimizacion_equilibra(self, ds):
        r = AsignacionSolver(ds).resolver()
        assert r.metricas_despues["ratio"] < 1.15
        assert r.metricas_despues["rango"] < r.metricas_antes["rango"]
        assert len(r.asignacion) == len(ds.tickets_abiertos)

    def test_cada_ticket_tiene_exactamente_un_gestor(self, ds):
        r = AsignacionSolver(ds).resolver()
        assert set(r.asignacion) == {t.ticket_id for t in ds.tickets_abiertos}

    def test_movimientos_limitados(self, ds):
        r = AsignacionSolver(ds).resolver(max_movimientos=6)
        assert len(r.movimientos) <= 6

    def test_sin_colisiones_tras_optimizar(self, ds):
        r = CalendarioSolver(ds).resolver()
        assert r.verificacion.dias_con_colision == 0
        assert r.verificacion.ok, r.verificacion.resumen()["detalle_violaciones"]

    def test_cobertura_total_de_obligatorias(self, ds):
        r = CalendarioSolver(ds).resolver()
        assert r.verificacion.obligatorias_cubiertas == r.verificacion.sesiones_obligatorias

    def test_nigun_gestor_supervisa_dos_el_mismo_dia(self, ds):
        r = CalendarioSolver(ds).resolver()
        for (gestor, dia), lista in r.plan.asignaciones.items():
            assert len(lista) <= 1, f"{gestor} tiene {len(lista)} sesiones el {dia}"

    def test_supervision_solo_en_la_fecha_real(self, ds):
        r = CalendarioSolver(ds).resolver()
        sesiones = {s.sesion_id: s for s in ds.sesiones}
        for (_, dia), lista in r.plan.asignaciones.items():
            for sid in lista:
                assert sesiones[sid].fecha.isoformat() == dia

    def test_ninguna_sesion_de_ruta_b_supervisada(self, ds):
        r = CalendarioSolver(ds).resolver()
        sesiones = {s.sesion_id: s for s in ds.sesiones}
        for lista in r.plan.asignaciones.values():
            for sid in lista:
                assert sesiones[sid].modalidad.value != "Virtual Asincrónico"

    def test_dias_saturados_se_reportan(self, ds):
        """Hay días con más sesiones que gestores: debe advertirse, no ocultarse."""
        saturados = CalendarioSolver.diagnostico_capacidad(ds)
        fechas = {d["fecha"] for d in saturados}
        assert "2026-10-13" in fechas
        assert "2026-10-12" in fechas
        assert all(not d["factible"] for d in saturados)

    def test_colisiones_originales_detectadas(self, ds):
        """El verificador debe encontrar choques en el calendario del Excel."""
        from app.engine.verificador import PlanSupervision

        plan = PlanSupervision()
        for s in ds.sesiones:
            t = ds.tickets_por_id[s.ticket_id]
            if t.estado.value != "Abierto" or s.modalidad.value == "Virtual Asincrónico":
                continue
            plan.asignaciones.setdefault((s.gestor, s.fecha.isoformat()), []).append(s.sesion_id)

        rep = VerificadorCalendario(ds).verificar(plan)
        assert rep.dias_con_colision > 0, "El calendario original debería mostrar choques"


# ---------------------------------------------------------------- Prueba 2
class TestPrueba2Vacaciones:
    def _gestores_con_vacaciones(self, ds, gestor: str, desde: date, hasta: date) -> list[Gestor]:
        gestores = deepcopy(ds.gestores)
        for g in gestores:
            if g.nombre == gestor:
                g.estado = EstadoGestor.VACACIONES
                g.vacaciones_desde = desde
                g.vacaciones_hasta = hasta
        return gestores

    def test_redistribuye_sin_colisiones(self, ds):
        """Con 4 gestores, el 13-oct es infeasible: debe declararse, no ocultarse.

        Ese día hay 5 sesiones obligatorias (una es del Gestor 1, de vacaciones)
        y quedan 4 gestores. Es aritméticamente imposible cubrirlas todas sin
        violar "máximo 1 evento por día". El sistema correcto:
          - no genera ninguna colisión,
          - cubre todo lo cubrible,
          - reporta el día saturado con su causa.
        """
        gestores = self._gestores_con_vacaciones(
            ds, "Gestor 1", date(2026, 10, 12), date(2026, 10, 30)
        )
        r = CalendarioSolver(ds).resolver(gestores=gestores)

        assert r.verificacion.dias_con_colision == 0

        reglas = {v.regla for v in r.verificacion.violaciones}
        assert reglas <= {"obligatoria_no_cubierta"}, (
            f"Con 4 gestores solo se admite infactibilidad de cobertura, no "
            f"colisiones ni errores de modelo: {reglas}"
        )
        # la única sesión imposible es la del gestor ausente en el día saturado
        faltantes = [
            v.detalle for v in r.verificacion.violaciones
            if v.regla == "obligatoria_no_cubierta"
        ]
        assert all("6375-PFIN-26" in d for d in faltantes), faltantes
        assert r.verificacion.obligatorias_cubiertas == r.verificacion.sesiones_obligatorias - 1

    def test_dia_saturado_reportado_con_causa(self, ds):
        """El día infeasible debe aparecer en el diagnóstico de capacidad."""
        gestores = self._gestores_con_vacaciones(
            ds, "Gestor 1", date(2026, 10, 12), date(2026, 10, 30)
        )
        ds_vac = deepcopy(ds)
        ds_vac.gestores = gestores
        saturados = CalendarioSolver.diagnostico_capacidad(ds_vac)
        por_fecha = {d["fecha"]: d for d in saturados}
        assert "2026-10-13" in por_fecha
        assert por_fecha["2026-10-13"]["gestores_disponibles"] == 4
        assert por_fecha["2026-10-13"]["factible"] is False

    def test_gestor_de_vacaciones_no_recibe_sesiones(self, ds):
        desde, hasta = date(2026, 10, 12), date(2026, 10, 30)
        gestores = self._gestores_con_vacaciones(ds, "Gestor 1", desde, hasta)
        r = CalendarioSolver(ds).resolver(gestores=gestores)
        for (gestor, dia), lista in r.plan.asignaciones.items():
            if gestor == "Gestor 1":
                d = date.fromisoformat(dia)
                assert not (desde <= d <= hasta), f"Gestor 1 supervisa el {dia} en vacaciones"

    def test_tickets_del_gestor_ausente_se_reasignan(self, ds):
        gestores = self._gestores_con_vacaciones(
            ds, "Gestor 1", date(2026, 10, 12), date(2026, 10, 30)
        )
        activos = [g for g in gestores if g.estado is not EstadoGestor.INACTIVO]
        r = AsignacionSolver(ds).resolver(gestores=activos)
        assert "Gestor 1" not in set(r.asignacion.values())
        assert r.metricas_despues["ratio"] < 1.2

    def test_gestor_extra_mejora_equidad(self, ds):
        gestores = deepcopy(ds.gestores)
        gestores.append(Gestor(gestor_id="Gestor 6", nombre="Gestor 6"))
        r = AsignacionSolver(ds).resolver(gestores=gestores)
        assert "Gestor 6" in set(r.asignacion.values())
        assert r.metricas_despues["ratio"] < 1.2

    def test_inactivo_no_trabaja_nunca(self, ds):
        gestores = deepcopy(ds.gestores)
        for g in gestores:
            if g.nombre == "Gestor 3":
                g.estado = EstadoGestor.INACTIVO
        r = CalendarioSolver(ds).resolver(gestores=gestores)
        assert all(g != "Gestor 3" for (g, _) in r.plan.asignaciones)


# ---------------------------------------------------------------- Prueba 3
class TestPrueba3CambioDocente:
    def test_6376_pasa_a_rojo(self, ds):
        t = next(x for x in ds.tickets if x.ticket_id == "6376-PFIN-26")
        s = simular_cambio_docente(t, TipoDocente.EXTERNO, HOY)
        assert s["antes"]["severidad"] == Severidad.AMBAR.value
        assert s["despues"]["severidad"] == Severidad.ROJO.value
        assert s["deterioro"] is True

    def test_6286_conserva_margen(self, ds):
        t = next(x for x in ds.tickets if x.ticket_id == "6286-PFIN-26")
        s = simular_cambio_docente(t, TipoDocente.EXTERNO, HOY)
        assert s["antes"]["severidad"] == Severidad.VERDE.value
        assert s["despues"]["severidad"] in (Severidad.AMBAR.value, Severidad.VERDE.value)
        assert s["despues"]["severidad"] != Severidad.ROJO.value

    def test_contraste_rojo_verde(self, ds):
        """El semáforo debe discriminar: no puede dar el mismo color a ambos."""
        rojo = next(x for x in ds.tickets if x.ticket_id == "6376-PFIN-26")
        verde = next(x for x in ds.tickets if x.ticket_id == "6286-PFIN-26")
        s1 = simular_cambio_docente(rojo, TipoDocente.EXTERNO, HOY)
        s2 = simular_cambio_docente(verde, TipoDocente.EXTERNO, HOY)
        assert s1["despues"]["severidad"] != s2["despues"]["severidad"]

    def test_peso_aumenta_con_contratacion_externa(self, ds):
        from app.engine.weights import calcular_peso

        t = next(x for x in ds.tickets if x.ticket_id == "6376-PFIN-26")
        peso_antes = calcular_peso(t, 0).total

        t2 = deepcopy(t)
        t2.tipo_docente = TipoDocente.EXTERNO
        peso_despues = calcular_peso(t2, 0).total
        assert peso_despues > peso_antes

    def test_sin_fecha_no_rompe(self, ds):
        t = next(x for x in ds.tickets if x.ticket_id == "6404-PFIN-26")
        s = simular_cambio_docente(t, TipoDocente.EXTERNO, HOY)
        assert s["antes"]["severidad"] == Severidad.SIN_FECHA.value
        assert s["despues"]["disponibles"] is None
